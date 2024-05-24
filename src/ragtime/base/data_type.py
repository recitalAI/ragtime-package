from enum import Enum, IntEnum
from datetime import datetime
from typing import Any, Generic, Optional, TypeVar, Union
from pydantic import BaseModel
from enum import IntEnum


class RagtimeBase(BaseModel):
    meta: dict[str, Any] = {}


class RagtimeText(RagtimeBase):
    text: str = ""


T = TypeVar("T")


class RagtimeList(RagtimeBase, Generic[T]):
    items: list[T] = []

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, item):
        return self.items[item]

    def __getitem__(self, row: int) -> T:
        return self.items[row]

    def __setitem__(self, row: int, t: T):
        self.items[row] = t

    def append(self, t: T):
        self.items.append(t)

    def __len__(self) -> int:
        return len(self.items)

    def empty(self):
        self.items = []


class Question(RagtimeText):
    pass


class Questions(RagtimeList[Question]):
    pass


class Prompt(RagtimeBase):
    user: Optional[str] = ""
    system: Optional[str] = ""


class LLMAnswer(RagtimeText):
    prompt: Optional[Prompt] = None
    name: Optional[str] = None
    full_name: Optional[str] = None
    timestamp: datetime = Optional[
        datetime
    ]  # timestamp indicating when the question has been sent to the LLM
    duration: Optional[float] = None  # time to get the answer in seconds
    cost: Optional[float] = None


class WithLLMAnswer(BaseModel):
    llm_answer: Optional[LLMAnswer] = None


class Eval(RagtimeText, WithLLMAnswer):
    """At first an Eval is made by a human, and then automatically generated from an LLM Answer"""

    human: Optional[float] = None
    auto: Optional[float] = None


class Answer(RagtimeText, WithLLMAnswer):
    eval: Optional[Eval] = Eval()


class Answers(RagtimeList[Answer]):
    pass


class Fact(RagtimeText):
    """A single fact contains only text - all the LLM data are in the Facts object
    since every single Fact is created with a single LLM generation"""

    pass


class Facts(RagtimeList[Fact], WithLLMAnswer):
    pass


class TypesWithLLMAnswer(Enum):
    answer = Answer
    facts = Facts
    eval = Eval


class Chunk(RagtimeText):
    pass


class Chunks(RagtimeList[Chunk]):
    pass


class QA(RagtimeBase):
    question: Question = Question()
    facts: Optional[Facts] = Facts()
    chunks: Optional[Chunks] = Chunks()
    answers: Optional[Answers] = Answers()

    def get_attr(self, path: str) -> list[Any]:
        """Returns the value within a QA object based on its path expressed as a string
        Useful for spreadhseets export - returns None if path is not found"""
        result: Any = self
        b_return_None: bool = False
        for a in path.split("."):
            if "[" in a:
                index: Union[str, int] = a[a.find("[") + 1 : a.rfind("]")]
                a_wo_index: str = a[: a.find("[")]

                if index.isdecimal():
                    index = int(index)  # if index is an int (list index), convert it
                elif index == "i":  # multi row
                    result = [
                        self.get_attr(path.replace("[i]", f"[{i}]"))
                        for i in range(len(getattr(result, a_wo_index)))
                    ]
                    return result
                else:  # dict (key not decimal)
                    index = index.replace('"', "").replace(
                        "'", ""
                    )  # if it is a string (dict index), remove quotes

                try:
                    result = getattr(result, a_wo_index)[index]
                except:
                    b_return_None = True
            else:
                try:
                    result = getattr(result, a)
                except:
                    b_return_None = True
            if b_return_None:
                return None

        return result


class UpdateTypes(IntEnum):
    human_eval = 0
    facts = 1


class StartFrom(IntEnum):
    beginning = 0
    chunks = 1
    prompt = 2
    llm = 3
    post_process = 4
