import litellm
litellm.telemetry = False
litellm.set_verbose = False #used for debugin purpose

#################################
## CONSTANTS

UNKOWN_LLM:str = "unkown LLM (manual ?)"
#################################

from ragtime.text_generators import *

from ragtime.config import (
    RagtimeException,
    DEFAULT_HTML_TEMPLATE,
    DEFAULT_SPREADSHEET_TEMPLATE,
    )
from ragtime.expe import ( Expe )
import ragtime.prompters

from pathlib import ( Path )
from typing import ( Union )
import toml

def LLMs_from_names(names:list[str], prompter:Prompter) -> list[LLM]:
    """
    names(str or list[str]):
    a list of LLM names to be instantiated as LiteLLMs the names come from https://litellm.vercel.app/docs/providers
    """
    if not prompter:
        raise RagtimeException('You have to provide a Prompter in order to create LLMs from their name.')
    if isinstance(names, str): names = [names]
    return [LiteLLM(name=name, prompter=prompter) for name in names]

def run_pipeline( configuration:dict ) -> dict:
    file_name:str = configuration['file_name']
    retriever:Retriever = configuration.get('retriever', None)
    if not configuration.get('generate', None):
        raise Exception("The pipeline must contain a generator suite")

    generator = {
        'answers':  (lambda llms : AnsGenerator(llms = llms, retriever = retriever) ),
        'facts':    (lambda llms : FactGenerator(llms = llms) ),
        'evals':    (lambda llms : EvalGenerator(llms = llms) ),
    }

    def exporter(exp:Expe, path:Union[str, Path]):
        return {
            'json': (lambda template_path = None: exp.save_to_json(path = path)),
            'html': (lambda template_path = None : exp.save_to_html(path = path, template_path = template_path)),
            'spreadsheet': (lambda template_path = None: exp.save_to_spreadsheet(path = path, template_path= template_path))
        }

    exporter_output:dict = dict()
    for step in ['answers', 'facts', 'evals']:
        step_conf:dict = configuration['generate'].get(step, None)
        if not step_conf:
            continue
        llms:list[LLM] = step_conf.get('llms', None)
        if not llms:
            raise Exception(f"All generator step need a list of LLM to run! Failed at step {step}")

        folder = step_conf['folder']
        expe:Expe = Expe(json_path = folder / file_name)
        generator[step](llms).generate(
            expe,
            only_llms = step_conf.get('only_llms', None),
            save_every = step_conf.get('save_every', 0),
            start_from = step_conf.get('start_from', StartFrom.beginning),
            b_missing_only = step_conf.get('b_missing_only', False),
        )
        export_to = exporter(exp = expe, path = folder / file_name)
        exports_format = step_conf.get('export', None)
        if not exports_format:
            continue

        for fmt in ['json', 'html', 'spreadsheet']:
            fmt_parameters = exports_format.get(fmt, None)
            if fmt_parameters:
                export_to[fmt](fmt_parameters['path'])
