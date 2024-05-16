#!/usr/bin/env python3

from ragtime.base.data_type import *

from ragtime.generator.prompters.base_answers import ( PptrAnsBase )
from ragtime.generator.prompters.eval_french import ( PptrEvalFR )
from ragtime.generator.prompters.fact_french import ( PptrFactsFR )
from ragtime.generator.prompters.RAG_answer_french import ( PptrAnsWithRetrieverFR )

#from ragtime.generator.prompters.simple_eval_french import ( PptrSimpleEvalFR )
#from ragtime.generator.prompters.simple_fact_french import ( PptrSimpleFactsFR )
#from ragtime.generator.prompters.two_fact_eval_french import ( PptrTwoFactsEvalFR )

prompt_table:dict = {
    "PptrAnsBase": (lambda : PptrAnsBase()),
    "PptrFactsFR": (lambda: PptrFactsFR()),
    "PptrEvalFR": (lambda: PptrEvalFR()),
    "PptrAnsWithRetrieverFR": (lambda: PptrAnsWithRetrieverFR()),
}
