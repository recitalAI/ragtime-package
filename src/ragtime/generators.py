import litellm
litellm.telemetry = False
litellm.set_verbose = False #used for debugin purpose

#################################
## CONSTANTS

UNKOWN_LLM:str = "unkown LLM (manual ?)"
#################################

from ragtime.base.llm_class import *
from ragtime.base.data_type import *
from ragtime.base.prompter import *
from ragtime.base.text_generators import *

from ragtime.config import (
    RagtimeException,
    DEFAULT_HTML_TEMPLATE,
    DEFAULT_SPREADSHEET_TEMPLATE,
    )
from ragtime.expe import ( Expe )

from ragtime.generator.text_generators.answer_generator import AnsGenerator
from ragtime.generator.text_generators.eval_generator import EvalGenerator
from ragtime.generator.text_generators.fact_generator import FactGenerator


from pathlib import ( Path )
from typing import ( Union )
import toml

def LLMs_from_names(names:list[str], prompter:Prompter) -> list[LLM]:
    """
    names(str or list[str]): a list of LLM names to be instantiated as LiteLLMs
        the names come from https://litellm.vercel.app/docs/providers
    """
    if not prompter:
        raise RagtimeException('You have to provide a Prompter in order to create LLMs from their name.')
    if isinstance(names, str): names = [names]
    return [LiteLLM(name=name, prompter=prompter) for name in names]


def path_from_conf(conf:dict) -> Path:
    path:str = input_conf['path']
    if not path:
        path = input_conf['folder'] / input_conf['fileName']
    return path

def build_from_config_file( filePath:Union[Path,str], retriever:Retriever=None ) -> dict:
    conf:dict = dict()
    with open(filePath, 'r') as file:
        fileContent:str = file.read()
        conf = toml.loads(fileContent)
    #print(parsed_toml)
    return build_from_config(conf, retriever)

"""
conf = {
    llms_names: [],
    generate: {
        answer:{
            input.path: '',
            output.path: ''
        },
        facts:{
            input.path: '',
            output.path: ''

        },
        evals:{
            input.path: '',
            output.path: '',
            b_missing_only: False,
            only_llms: [],
            save_every: True,
            export_to: {
                html:{
                    template_path: ''
                }
            }
        },
    }
}
"""

def build_from_config( conf:dict, retriever:Retriever=None, start_from:StartFrom = StartFrom.beginning ) -> dict:
    llms:list[LLM] = LLMs_from_names(conf.llms_name)
    generate = {
        'answers':  (lambda: AnsGenerator(llms = llms, retriever=retriever).generate ),
        'facts':    (lambda: FactGenerator(llms = llms).generate ),
        'evals':    (lambda: EvalGenerator(llms = llms).generate ),
    }
    def exporter(exp:Expe, path:Union[str, Path]):
        return {
            'json': (lambda template_path = None: exp.save_to_json(path = path)),
            'html': (lambda template_path = None : exp.save_to_html(path = path, template_path = template_path)),
            'spreadsheet': (lambda template_path = None: exp.save_to_spreadsheet(path = path, template_path= template_path))
        }

    exporter_output:dict = dict()
    for step in ['answers', 'facts', 'evals']:
        step_conf:dict = conf.generate[step]
        if not step_conf:
            continue

        expe:Expe = Expe(json_path = step_conf.input.path)
        export_to = exporter(expe = expe, path = step_conf.output.path)
        generate[step](
            expe,
            start_from = start_from,
            b_missing_only = step_conf.b_missing_only,
            only_llms = step_conf.only_llms,
            save_every = step_conf.save_every
        )
        for fmt in ['json', 'html', 'spreadsheet']:
            fmt = step.export_to[fmt]
            if not fmt:
                continue
            export_to[fmt](fmt.template_path)
        exporter_output[step] = expe
    return exporter_output

def run_pipeline( configuration:dict ) -> dict:
    folder:str = configuration['folder']
    file_name:str = configuration['file_name']
    retriever:Retriever = configuration['retriever']
    generate = {
        'answers':  (lambda llms: AnsGenerator(llms = llms, retriever = retriever) ),
        'facts':    (lambda llms: FactGenerator(llms = llms) ),
        'evals':    (lambda llms: EvalGenerator(llms = llms) ),
    }
    def exporter(exp:Expe, path:Union[str, Path]):
        return {
            'json': (lambda template_path = None: exp.save_to_json(path = path)),
            'html': (lambda template_path = None : exp.save_to_html(path = path, template_path = template_path)),
            'spreadsheet': (lambda template_path = None: exp.save_to_spreadsheet(path = path, template_path= template_path))
        }


    exporter_output:dict = dict()
    for step in ['answers', 'facts', 'evals']:
        step_conf:dict = configuration['generate'][step]
        if not step_conf:
            continue

        expe:Expe = Expe(json_path = folder / file_name)
        generate[step](step_conf['llms']).generate(
            expe,
            start_from = step_conf.get('start_from', StartFrom.beginning),
            b_missing_only = step_conf.get('b_missing_only', False),
            only_llms = step_conf.get('only_llms', None),
            save_every = step_conf.get('save_every', 0),

        )
        export_to = exporter(expe = expe, path = step_conf['folder'] / file_name)
        # update the folder and the file_name for the next step
        folder = step_conf['folder']
        file_name = expe.json_path.stem + '.json'
        for fmt in ['json', 'html', 'spreadsheet']:
            fmt = step['export'][fmt]
            if not fmt:
                continue
            export_to[fmt](fmt.path)
        exporter_output[step] = expe
    return exporter_output


#def generate(
#        text_generator: TextGenerator,
#        folder_in:Path,
#        folder_out:Path,
#        json_file: Union[Path,str],
#        start_from:StartFrom=StartFrom.beginning,
#        b_missing_only:bool = False,
#        only_llms:list[str] = None,
#        save_every:int=0,
#        save_to_json:bool=True,
#        save_to_html:bool=False,
#        template_html_path:Path=DEFAULT_HTML_TEMPLATE,
#        save_to_spreadsheet:bool=False,
#        template_spreadsheet_path:Path=DEFAULT_SPREADSHEET_TEMPLATE
#) -> Expe:
#
#    expe:Expe = Expe(json_path=folder_in / json_file)
#
#    text_generator.generate(
#        expe,
#        start_from=start_from,
#        b_missing_only=b_missing_only,
#        only_llms=only_llms,
#        save_every=save_every
#    )
#    if save_to_json: expe.save_to_json(path=folder_out / json_file)
#    if save_to_html: expe.save_to_html(template_path=template_html_path)
#    if save_to_spreadsheet: expe.save_to_spreadsheet(template_path=template_spreadsheet_path)
#    return expe



# TODO: the function below cannot be implemented as of now since `expe.gen_Eval` cannot be too - see TODO with expe.gen_Eval for more details
# def gen_Evals(folder_in:Path, folder_out:Path, json_file: Union[Path,str], prompter:Prompter, llm_names:list[str],
#                 start_from:StartFrom=StartFrom.beginning, b_missing_only:bool = False, only_llms:list[str] = None, save_every:int=0) -> Expe:
#   """Standard function to generate evals - returns the updated Expe or None if an error occurred"""
#   expe:Expe = Expe(json_path=folder_in / json_file)
#   expe.gen_Evals(folder_out=folder_out, prompter=prompter, llm_names=llm_names, start_from=start_from,
#                  b_missing_only=b_missing_only, only_llms=only_llms, save_every=save_every)
#   return expe
