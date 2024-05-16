#!/usr/bin/env python3

from ragtime.base.prompter import ( Prompter )

from ragtime.expe import ( QA, Prompt, Facts, Fact, Answer )

#class PptrSimpleFactsFR(Prompter):
#    """
#    Simple Prompter to generate Facts.
#    Asks for 1 to 5 facts in French
#    """
#    def get_prompt(self, answer:Answer) -> Prompt:
#        result:Prompt = Prompt()
#        result.user = f'{answer.llm_answer.text}'
#        result.system = "Extrait entre 3 et 5 faits décrivant le paragraphe fourni."
#        return result
#
#    def post_process(self, qa:QA, cur_obj:Facts):
#        """
#        Processes the answer returned by the LLM to return a list of Fact
#        Can be overriden to fit specific prompts
#        """
#        cur_obj.items = [Fact(text=t.strip()) for t in cur_obj.llm_answer.text.split('\n') if t.strip()]
