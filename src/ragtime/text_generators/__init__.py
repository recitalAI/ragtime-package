
from ragtime.base.text_generators import *

from ragtime.text_generators.answer_generator import AnsGenerator
from ragtime.text_generators.eval_generator import EvalGenerator
from ragtime.text_generators.fact_generator import FactGenerator

def generator_dictionary(retriever:Retriever):
    return {
        'answers':  (lambda llms : AnsGenerator(llms = llms, retriever = retriever) ),
        'facts':    (lambda llms : FactGenerator(llms = llms) ),
        'evals':    (lambda llms : EvalGenerator(llms = llms) ),
    }
