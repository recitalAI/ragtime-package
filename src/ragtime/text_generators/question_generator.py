from pathlib import Path
import random
from ragtime.config import logger
from ragtime.base.text_generator import *
from ragtime.base.rag import read_doc
from ragtime.base.data_type import QA, Chunk, Question, Answer
from llama_index.core import Document


class QuestionGenerator(TextGenerator):
    """
    Generate Questions from a set of documents.
    """
    docs_path: Path = None
    nb_quest: int = 10
    docs: list[Document] = []
    expe: Expe = Expe()

    def __init__(self, nb_quest: int, docs_path: Path, llms: list[LLM] = None):

        super().__init__(llms=llms)
        self.nb_quest = nb_quest
        if docs_path:
            self.docs_path = docs_path
            self.add_documents()

    def add_documents(self):

        documents = read_doc(name=self.docs_path)
        random.shuffle(documents)
        documents = documents[:min(self.nb_quest, len(documents))]
        for doc in documents:
            # Create a new QA object for each question
            qa: QA = QA()
            qa.question.meta = {"Node id": doc.id_} | doc.metadata | {
                'chunk': doc.text}
            self.expe.append(qa)

        self.docs = documents

    # def generate(
    #     self,
    #     expe: Expe,
    #     save_every: int = 0,
    #     b_missing_only: bool = False,
    #     only_llms: list[str] = None,
    #     start_from: StartFrom = StartFrom.beginning,
    # ):

    #     super().generate(
    #         expe=self.expe,
    #         save_every=save_every,
    #         b_missing_only=b_missing_only,
    #         only_llms=only_llms,
    #         start_from=start_from,
    #     )

    async def gen_for_qa(
        self,
        qa: QA,
        start_from: StartFrom = StartFrom.beginning,
        b_missing_only: bool = False,
        only_llms: list[str] = None
    ):

        original_prefix: str = logger.prefix
        logger.prefix = f"{original_prefix}[QestGen][{self.llms[0].name}]"
        logger.info(f"* Start question generation")
        prev_question: Question = qa.question
        qa.question = await self.llm.generate(
            cur_obj=Question(),
            prev_obj=prev_question,
            qa=qa,
            start_from=start_from,
            b_missing_only=b_missing_only,
            chunk=qa.question.meta['chunk'],
        )
        qa.question.meta = prev_question.meta
