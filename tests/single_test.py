PROJECT_NAME:str = "test_async"

from pathlib import Path
import shutil
import ragtime
from ragtime import expe, generators
from ragtime.expe import QA, Chunks, Prompt, Question, WithLLMAnswer, UpdateTypes, Answers
from ragtime.generators import StartFrom, PptrFactsFRv2, PptrEvalFRv2, PptrRichAnsFR, PptrBaseAns
from ragtime.expe import Expe

# always start with init_project before importing ragtime.config values since they are updated
# with init_project and import works by value and not by reference, so values imported before
# calling init_project are not updated after the function call
ragtime.config.init_project(name=PROJECT_NAME, init_type="globals_only")
from ragtime.config import FOLDER_ANSWERS, FOLDER_QUESTIONS, FOLDER_FACTS, FOLDER_EVALS, logger, FOLDER_SST_TEMPLATES
logger.debug('MAIN STARTS')


ragtime.config.init_win_env(['OPENAI_API_KEY', 'ALEPHALPHA_API_KEY', 'ANTHROPIC_API_KEY',
                             'COHERE_API_KEY', 'HUGGINGFACE_API_KEY', 'MISTRAL_API_KEY',
                             'NLP_CLOUD_API_KEY', 'GROQ_API_KEY'])

validation_file:str = "validation_set--30Q_0C_219F_0M_0A_0HE_0AE_2024-05-02_17h30,58.json"
# shutil.copy(src=Path('C:/Users/gilles_recital/source/repos/rag-projects/google_nq/expe/03. Facts') / validation_file,
#             dst=FOLDER_FACTS)

# expe:Expe = generators.gen_Answers(folder_in=FOLDER_FACTS,
#                                    folder_out=FOLDER_ANSWERS,
#                                    json_file=validation_file,
#                                    prompter=PptrBaseAns(),
#                                    llm_names=["gpt-4", 'vertex_ai/gemini-pro', "mistral/mistral-large-latest",
#                                               "groq/llama3-8b-8192", "groq/llama3-70b-8192",
#                                               "groq/mixtral-8x7b-32768", "groq/gemma-7b-it"])
expe:Expe = Expe(json_path=FOLDER_ANSWERS / "validation_set--30Q_0C_219F_7M_154A_0HE_0AE_2024-05-03_14h36,50.json")
expe.save_to_html()
expe.save_to_spreadsheet(template_path=FOLDER_SST_TEMPLATES / 'rich_ans_template.xlsx')