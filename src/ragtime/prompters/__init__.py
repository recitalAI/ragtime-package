#!/usr/bin/env python3

from ragtime.base.prompter import Prompter

from ragtime.prompters.answer.base import PptrAnsBase
from ragtime.prompters.answer.with_retriever import PptrAnsWithRetrieverFR
from ragtime.prompters.fact.base_fr import PptrFactsFR
from ragtime.prompters.eval.base_fr import PptrEvalFR

prompterTable: dict = {
    "PptrAnsBase": PptrAnsBase,
    "PptrFactsFR": PptrFactsFR,
    "PptrEvalFR": PptrEvalFR,
    "PptrAnsWithRetrieverFR": PptrAnsWithRetrieverFR,
}


def reference_Prompter(name, cls):
    prompterTable[name] = cls
