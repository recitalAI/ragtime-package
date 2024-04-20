from collections import defaultdict
from enum import Enum
import json
from pathlib import Path
import re
import shutil
from openpyxl import load_workbook, Workbook
from openpyxl.worksheet.worksheet import Worksheet
from copy import copy
from datetime import datetime
from typing import Any, Callable, Generic, Optional, TypeVar, Union
from pydantic import BaseModel, Field
from ragtime.config import DEFAULT_FACTS_COL, DEFAULT_HUMAN_EVAL_COL, DEFAULT_HEADER_SIZE, DEFAULT_HUMAN_EVAL_COL, DEFAULT_ANSWERS_COL, DEFAULT_QUESTION_COL, DEFAULT_SPREADSHEET_TEMPLATE, DEFAULT_WORKSHEET, RagtimeException, logger, DEFAULT_HTML_RENDERING, DEFAULT_HTML_TEMPLATE
from jinja2 import Environment, FileSystemLoader
from tabulate import tabulate

class RagtimeBase(BaseModel):
    meta: dict[str, Any] = {}

class RagtimeText(RagtimeBase):
    text:str = ""

T = TypeVar('T')
class RagtimeList(RagtimeBase, Generic[T]):
    items: list[T] = []

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, item):
        return self.items[item]

    def __getitem__(self, row:int) -> T:
        return self.items[row]
    
    def __setitem__(self, row:int, t: T):
        self.items[row] = t
    
    def append(self, t: T):
        self.items.append(t)

    def __len__(self) -> int:
        return len(self.items)
    
    def empty(self):
        self.items = []    

class Question(RagtimeText):
    pass

class Questions(RagtimeList[Question]):
    pass

class Prompt(RagtimeBase):
    user:Optional[str] = ""
    system:Optional[str] = ""

class LLMAnswer(RagtimeText):
    prompt:Optional[Prompt] = None
    name:Optional[str] = None
    full_name:Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now())  # timestamp indicating when the question has been sent to the LLM
    duration: Optional[float] = None # time to get the answer in seconds
    cost: Optional[float] = None

class WithLLMAnswer(BaseModel):
    llm_answer:Optional[LLMAnswer] = None

class Eval(RagtimeText, WithLLMAnswer):
    """At first an Eval is made by a human, and then automatically generated from an LLM Answer"""
    human:Optional[float] = None
    auto:Optional[float] = None

class Answer(RagtimeText, WithLLMAnswer):
    eval:Optional[Eval] = Eval()

class Answers(RagtimeList[Answer]):
    pass

class Fact(RagtimeText):
    """A single fact contains only text - all the LLM data are in the Facts object
    since every single Fact is created with a single LLM generation"""
    pass

class Facts(RagtimeList[Fact], WithLLMAnswer):
    pass

class TypesWithLLMAnswer(Enum):
    answer = Answer
    facts = Facts
    eval = Eval

class Chunk(RagtimeText):
    pass

class Chunks(RagtimeList[Chunk]):
    pass

class QA(RagtimeBase):
    question:Question = Question()
    facts:Optional[Facts] = Facts()
    chunks:Optional[Chunks] = Chunks()
    answers:Optional[Answers] = Answers()

    def get_attr(self, path:str) -> list[Any]:
        """Returns the value within a QA object based on its path expressed as a string
        Useful for spreadhseets export - returns None if path is not found"""
        result:Any = self
        b_return_None:bool = False
        for a in path.split('.'):
            if "[" in a:
                index:Union[str,int] = a[a.find('[')+1:a.rfind(']')]
                a_wo_index:str = a[:a.find('[')]

                if index.isdecimal():
                    index = int(index) # if index is an int (list index), convert it
                elif index == "i": # multi row
                    result = [self.get_attr(path.replace("[i]", f"[{i}]")) for i in range(len(getattr(result, a_wo_index)))]
                    return result
                else: # dict (key not decimal)
                    index = index.replace('"', '').replace("'", '') # if it is a string (dict index), remove quotes

                try:
                    result = getattr(result, a_wo_index)[index]
                except:
                    b_return_None = True
            else:
                try:
                    result = getattr(result, a)
                except:
                    b_return_None = True
            if b_return_None:
                return None

        return result

