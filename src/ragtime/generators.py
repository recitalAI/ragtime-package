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

from ragtime.config import ( RagtimeException )
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

def build_from_config_file( filePath:Union[Path,str], retriever:Retriever=None ):
    conf:dict = dict()
    with open(filePath, 'r') as file:
        fileContent:str = file.read()
        conf = toml.loads(fileContent)
    print(parsed_toml)

    constructor = {
        'answers':  (lambda llms: AnsGenerator(llms = llms, retriever=retriever)),
        'facts':    (lambda llms: FactGenerator(llms = llms) ),
        'evals':    (lambda llms: EvalGenerator(llms = llms) ),
    }
    llms_list:list[LLM] = LLMs_from_names(conf['Configuration']['llms_name'])

    for step in ['answers', 'facts', 'evals']:
        step_conf:dict = conf['Generate'][step]
        expe:Expe = Expe(json_path = path_from_conf(step_conf['file']['input']))
        constructor[step](llms).generate(
            expe,
            start_from = start_from,
            b_missing_only = step_conf['b_missing_only'],
            only_llms = step_conf['only_llms'],
            save_every = step_conf['save_every']
        )
        expe.save_to_json(path = path_from_conf(step_conf['file']['output']))
    return expe

def generate(text_generator: TextGenerator, folder_in:Path, folder_out:Path, json_file: Union[Path,str],
                start_from:StartFrom=StartFrom.beginning, b_missing_only:bool = False, only_llms:list[str] = None, save_every:int=0,
                save_to_json:bool=True, save_to_html:bool=False, template_html_path:Path=DEFAULT_HTML_TEMPLATE,
                save_to_spreadsheet:bool=False, template_spreadsheet_path:Path=DEFAULT_SPREADSHEET_TEMPLATE) -> Expe:
    expe:Expe = Expe(json_path=folder_in / json_file)
    text_generator.generate(expe, start_from=start_from,  b_missing_only=b_missing_only, only_llms=only_llms, save_every=save_every)
    if save_to_json: expe.save_to_json(path=folder_out / json_file)
    if save_to_html: expe.save_to_html(template_path=template_html_path)
    if save_to_spreadsheet: expe.save_to_spreadsheet(template_path=template_spreadsheet_path)
    return expe


"""
def gen_Answers(
        folder_in:Path,
        folder_out:Path,
        json_file: Union[Path,str],

        llms:list[LLM],
        only_llms:list[str] = None,

        retriever:Retriever=None,
        start_from:StartFrom=StartFrom.beginning,
        b_missing_only:bool = False,
        save_every:int=0
) -> Expe:
  ""
  Standard function to generate answers - returns the updated Expe or None if an error occurred
  ""
  expe:Expe = Expe(json_path=folder_in / json_file)
  ans_gen:AnsGenerator = AnsGenerator(retriever=retriever, llms=llms)
  ans_gen.generate(
      expe,
      start_from=start_from,
      b_missing_only=b_missing_only,
      only_llms=only_llms,
      save_every=save_every
  )
  expe.save_to_json(path=folder_out / json_file)
  return expe


def gen_Facts(
        folder_in:Path,
        folder_out:Path,
        json_file: Union[Path,str],

        llms:list[LLM],
        only_llms:list[str] = None,

        start_from:StartFrom=StartFrom.beginning,
        b_missing_only:bool = False,
        save_every:int=0
) -> Expe:
  ""
  Standard function to generate facts - returns the updated Expe or None if an error occurred
  ""
  expe:Expe = Expe(json_path=folder_in / json_file)
  fact_gen:FactGenerator = FactGenerator(llms=llms)
  fact_gen.generate(
      expe,
      start_from=start_from,
      b_missing_only=b_missing_only,
      only_llms=only_llms,
      save_every=save_every
  )
  expe.save_to_json(path=folder_out / json_file)
  return expe


  def gen_Evals(
        folder_in:Path,
        folder_out:Path,
        json_file: Union[Path,str],

        llms:list[LLM],
        only_llms:list[str] = None,

        start_from:StartFrom=StartFrom.beginning,
        b_missing_only:bool = False,
        save_every:int=0
) -> Expe:
  ""
  Standard function to generate evals - returns the updated Expe or None if an error occurred
  ""
  expe:Expe = Expe(json_path=folder_in / json_file)
  eval_gen:EvalGenerator = EvalGenerator(llms=llms)
  eval_gen.generate(
      expe,
      start_from=start_from,
      b_missing_only=b_missing_only,
      only_llms=only_llms,
      save_every=save_every
  )
  expe.save_to_json(path=folder_out / json_file)
  return expe
"""

