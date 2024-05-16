#!/usr/bin/env python3

from ragtime.base.prompter import ( Prompter )

from ragtime.expe import ( QA, Prompt, Facts, Answer, Eval )

#class PptrSimpleEvalFR(Prompter):
#    def get_prompt(self, answer:Answer, facts:Facts) -> Prompt:
#        result:Prompt = Prompt()
#        temp:str = '\n'.join(f'{i}. {fact.text}' for i, fact in enumerate(facts, start=1))
#        result.user = f'Réponse: {answer.text}\n\n{temp}'
#        result.system = """Tu dois dire pour chaque fait numérotés 1, 2, 3...s'il est présent dans la Réponse.
#        Si le fait 1 est présent dans la réponse, renvoie 1. Si le fait 2 est présent dans la réponse, renvoie 2 etc...
#        Si le fait est vrai mais qu'il n'est pas présent dans la réponse, tu ne dois pas le renvoyer."""
#        return result
#
#    def post_process(self, qa:QA, cur_obj:Eval):
#        """
#        Processes the answer returned by the LLM to return an Eval
#        Update the previously existing eval associated with the answer, if any - if None, creates a new Eval object
#        This is used to save the human eval previously entered, if any
#        Can be overriden to fit specific prompts
#        By default, the LLM is supposed to return a list of validated facts
#        """
#        text:str = cur_obj.llm_answer.text if cur_obj.llm_answer.text != "[]" else ""
#        validated_facts:list[str] = [f.strip() for f in text.split(',') if f.strip()]
#        not_validated_facts:list[str] = [str(i) for i, f in enumerate(qa.facts, start=1) if str(i) not in validated_facts]
#        cur_obj.text = f'Validated: {validated_facts} - Not validated: {not_validated_facts}'
#        cur_obj.auto = len(validated_facts) / len(qa.facts)