class Expe(RagtimeList[QA]):
    meta:Optional[dict] = {}
    json_path:Path = Field(None, exclude=True)

    def __init__(self, json_path:Path=None):
        super().__init__()
        if json_path:
            self.json_path = json_path
            self.load_from_json(path=json_path)

    def stats(self) -> dict:
        """Returns stats about the expe : nb models, nb questions, nb facts, nb answers, nb human eval, nb auto eval"""
        res:dict = {}
        res['questions'] = len([qa for qa in self if qa.question.text])
        res['chunks'] = len([c for qa in self for c in qa.chunks if c])
        res['facts'] = len([f for qa in self for f in qa.facts if f])
        res['models'] = len(self[0].answers)
        res['answers'] = len([a for qa in self for a in qa.answers if a.text])
        res['human eval'] = len([a for qa in self for a in qa.answers if a.eval and a.eval.human])
        res['auto eval'] = len([a for qa in self for a in qa.answers if a.eval and a.eval.auto])
        return res
            
    def get_name(self) -> str:
        """Returns the name of the Expe based on the number of questions, answers..."""
        date_to_time_format:str = "%Y-%m-%d_%Hh%M,%S"
        stats:dict = self.stats()
        name:str = f'{stats["questions"]}Q_{stats["chunks"]}C_{stats["facts"]}F_{stats["models"]}M_{stats["answers"]}A_{stats["human eval"]}HE_{stats["auto eval"]}AE_{datetime.now().strftime(date_to_time_format)}'
        return name

    def _file_check_before_writing(self, path:Path, b_overwrite:bool=False, b_add_suffix:bool = True, force_ext:str=None) -> Path:
        # Make sure at least 1 QA is here
        if len(self) == 0:
            raise Exception("""The Expe object you're trying to write is empty! Please add at least one QA""")
        
        # Check and prepare the destination file path
        if not(path):
            raise Exception("""No file defined - please specify a file name to save the Expe into""")
        
        # If the provided path is a string, convert it to a Path
        result_path = Path(path) if isinstance(path, str) else path

        # If a suffix is to be added, add it
        if b_add_suffix:
            file_no_ext:str = result_path.stem
            # genrates the new suffix like --5M_50Q_141F_50A_38HE
            sep:str = "--"
            new_suf:str = self.get_name()
            if file_no_ext.find(sep) != -1: # if already a suffix, replace it
                old_suf:str = file_no_ext[file_no_ext.find(sep)+len(sep):]
                file_no_ext = file_no_ext.replace(old_suf, new_suf)
            else:
                file_no_ext = f'{file_no_ext}{sep}{new_suf}'
            str_name:str = f'{file_no_ext}{result_path.suffix}'
            result_path = result_path.parent / Path(str_name)            

        # Force ext
        if force_ext:
            if result_path.suffix: # if already an extension, replace it
                result_path = Path(str(result_path).replace(result_path.suffix, force_ext))
            else: # if no extension, just add it
                result_path = Path(f'{result_path}{force_ext}')
        
        # If path exists and overwrite not allowed, raise an Exception
        if result_path.is_file() and not b_overwrite: 
            raise FileExistsError(f'"{path}" already exists! Set b_overwrite=True to allow overwriting.')

        return result_path

    def save_temp(self, name:str = "TEMP_"):
        '''Save the expe as is as a temporary backup. Useful to save the work already done
        when an Exception occurs or if you want to create intermediate backups while computing.'''
        if self.json_path:
            file_name:str = f'{name}{self.json_path.stem}'
            file_path:str = self.json_path.parent
        else:
            file_name:str = f'{name}.json'
            file_path:str = ''
        self.save_to_json(path=Path(file_path) / Path(file_name), b_overwrite=True, b_add_suffix=True)

    def load_from_json(self, path:Path):
        with open(path, mode="r", encoding="utf-8") as file:
            data:list = json.load(file)
            qa_list:dict = data
            if 'meta' in data:
                self.meta = data['meta']
                qa_list = data['items']
            for json_qa in qa_list:
                qa:QA = QA(**json_qa)
                self.append(qa)
   
    def update_from_spreadsheet(self, path:Path, sheet_name:str = DEFAULT_WORKSHEET,
                                question_col:int=DEFAULT_QUESTION_COL,
                                facts_col:int=DEFAULT_FACTS_COL,
                                answers_col:int=DEFAULT_ANSWERS_COL,
                                human_eval_col:int=DEFAULT_HUMAN_EVAL_COL):
        # Load Human Evaluations from a Spreadsheet
        # Assumes a spreadhseet formatted like "spreadsheet_multi_rows_template.xlsx", so:
        # Question column is B
        # Facts column is D
        # LLM name column is J
        # Human eval column is O
        def find_row(ws:Worksheet, row:int, column:int, val_to_find:str):
            return next((r+1 for r in range(row, ws.max_row) if ws.cell(row=r+1, column=column).value.lower() == val_to_find.lower()), None)
        
        def find_next(ws:Worksheet, row:int, column:int):
            return next((r+1 for r in range(row, ws.max_row) if ws.cell(row=r+1, column=column).value), None)

        wb:Workbook = load_workbook(path)
        ws:Worksheet = wb[sheet_name]

        # For each question in the current Expe object
        for qa in self:
            # find the corresponding question in the spreadsheet
            q_row:int = find_row(ws=ws, row=1, column=question_col, val_to_find=qa.question.text)
            if q_row:
                # update human evaluations
                for ans in qa.answers:
                    ans_row:int = find_row(ws=ws, row=q_row, column=answers_col, val_to_find=ans.text)
                    if ans_row:
                        human_eval:int = int(ws.cell(row=ans_row, column=human_eval_col).value)
                        ans.eval.human = human_eval
                # update facts list 
                new_facts:Facts = Facts()
                for fact in qa.facts:
                    fact_row:int = find_row(ws=ws, row=q_row, column=facts_col, val_to_find=fact.text)
                    if fact_row: # fact still exists -> keep it
                        new_facts.append(fact)
                qa.facts = new_facts
                # add facts added in the spreadsheet
                next_q_row:int = find_next(ws=ws, row=q_row, column=question_col)
                if not next_q_row: next_q_row = ws.max_row
                fact_list:list[str] = [f.text.lower() for f in qa.facts]
                for r in range(q_row, next_q_row):
                    fact_text:str = ws.cell(row=r, column=facts_col).value
                    if fact_text.lower() not in fact_list:
                        qa.facts.append(Fact(text=fact_text))

    def save_to_json(self, path:Path=None, b_overwrite:bool=False, b_add_suffix:bool = True) -> Path:
        """Saves Expe to JSON - can generate a suffix for the filename
        Returns the Path of the file actually saved"""
        if not path:
            if self.json_path:
                path = Path(self.json_path.parent) / self.json_path.stem
            else:
                raise RagtimeException(f'Cannot save to JSON since no json_path is stored in expe and not path has been provided in argument.')        
        path:Path = self._file_check_before_writing(path, b_overwrite=b_overwrite, 
                                                    b_add_suffix=b_add_suffix, force_ext='.json')
        with open(path, mode='w', encoding='utf-8') as file:
            file.write(self.model_dump_json(indent=2))
        logger.info(f'Expe saved as JSON to {path}')
        return path

    def save_to_html(self, path:Path, render_params:dict[str,bool]=DEFAULT_HTML_RENDERING,
                     template_path:Path=DEFAULT_HTML_TEMPLATE, b_overwrite:bool=False, b_add_suffix:bool = True):
        """Saves Expe to an HTML file from a Jinja template - can generate a suffix for the filename
        Returns the Path of the file actually saved"""
        path:Path = self._file_check_before_writing(path, b_overwrite=b_overwrite, b_add_suffix=b_add_suffix, force_ext='.html')
        environment = Environment(loader=FileSystemLoader(searchpath=template_path.parent,encoding='utf-8'))
        template = environment.get_template(template_path.name)
        context = {"expe": self, **render_params, "report_name": self.get_name(), "sub": (lambda pattern, repl, s: re.sub(pattern, repl, s))}
        with open(path, mode='w', encoding='utf-8') as file:
            file.write(template.render(context))
        logger.info(f'Expe saved as HTML to {path}')
        return path

    def save_to_spreadsheet(self, path:Path, template_path:Path=DEFAULT_SPREADSHEET_TEMPLATE,
                            header_size:int=DEFAULT_HEADER_SIZE, sheet_name:str = DEFAULT_WORKSHEET,
                            b_overwrite:bool=False, b_add_suffix:bool = True):
        """Saves Expe to a spreadsheet - can generate a suffix for the filename
        Returns the Path of the file actually saved"""
        path:Path = self._file_check_before_writing(path, b_overwrite=b_overwrite, b_add_suffix=b_add_suffix, force_ext='.xlsx')
        
        # Prepare the result file
        # Copy template
        shutil.copy(template_path, path)
        wb:Workbook = load_workbook(path)
        wb.iso_dates = True
        
        # Create worksheet
        ws:Worksheet = wb[sheet_name]

        # Retreive sst configuration from original file
        # ws_conf is a list of str, each element describes the path of the data to be added in the current row
        ws_conf:list[str] = [cell.value for cell in ws[header_size+1]]
        
        # Write the values at specific rows - they are defined in second row, below the one describing the value to insert
        for cell in ws[header_size+2]: # read the row just after the conf row - it contains configuration for specific rows
            # if a value is present, analyse it - it should contain a "row" indication e.g. "answers[0].full_name, row=1"
            if cell.value:
                if cell.value == "#": continue # special token # used to indicate question number
                val:str = cell.value
                row:int = int(val[val.find('row=')+len('row='):])
                if row < 1: raise RagtimeException(f'The row value "row={row}" specified in cell {cell.coordinate} is invalid and must be greater than 0')
                # write the value since it does not need to be done for each row
                p:str = val[:val.find(',')]
                # get the first non empty value in the required column
                val = next((qa.get_attr(p) for qa in self if qa.get_attr(p)), "")
                ws.cell(row=row, column=cell.column, value=val)

        qa:QA
        row:int = header_size+1
        col_with_formulas:dict[int, str] = {c: ws.cell(column=c, row=row).value
                                            for c in range(1, ws.max_column) if ws.cell(column=c, row=row).value[0] == "="}
        for num_q, qa in enumerate(self, start=1): # write each row in expe
            next_row:int = 0
            for col, p in enumerate(ws_conf, start=1):
                if p == "#": # special token # used to indicate question number
                    val = [num_q]
                elif p[0] == "=": # if a formula is here, write it as is in the formula field
                    continue
                else: # if it is a path to get a value in QA, get it
                    # Get value in the QA object
                    val = qa.get_attr(p)
                    if val is None or val == []: val = [""] # write a blank if nothing is found
                if not isinstance(val, list): val = [val]
                
                # Write the value(s)
                for offset, v in enumerate(val):
                    # Do standard conversions to string
                    if isinstance(v, list): v = str(v)
                    elif isinstance(v, datetime): v = v.strftime("%d/%m/%Y %H:%M:%S")
                    # Write value
                    ws.cell(row=row+offset, column=col).value = v
                    # From second row copy cell style from the one up
                    if row+offset > header_size+1:
                        ws.cell(row=row+offset, column=col)._style = copy(ws.cell(row=header_size+1, column=col)._style)
                
                next_row = max(next_row, row+offset+1)
            row = next_row

        # extend the formulas
        for row in range(header_size+1, ws.max_row):
            for col, formula in col_with_formulas.items():
                # simply adjust the row number in the formula
                cell_refs:set = set(re.findall(r"[A-Z]+[0-9]+", formula))
                for cell_ref in cell_refs:
                    new_cell_ref:str = cell_ref.replace(str(header_size+1), str(row))
                    formula = formula.replace(cell_ref, new_cell_ref)
                ws.cell(row=row, column=col, value=formula)
        
        # save spreadsheet
        wb.save(path)
        logger.info(f'Expe saved as Spreadsheet to {path}')
        return path
    
def analyse_expe_folder(path:Path):
    if not path.is_dir(): raise Exception(f'"{path}" is not a folder - please provide one')
    print(f'In "{path}":')
    res:defaultdict = defaultdict(list)
    for f in [f for f in path.iterdir() if f.is_file() and f.suffix == '.json']:
        exp:Expe = Expe(json_path=f)
        res['File'].append(f.name)
        for k, v in exp.stats(): res[k].append(v)

    print(tabulate(res, headers="keys"))

def export_to_html(json_path:Path, render_params:dict[str,bool]=DEFAULT_HTML_RENDERING,
                     template_path:Path=DEFAULT_HTML_TEMPLATE):
  expe:Expe = Expe(json_path=json_path)
  expe.save_to_html(path=json_path, render_params=render_params, template_path=template_path, b_add_suffix=True)

def export_to_spreadsheet(json_path:Path, template_path:Path=DEFAULT_SPREADSHEET_TEMPLATE,
                            header_size:int=DEFAULT_HEADER_SIZE, sheet_name:str = DEFAULT_WORKSHEET,):
  expe:Expe = Expe(json_path=json_path)
  expe.save_to_spreadsheet(path=json_path, template_path=template_path, header_size=header_size, sheet_name=sheet_name, b_add_suffix=True)