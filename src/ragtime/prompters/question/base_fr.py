from ragtime.base.prompter import Prompter
import random
from ragtime.base.data_type import QA, Prompt, Question, Questions, Answer


class PptrQuestionsFR(Prompter):
    """
    Generate questin from documents
    """

    def get_prompt(self, chunk) -> Prompt:
        result: Prompt = Prompt()
        result.user = f"Les informations contextuelles sont ci-dessous: \n {chunk}"
        result.system = "Votre tâche consiste à préparer 5 questions pour un quiz/examen à venir. Les questions doivent être variées dans l'ensemble du document. Limitez les questions aux informations contextuelles fournies. Tu dois impérativement donner dans ta réponse que les questions (sans explication supplémentaire ou autre) et chaque question dans une ligne séparée(sans numérotation)."
        return result

    def post_process(self, qa: QA, cur_obj: Answer):
        """
        Processes the answer returned by the LLM to return a list of questions
        """
        temp_list: list[str] = [
            t.strip() for t in cur_obj.llm_answer.text.split("\n") if t.strip()]

        random.shuffle(temp_list)
        cur_obj.text = temp_list[0]
