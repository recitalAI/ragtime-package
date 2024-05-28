from ragtime.base.data_type import StartFrom
from ragtime.text_generators import (
    AnsGenerator,
    FactGenerator,
    EvalGenerator,
)
from ragtime.base.retriever import Retriever
from ragtime.base.llm import LLM, LiteLLM
from ragtime.prompters import Prompter, prompterTable
from ragtime.expe import Expe

from ragtime.config import (
    FOLDER_ANSWERS,
    FOLDER_FACTS,
    FOLDER_EVALS,
    DEFAULT_HTML_TEMPLATE,
    FOLDER_HTML_TEMPLATES,
    DEFAULT_SPREADSHEET_TEMPLATE,
    FOLDER_SST_TEMPLATES,
)
from pydantic import BaseModel, field_validator, ValidationInfo
from pathlib import Path
from typing import Union, Optional, List

steps: list[str] = ["answers", "facts", "evals"]

ref: dict = {}


def reference_LLM(cls, name):
    ref[name] = cls


class Export(BaseModel):
    template_file_name: Optional[str] = None
    template_folder_name: Optional[str] = None
    template_path: Optional[Union[Path, str]] = None

    def run(self, fmt: str, expe: Expe, output_folder, file_name):
        path: Path = output_folder / file_name
        exporter_table = {
            "json": {
                "exe": (lambda template_path: expe.save_to_json(path=path)),
                "folder": "",
                "path": "",
            },
            "html": {
                "exe": (
                    lambda template_path: expe.save_to_html(
                        path=path, template_path=template_path
                    )
                ),
                "folder": FOLDER_HTML_TEMPLATES,
                "path": DEFAULT_HTML_TEMPLATE,
            },
            "spreadsheet": {
                "exe": (
                    lambda template_path: expe.save_to_spreadsheet(
                        path=path, template_path=template_path
                    )
                ),
                "folder": FOLDER_SST_TEMPLATES,
                "path": DEFAULT_SPREADSHEET_TEMPLATE,
            },
        }
        data = exporter_table[fmt]
        if not self.template_path and self.template_file_name:
            folder: str = self.template_folder_name or data["folder"]
            self.template_path = folder / self.template_file_name
        elif not self.template_path:
            self.template_path = data["path"]
        data["exe"](self.template_path)


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
                llm_instance = ref.get(name, None)
                if llm_instance:
                    llm_list.append(llm_instance(prompter=prompter))
                else:
                    llm_list.append(LiteLLM(name=name, prompter=prompter))
            except:
                raise ValueError(
                    f"All name in the list must be convertible to LLM instance. {name}"
                )
        return llm_list

    only_llms: Optional[List[str]] = None
    save_every: Optional[int] = 0
    start_from: Optional[StartFrom] = StartFrom.beginning
    b_missing_only: Optional[bool] = False
    export: Optional[dict[str, Export]] = None
    output_folder: Optional[str] = None
    retriever: Optional[Retriever] = None
    num_quest: Optional[int] = 10
    docs_path: Optional[str] = None

    __generator_table: dict[str, dict] = {
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

    def run(self, step: str, folder: Path, file_name: str) -> Path:
        conf = self.__generator_table[step]
        self.output_folder: Path = self.output_folder or conf["default_output_folder"]

        expe: Expe = Expe(json_path=folder / file_name)
        conf["generator"](
            self.llms_name, self.retriever, self.num_quest, self.docs_path
        ).generate(
            expe,
            only_llms=self.only_llms,
            save_every=self.save_every,
            start_from=self.start_from,
            b_missing_only=self.b_missing_only,
        )
        for fmt, exporter in self.export.items():
            exporter.run(fmt, expe, self.output_folder, file_name)
        return self.output_folder


class Configuration(BaseModel):
    file_name: str = None
    folder_name: Optional[Union[Path, str]] = None
    generators: dict[str, GeneratorParameters] = None

    def run(self, start_from: str = None, stop_after: str = None):
        b = steps.index(start_from if start_from in steps else steps[0])
        e = steps.index(stop_after if stop_after in steps else steps[-1], b)

        input_folder: Union[Path, str] = self.folder_name or FOLDER_ANSWERS
        for step in steps[b:e]:
            if not self.generators.get(step, None):
                continue
            input_folder = self.generators[step].run(
                step=step, folder=input_folder, file_name=self.file_name
            )
