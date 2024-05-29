from ragtime.base.data_type import StartFrom
from ragtime.text_generators import (
    AnsGenerator,
    FactGenerator,
    EvalGenerator,
)
from ragtime.base.retriever import Retriever
from ragtime.base.llm import LLM, LiteLLM

from ragtime.prompters import Prompter, prompterTable
from ragtime.exporters import Exporter, exporterTable

from ragtime.expe import Expe

from ragtime.config import (
    FOLDER_ANSWERS,
    FOLDER_FACTS,
    FOLDER_EVALS,
)
from pydantic import BaseModel, field_validator, ValidationInfo, DirectoryPath, FilePath
from pathlib import Path
from typing import Union, Optional, List
from ragtime.exporters import Json


steps: list[str] = ["answers", "facts", "evals"]

llms_reference: dict = {}


def reference_LLM(cls, name):
    llms_reference[name] = cls


_generator_table: dict[str, dict] = {
    # "questions": {
    #     "generator": (
    #         lambda llms, retriever, num_quest, docs_path: QuestionGenerator(
    #             num_quest=num_quest, docs_path=docs_path, llms=llms
    #         )
    #     ),
    #     "default_output_folder": FOLDER_QUESTIONS,
    # },
    "answers": {
        "generator": (
            lambda llms, retriever, num_quest, docs_path: AnsGenerator(
                llms=llms, retriever=retriever
            )
        ),
        "default_output_folder": FOLDER_ANSWERS,
    },
    "facts": {
        "generator": (
            lambda llms, retriever, num_quest, docs_path: FactGenerator(llms=llms)
        ),
        "default_output_folder": FOLDER_FACTS,
    },
    "evals": {
        "generator": (
            lambda llms, retriever, num_quest, docs_path: EvalGenerator(llms=llms)
        ),
        "default_output_folder": FOLDER_EVALS,
    },
}


class GeneratorParameters(BaseModel):
    prompter: Prompter

    @field_validator("prompter", mode="before")
    @classmethod
    def prompter_from_names(cls, v) -> List[LLM]:
        if isinstance(v, Prompter):
            return v
        if isinstance(v, str) and prompterTable.get(v, None):
            return prompterTable[v]()
        raise ValueError("You have to provide a Prompter in order to create LLMs.")

    llms_name: List[LLM]

    @field_validator("llms_name", mode="before")
    @classmethod
    def llms_from_names(cls, v, info: ValidationInfo) -> List[LLM]:
        """
        Converts a list of names to corresponding llm instance.
        LLM names to be instantiated as LiteLLMs come from https://litellm.vercel.app/docs/providers
        """
        if isinstance(v, list) and all(isinstance(item, LLM) for item in v):
            return v
        prompter: Prompter = info.data.get("prompter", None)
        llm_list: list[LLM] = []
        for name in v:
            try:
                llm_instance = llms_reference.get(name, None)
                if llm_instance:
                    llm_list.append(llm_instance(prompter=prompter))
                else:
                    llm_list.append(LiteLLM(name=name, prompter=prompter))
            except:
                raise ValueError(
                    f"All name in the list must be convertible to LLM instance. {name}"
                )
        return llm_list

    export_to: List[Exporter] = []

    @field_validator("export_to", mode="before")
    @classmethod
    def exporters_from_names(cls, input) -> List[Exporter]:
        exporter_list: List[Exporter] = []
        for key, value in input.items():
            exporter_class: Exporter = exporterTable.get(key, None)
            if not exporter_class:
                raise ValueError(
                    f"All exporter in the list 'export_to' must be convertible to Exporter instance. {key}"
                )
            exporter_list.append(exporter_class(**value))
        return exporter_list

    only_llms: Optional[List[str]] = None
    save_every: Optional[int] = 0
    start_from: Optional[StartFrom] = StartFrom.beginning
    b_missing_only: Optional[bool] = False

    output_folder: Optional[str] = None
    retriever: Optional[Retriever] = None
    num_quest: Optional[int] = 10
    docs_path: Optional[str] = None

    def run(self, step: str, input_file_path: Path) -> Path:
        expe: Expe = Expe(input_file_path.parent, input_file_path.name)

        conf = _generator_table[step]
        conf["generator"](
            self.llms_name, self.retriever, self.num_quest, self.docs_path
        ).generate(
            expe,
            only_llms=self.only_llms,
            save_every=self.save_every,
            start_from=self.start_from,
            b_missing_only=self.b_missing_only,
        )

        output_folder: Path = self.output_folder or conf["default_output_folder"]

        for exporter in self.export_to:
            exporter.save(expe, output_folder, input_file_path.name)
        return Json().save(expe, output_folder, input_file_path.name)


class Pipeline(BaseModel):
    file_name: str = None
    folder_name: Optional[DirectoryPath] = None
    generators: dict[str, GeneratorParameters] = None

    def _next_steps(self, start_from: str = None, stop_after: str = None):
        start_from = start_from if (start_from in steps) else steps[0]
        stop_after = stop_after if (stop_after in steps) else steps[-1]

        start_from = steps.index(start_from)
        stop_after = steps.index(stop_after, start_from) + 1
        for step in steps[start_from:stop_after]:
            generator = self.generators.get(step, None)
            if generator:
                yield (step, generator)

    def run(self, start_from: str = None, stop_after: str = None):
        next_input_file: Path = (self.folder_name or FOLDER_ANSWERS) / self.file_name
        for step, generator in self._next_steps(start_from, stop_after):
            next_input_file = generator.run(step=step, input_file_path=next_input_file)