# def gen_Answers(folder_in:Path, folder_out:Path, json_file: Union[Path,str], prompter:Prompter, llm_names:list[str], retriever:Retriever=None,
#                 start_from:StartFrom=StartFrom.beginning, b_missing_only:bool = False, only_llms:list[str] = None, save_every:int=0,
#                 save_to_json:bool=True, save_to_html:bool=False, template_html_path:Path=DEFAULT_HTML_TEMPLATE,
#                 save_to_spreadsheet:bool=False, template_spreadsheet_path:Path=DEFAULT_SPREADSHEET_TEMPLATE) -> Expe:
#   """Standard function to generate answers - returns the updated Expe or None if an error occurred"""
#   ans_gen:AnsGenerator = AnsGenerator(retriever=retriever, llm_names=llm_names, prompter=prompter)
#   expe:Expe = Expe(json_path=folder_in / json_file)
#   ans_gen:AnsGenerator = AnsGenerator(retriever=retriever, llm_names=llm_names, prompter=prompter)
#   ans_gen.generate(expe, start_from=start_from,  b_missing_only=b_missing_only, only_llms=only_llms, save_every=save_every)
#   expe.save_to_json(path=folder_out / json_file)
#   if save_to_html: expe.save_to_html(template_path=template_html_path)
#   if save_to_spreadsheet: expe.save_to_spreadsheet(template_path=template_spreadsheet_path)
#   return expe


# def gen_Facts(folder_in:Path, folder_out:Path, json_file: Union[Path,str], prompter:Prompter, llm_names:list[str],
#                 start_from:StartFrom=StartFrom.beginning, b_missing_only:bool = False, only_llms:list[str] = None, save_every:int=0) -> Expe:
#   """Standard function to generate facts - returns the updated Expe or None if an error occurred"""
#   expe:Expe = Expe(json_path=folder_in / json_file)
#   fact_gen:FactGenerator = FactGenerator(llm_names=llm_names, prompter=prompter)
#   fact_gen.generate(expe, start_from=start_from,  b_missing_only=b_missing_only, only_llms=only_llms, save_every=save_every)
#   expe.save_to_json(path=folder_out / json_file)
#   return expe

# def gen_Evals(folder_in:Path, folder_out:Path, json_file: Union[Path,str], prompter:Prompter, llm_names:list[str],
#                 start_from:StartFrom=StartFrom.beginning, b_missing_only:bool = False, only_llms:list[str] = None, save_every:int=0) -> Expe:
#   """Standard function to generate evals - returns the updated Expe or None if an error occurred"""
#   expe:Expe = Expe(json_path=folder_in / json_file)
#   expe.gen_Evals()
#   eval_gen:EvalGenerator = EvalGenerator(llm_names=llm_names, prompter=prompter)
#   eval_gen.generate(expe, start_from=start_from,  b_missing_only=b_missing_only, only_llms=only_llms, save_every=save_every)
#   expe.save_to_json(path=folder_out / json_file)
#   return expe

# TODO: the function below cannot be implemented as of now since `expe.gen_Eval` cannot be too - see TODO with expe.gen_Eval for more details
# def gen_Evals(folder_in:Path, folder_out:Path, json_file: Union[Path,str], prompter:Prompter, llm_names:list[str],
#                 start_from:StartFrom=StartFrom.beginning, b_missing_only:bool = False, only_llms:list[str] = None, save_every:int=0) -> Expe:
#   """Standard function to generate evals - returns the updated Expe or None if an error occurred"""
#   expe:Expe = Expe(json_path=folder_in / json_file)
#   expe.gen_Evals(folder_out=folder_out, prompter=prompter, llm_names=llm_names, start_from=start_from,
#                  b_missing_only=b_missing_only, only_llms=only_llms, save_every=save_every)
#   return expe
