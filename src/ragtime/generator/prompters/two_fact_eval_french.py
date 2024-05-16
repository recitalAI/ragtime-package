#!/usr/bin/env python3

from ragtime.base.prompter import ( Prompter )

from ragtime.expe import ( QA, Prompt, Facts, Eval )

class PptrTwoFactsEvalFR(Prompter):
    def get_prompt(self, answer_facts:Facts, gold_facts:Facts) -> Prompt:
        """
        Compares the facts extracted from the answer to evaluate (answer_facts) with the
        ground truth facts (gold_facts) to evaluate the answer
        """
        result:Prompt = Prompt()
        gold_list:str = '\n'.join(f'{chr(i + 65)}. {fact.text[3:] if fact.text[1]=="." else fact.text}' for i, fact in enumerate(gold_facts))
        answer_list:str = '\n'.join(f'{i + 1}. {fact.text[3:] if fact.text[1]=="." else fact.text}'
                                    for i, fact in enumerate(answer_facts) if len(fact.text.strip()) > 3)
        result.user = f'Liste 1:\n{gold_list}\n\nListe 2:\n{answer_list}'
        result.system = """Compare deux listes de faits (Liste 1 et Liste 2) et renvoie les faits identiques dans les deux listes.
        Les faits de la première liste sont précédés par des lettres, les faits de la seconde liste sont précédés par des chiffres.
        Assemble les lettres et les chiffres pour les faits identiques.
        Ne renvoie que des couples Lettres+Chiffres.
        Ne répète pas les phrases des listes.
        Si aucun fait n'est identique dans les deux listes, ne renvoie rien.

        Par exemple si les deux listes suivantes sont fournies, le résultat attendu est A2, B1

        Liste 1 :
        A. Les chats sont plus petits que les chiens
        B. Les chats mangent les souris
        C. Les chats vivent au plus 30 ans

        Liste 2 :
        1. Les souris sont mangées par les chats
        2. Les chiens sont la plupart du temps plus grand en taille que les chats
        3. Les chats et les chiens se disputent souvent"""
        return result

    def post_process(self, qa:QA, cur_obj:Eval):
        """
        Processes the answer returned by the LLM to return an Eval
        Assumes a list like A3, B1
        """
        text:str = cur_obj.llm_answer.text if cur_obj.llm_answer.text != "[]" else ""
        text_list:list = [t.strip() for t in text.split(',')]
        num_true_facts:int = len(qa.facts)
        num_returned_facts:int = len(cur_obj.meta["answer_facts"])
        num_true_returned:int = len(set(t[1] for t in text_list))
        cur_obj.meta["precision"] = float(num_true_returned / num_returned_facts)
        cur_obj.meta["recall"] = float(num_true_returned / num_true_facts)
        cur_obj.auto = float(2*cur_obj.meta["precision"]*cur_obj.meta["recall"] / (cur_obj.meta["precision"]+cur_obj.meta["recall"]))
        cur_obj.text = text
