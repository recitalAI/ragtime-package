from ragtime.prompters.prompter import Prompter

from ragtime.expe import QA, Prompt, Facts, Answer, Eval
from ragtime.base import div0

import re


class EvalPrompterFR(Prompter):
    """
    Prompt: FAITS and REPONSE - expect the REPONSE to be rewritten including the FACTS in the text
    Post_process: analyse cited factsfacts not cited, and facts invented (?)
    """

    system: str = """Tu dois comparer une liste numérotée de FAITS avec une REPONSE.
        Tu dois reprendre exactement la REPONSE en insérant dans le texte le numéro du FAIT auquel correspond exactement le passage ou la phrase.
        Si la phrase correspond à plusieurs FAITS, indique les entre parenthèses.
        Il ne faut pas insérer le FAIT s'il est en contradiction avec le passage ou la phrase.
        Si un passage ou une phrase dans la REPONSE ne correspond à aucun FAIT il faut mettre un point d'interrogation entre parenthèses (?)
        sauf si ce passage fait référence à un emplacement dans le document, auquel cas il ne faut rien indiquer."""

    def get_prompt(self, answer: Answer, facts: Facts) -> Prompt:
        result: Prompt = Prompt()
        facts_as_str: str = "\n".join(
            f"{i}. {fact.text}" for i, fact in enumerate(facts, start=1)
        )
        result.user = f"-- FAITS --\n{facts_as_str}\n\n-- REPONSE --\n{answer.text}"
        result.system = self.system
        return result

    def post_process(self, qa: QA, cur_obj: Eval):
        answer: str = cur_obj.llm_answer.text if cur_obj.llm_answer.text != "[]" else ""
        answer = answer.replace(
            "(FAIT ", "("
        )  # removes the word FAIT before the fact number as it is sometimes generated in the answer
        # get the set of facts numbers from answer
        facts_in_answer: set[int] = set(
            [
                int(s)
                for s in ",".join(re.findall("\([\d+,+\s+]+\)", answer))
                .replace("(", "")
                .replace(")", "")
                .split(",")
                if s
            ]
        )
        # get the numbers in the true facts
        true_facts: set[int] = set(
            [int(s.text[0] if s.text[1] == "." else s.text[:2]) for s in qa.facts if s]
        )
        true_facts_in_answer: set[int] = facts_in_answer & true_facts
        true_facts_not_in_answer: set[int] = true_facts - true_facts_in_answer
        # get the number of hallucinations (?)
        nb_false_facts_in_answer: int = len(re.findall("\(\?\)", answer))
        # compute metrics
        precision: float = div0(
            len(true_facts_in_answer), len(facts_in_answer) + nb_false_facts_in_answer
        )
        recall: float = div0(len(true_facts_in_answer), len(true_facts))
        cur_obj.meta["precision"] = precision
        cur_obj.meta["recall"] = recall
        cur_obj.meta["hallus"] = nb_false_facts_in_answer
        cur_obj.meta["missing"] = ", ".join(str(v) for v in list(true_facts_not_in_answer))
        cur_obj.meta["nb_missing"] = len(cur_obj.meta["missing"])
        cur_obj.meta["facts_in_ans"] = str(sorted(facts_in_answer))
        cur_obj.auto = div0(2 * precision * recall, precision + recall)
        cur_obj.text = answer
