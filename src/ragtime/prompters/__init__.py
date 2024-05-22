#!/usr/bin/env python3

from ragtime.base.prompter import *

from ragtime.prompters.answer_base import ( PptrAnsBase )
from ragtime.prompters.eval_fr import ( PptrEvalFR )
from ragtime.prompters.facts_fr import ( PptrFactsFR )
from ragtime.prompters.answer_with_retriever_fr import ( PptrAnsWithRetrieverFR )

prompt_table:dict = {
    "PptrAnsBase": (lambda : PptrAnsBase()),
    "PptrFactsFR": (lambda: PptrFactsFR()),
    "PptrEvalFR": (lambda: PptrEvalFR()),
    "PptrAnsWithRetrieverFR": (lambda: PptrAnsWithRetrieverFR()),
}
