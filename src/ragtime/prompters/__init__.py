#!/usr/bin/env python3

from ragtime.base.prompter import *

from ragtime.prompters.answer.base import PptrAnsBase
from ragtime.prompters.answer.with_retriever import PptrAnsWithRetrieverFR
from ragtime.prompters.fact.base_fr import PptrFactsFR
from ragtime.prompters.eval.base_fr import PptrEvalFR
from ragtime.prompters.question.base_fr import PptrQuestionsFR

table: dict = {
    "PptrQuestionsFR": (lambda: PptrQuestionsFR()),
    "PptrAnsBase": (lambda: PptrAnsBase()),
    "PptrFactsFR": (lambda: PptrFactsFR()),
    "PptrEvalFR": (lambda: PptrEvalFR()),
    "PptrAnsWithRetrieverFR": (lambda: PptrAnsWithRetrieverFR()),
}
