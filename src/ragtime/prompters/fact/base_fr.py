#!/usr/bin/env python3

from ragtime.base.prompter import Prompter

from ragtime.base.data_type import QA, Prompt, Facts, Fact, Answer


class PptrFactsFR(Prompter):
    """
    New version of Facts Prompters
    Asks for 1 to 5 facts in French
    """

    system:str = """Génère un minimum de phrases numérotées courtes et simples qui décrivent ce paragraphe.
        Chaque phrase doit être indépendante et aucune phrase ne doit contenir la même information qu'une autre phrase.
        Les phrases ne doivent pas contenir de référence au document source ni à sa page.
        Les phrases doivent être compréhensibles seules et donc ne pas contenir de référence aux autres phrases ni nécessiter les autres phrases pour être comprises."""

    def get_prompt(self, answer: Answer) -> Prompt:
        result: Prompt = Prompt()
        result.user = f"{answer.text}"
        result.system = self.system
        return result

    def post_process(self, qa: QA, cur_obj: Facts):
        """
        Processes the answer returned by the LLM to return a list of Fact
        Can be overriden to fit specific prompts
        """
        temp_list: list[str] = [
            t.strip() for t in cur_obj.llm_answer.text.split("\n") if t.strip()
        ]
        temp_list = [
            Fact(text=f"{i}. {t}" if t[1] != "." and t[2] != "." else t)
            for i, t in enumerate(temp_list, start=1)
            if len(t) > 2
        ]
        cur_obj.items = temp_list
