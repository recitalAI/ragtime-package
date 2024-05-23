#!/usr/bin/env python3

from ragtime.base.prompter import *

from ragtime.prompters.answer.base_fr import ( PptrAnsBase )
from ragtime.prompters.answer.with_retriever import ( PptrAnsWithRetrieverFR )
from ragtime.prompters.eval.base_fr import ( PptrEvalFR )
from ragtime.prompters.fact.base_fr import ( PptrFactsFR )

table:dict = {
    "PptrAnsBase": (lambda : PptrAnsBase()),
    "PptrFactsFR": (lambda: PptrFactsFR()),
    "PptrEvalFR": (lambda: PptrEvalFR()),
    "PptrAnsWithRetrieverFR": (lambda: PptrAnsWithRetrieverFR()),
}
