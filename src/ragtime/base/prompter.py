#!/usr/bin/env python3

from abc import ABC, abstractmethod
from ragtime.base.data_type import RagtimeBase, Prompt, QA, WithLLMAnswer


class Prompter(RagtimeBase, ABC):
    """
    Base Prompter class. Every Prompter must inherit from it.
    A Prompter is designed to generate prompts for Answers, Facts and Evals.
    It also contains a method to post-process text returned by an LLM, since post-processing is directly related to the prompt
    It must be provided to every LLM objects at creation time
    """
    system:str = None
    
    @abstractmethod
    def get_prompt(self) -> Prompt:
        raise NotImplementedError("Must implement this!")

    @abstractmethod
    def post_process(self, qa: QA, cur_obj: WithLLMAnswer) -> WithLLMAnswer:
        raise NotImplementedError("Must implement this!")
