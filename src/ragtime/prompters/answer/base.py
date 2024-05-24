#!/usr/bin/env python3

from ragtime.base.prompter import Prompter

from ragtime.base.data_type import QA, Prompt, Question, Chunks, Answer

from typing import Optional


class PptrAnsBase(Prompter):
    """
    This simple prompter just send the question as is to the LLM
    and does not perform any post-processing
    """

    def get_prompt(self, question: Question, chunks: Optional[Chunks] = None) -> Prompt:
        result: Prompt = Prompt()
        result.user = f"{question.text}"
        result.system = ""
        return result

    def post_process(self, qa: QA = None, cur_obj: Answer = None):
        """
        Does not do anything by default, but can be overridden to add fields in meta data for instance
        """
        cur_obj.text = cur_obj.llm_answer.text
