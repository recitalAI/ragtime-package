from ragtime.base.llm import LiteLLM
from ragtime.base.prompter import Prompter
from ragtime.base.retriever import Retriever

from ragtime.text_generators import *
from ragtime.expe import Expe
from ragtime.config import (
    RagtimeException,
    FOLDER_ANSWERS,
    FOLDER_FACTS,
    FOLDER_EVALS,
    DEFAULT_HTML_TEMPLATE,
    DEFAULT_SPREADSHEET_TEMPLATE,
)

from pathlib import Path
from typing import Union
import toml


# Helper function
# TODO: move then in an other place
from typing import Callable, Iterable, TypeVar, Iterator

T = TypeVar("T")


def drop_while(predicate: Callable[[T], bool], iterable: Iterable[T]) -> Iterator[T]:
    iterator = iter(iterable)
    for element in iterator:
        if not predicate(element):
            yield element
            break
    for element in iterator:
        yield element


T = TypeVar("T")


def drop_until(predicate: Callable[[T], bool], iterable: Iterable[T]) -> Iterator[T]:
    iterator = iter(iterable)
    for element in iterator:
        if predicate(element):
            yield element
            break

    for element in iterator:
        yield element


T = TypeVar("T")


def keep_while(predicate: Callable[[T], bool], iterable: Iterable[T]) -> Iterator[T]:
    for element in iterable:
        yield element
        if not predicate(element):
            break


T = TypeVar("T")


def keep_until(predicate: Callable[[T], bool], iterable: Iterable[T]) -> Iterator[T]:
    for element in iterable:
        yield element
        if predicate(element):
            break


def LLMs_from_names(names: list[str], prompter: Prompter) -> list[LLM]:
    """
    names(str or list[str]):
    a list of LLM names to be instantiated as LiteLLMs the names come from https://litellm.vercel.app/docs/providers
    """
    if not prompter:
        raise RagtimeException(
            "You have to provide a Prompter in order to create LLMs from their name."
        )
    if isinstance(names, str):
        names = [names]
    return [LiteLLM(name=name, prompter=prompter) for name in names]


def run_pipeline(
    configuration: dict, start_from: str = None, stop_after: str = None
) -> dict:
    # Check if there is a folder and file name for a starting point
    # TODO: refacto the error handling + check if the folder and the file exist
    input_folder: Union[Path, str] = configuration.get("folder_name", None)
    if not input_folder:
        raise Exception("You must provide starting point folder")
    file_name: str = configuration.get("file_name", None)
    if not file_name:
        raise Exception("You must provide starting point file name")
    output_folder: Union[Path, str]

    # This table HO function are helper to instanciate the classe and methode call from a dictionary
    # TODO: break down this implementation to a PipelineConfiguration class
    #       to split the error handling from the config file and the implementation details
    #       of the pipeline implementation
    generator_table: dict[str, dict] = {
        "answers": {
            "generator": (
                lambda llms, retriever: AnsGenerator(
                    llms=llms, retriever=retriever
                ).generate
            ),
            "default_output_folder": FOLDER_ANSWERS,
        },
        "facts": {
            "generator": (lambda llms, retriever: FactGenerator(llms=llms).generate),
            "default_output_folder": FOLDER_FACTS,
        },
        "evals": {
            "generator": (lambda llms, retriever: EvalGenerator(llms=llms).generate),
            "default_output_folder": FOLDER_EVALS,
        },
    }

    # Check is the generator suite is present
    # TODO: refacto error handling
    if not configuration.get("generate", None):
        raise Exception("The pipeline must provide a generator suite")

    steps: list[str] = ["answers", "facts", "evals"]
    if start_from:
        steps = list(drop_until((lambda s: s == start_from), steps))
    if stop_after:
        steps = list(keep_until((lambda s: s == stop_after), steps))

    # loop through the step of the pipeline in this specific order
    for step in steps:
        # Skip if the step is not defined
        # NOTE: I think there is a better way to express this behavior
        step_conf: dict = configuration["generate"].get(step, None)
        if not step_conf:
            continue

        # Check if a list if LLMs is provided
        # NOTE: The AnswerGenerator is the only step that allow using multiple LLMs
        #       finding a way to better expres that.
        # TODO: error handling
        llms: list[LLM] = step_conf.get("llms", None)
        if not llms:
            raise Exception(
                f"All generator step need a list of LLM to run! Failed at step {step}"
            )

        # Get the generator
        # and if not provider get the default_output_folder associated with the current step
        generator = generator_table[step]
        output_folder = step_conf.get(
            "output_folder", generator["default_output_folder"]
        )

        # The Retriever should be closer the the AnswerGenerator
        # TODO: find an elegant way to present this relation
        retriever: Retriever = None
        if step == "answers":
            retriever = configuration.get("retriever", None)

        # Instanciate the Exporter and start the generation
        expe: Expe = Expe(json_path=input_folder / file_name)
        generator["generator"](llms, retriever)(
            expe,
            only_llms=step_conf.get("only_llms", None),
            save_every=step_conf.get("save_every", 0),
            start_from=step_conf.get("start_from", StartFrom.beginning),
            b_missing_only=step_conf.get("b_missing_only", False),
        )

        # Check if export is provided
        exports_format = step_conf.get("export", None)
        if not exports_format:
            continue

        # Run the export with the parameter provided
        for fmt in ["json", "html", "spreadsheet"]:
            fmt_parameters = exports_format.get(fmt, None)
            if not fmt_parameters:
                continue
            getattr(expe, f"save_to_{fmt}")(
                path=output_folder / file_name,
                template_path=fmt_parameters.get("path", None),
            )

        # Update the next input folder with the current output folder
        input_folder = output_folder
