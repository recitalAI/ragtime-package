from abc import ABC, abstractmethod
from pathlib import Path
from langdetect import detect
import json
from unidecode import unidecode
from enum import IntEnum
from typing import Optional, Union
from ragtime.expe import Answer, Answers, Chunks, Eval, Expe, Fact, Facts, LLMAnswer, Question, RagtimeBase, QA, Prompt, WithLLMAnswer
from litellm import completion_cost, acompletion
from ragtime.config import RagtimeException, logger, div0
import re
import asyncio

import litellm
litellm.telemetry = False

#################################
## CONSTANTS
#################################
UNKOWN_LLM:str = "unkown LLM (manual ?)"

#################################
## RETREIVER
#################################
class Retriever(RagtimeBase):
    """
    Retriever abstract class
    The `retrieve` method must be implemented
    The LLM must be given as a list of string from https://litellm.vercel.app/docs/providers
    """
    @abstractmethod
    def retrieve(self, qa: QA):
        """Retrurns the Chunks from a Question and writes them in the QA object"""
        raise NotImplementedError('Must implement this!')


#################################
## PROMPTER + PROMPTERS
#################################
class Prompter(RagtimeBase, ABC):
    """Base Prompter class. Every Prompter must inherit from it.
    A Prompter is designed to generate prompts for Answers, Facts and Evals.
    It also contains a method to post-process text returned by an LLM, since post-processing is directly related to the prompt
    It must be provided to every LLM objects at creation time"""

    @abstractmethod
    def get_prompt(self) -> Prompt:
        raise NotImplementedError('Must implement this!')

    @abstractmethod
    def post_process(self, qa:QA, cur_obj:WithLLMAnswer) -> WithLLMAnswer:
        raise NotImplementedError('Must implement this!')

class PptrBase(Prompter):
    """This simple prompter just send the question as is to the LLM
    and does not perform any post-processing"""
    def get_prompt(self, question:Question, chunks:Optional[Chunks] = None) -> Prompt:
        result:Prompt = Prompt()
        result.user = f'{question.text}'
        result.system = ""
        return result
    
    def post_process(self, qa:QA=None, cur_obj:Answer=None):
        """Does not do anything by default, but can be overridden to add fields in meta data for instance"""
        cur_obj.text = cur_obj.llm_answer.text

class PptrRichAnsFR(Prompter):
    """This prompter uses a prompt asking the LLM to generate a JSON structure
    and includes chunks in its prompt. It performs post-processing to exploit
    the JSON structure the LLM is supposed to generate."""
    FLD_QUEST_OK:str = "q_ok"
    FLD_CHUNKS_OK:str = "chunks_ok"
    FLD_ANSWER:str = "answer" 

    def get_prompt(self, question:Question, chunks:Optional[Chunks] = None) -> Prompt:
        """This Answer prompt asks for a JSON answer"""

        # Format string to convert a chunk into a string
        fmt_chunk_to_str:str = """- {title} (p. {page})
        {text}"""
        
        # Format string to join the strings representing the different chunks
        str_joint:str = "\n\n"
        
        # Format string to convert the string containing all the chunks to a user prompt
        fmt_chunks_to_user_msg:str = """{chunks}
        La question est '{question}'""" 

        # System prompt
        system_msg:str = f"""Tu es un expert qui doit répondre à des questions à l'aide de paragraphes qui te sont fournis.
        Tu dois utiliser uniquement ces paragraphes pour répondre aux questions.
        Tu dois inclure les titres exacts de ces paragraphes dans la réponse que tu renvoies.
        Tu dois justifier tes réponses et expliquer comment tu les as construites.
        Tu dois détailler les phrases et les mots qui te permettent de générer ta réponse.

        Les paragraphes sont présentés ainsi :
        - Titre (Page X)
        Contenu

        La réponse générée doit indiquer clairement la source avec le Titre et la Page.

        La réponse doit utiliser le format JSON suivant :
        {{
        "{self.FLD_QUEST_OK}": 0 ou 1,
        "{self.FLD_CHUNKS_OK}": 0 ou 1,
        "{self.FLD_ANSWER}": une chaîne de caractères contenant la réponse
        }}

        Le champ "{self.FLD_QUEST_OK}" vaut 0 si la question n'est pas claire, 1 sinon.
        Le champ "{self.FLD_CHUNKS_OK}" vaut 0 si les paragraphes fournis ne permettent pas de répondre à la question, 1 sinon.
        Le champ "{self.FLD_ANSWER}" contient la réponse."""

        result:Prompt = Prompt()
        # Compute the user prompt
        chunks_as_list:list[str] = [fmt_chunk_to_str.format(title=chunk.meta['display_name'],
                                                                 page=chunk.meta['page_number'],
                                                                 text=chunk.text) for chunk in chunks]
        chunks_as_str:str = str_joint.join(chunks_as_list)
        result.user = fmt_chunks_to_user_msg.format(chunks=chunks_as_str, question=question.text)

        # Get the system prompt
        result.system = system_msg        

        return result

    def post_process(self, qa:QA, cur_obj:Answer):
        """Do JSON post processing (i.e. tries to extract correct JSON in an incorrect
        format) and finds the sources chunks quoted in the generated answer"""
        
        def fmt_name(a_str:str) -> str:
            """Internal function used to format the documents' references"""
            result: str = unidecode(a_str)
            rep_str:list[tuple(str, str)] = [ # type: ignore
                ('a la page', 'p'), ('aux pages', 'p'), ('page', 'p'), 
                (' ', ''), ('.pdf', ''), ('.pptx', ''), ('.', ''), ("'", ''), ('"', ''),
                ('(', ''), (')', ''), (',', ''),
                ('-', ''), ]
            for c in rep_str: result = result.replace(*c)
            return result
        
        # deprecated answer.text_field = "answer" # tells the Answer to fetch the value from the meta "answer", not the original "text" field
        # which contains the raw text returned by the LLM in this case
        json_ok: bool = False
        # test JSON and tries to extract fields if needed
        json_ans:dict = {}
        if not cur_obj.llm_answer:
            logger.error(f'Nothing to post-process! LLMAnswer is None for current Answer!')
            return
        cur_obj.text = cur_obj.llm_answer.text
        try:
            json_ans:dict = json.loads(cur_obj.text)
            json_ok = True
        except:
            ans_text:str = cur_obj.text[cur_obj.text.find('{'):cur_obj.text.find('}')+1]
            ans_text = ans_text.replace('\n', '').replace('\\','').replace('   ', ' ')
            ans_text = ans_text.replace("'}", '"}')
            t:str = ans_text
            p1:int = t.find(f'"{self.FLD_ANSWER}"') + len(f'"{self.FLD_ANSWER}": "')
            p2:int = t.rfind('"')
            ans_text = t[:p1] + t[p1:p2].replace('"', "'") + t[p2:]
            try:
                json_ans = json.loads(ans_text)
                json_ok = True
            except:
                pass
        
        # Fills the fields with values from the returned JSON if ok
        cur_obj.meta['json_ok'] = json_ok
        cur_obj.meta['question_ok'] = bool(json_ans[self.FLD_QUEST_OK]) if json_ok else None
        cur_obj.meta['chunks_ok'] = bool(json_ans[self.FLD_CHUNKS_OK]) if json_ok else None
        cur_obj.text = json_ans[self.FLD_ANSWER] if json_ok else cur_obj.llm_answer.text

        # Get Answers's lang
        try:
            lang:str = detect(cur_obj.llm_answer.text)
            cur_obj.meta['lang'] = lang
        except:
            cur_obj.meta['lang'] = None

        # Calc nb sources in answer even if the JSON is not formatted well
        ans_formatted:str = fmt_name(cur_obj.llm_answer.text)
        docs_in_chunks:dict[str, str] = {c.meta["display_name"]: 
                                            fmt_name(c.meta["display_name"])
                                            for c in qa.chunks}
        docs_page_in_chunks:dict[str] = {f'{c.meta["display_name"]} p.{c.meta["page_number"]}':
                                            fmt_name(f'{c.meta["display_name"]}p.{c.meta["page_number"]}')
                                            for c in qa.chunks}
        cur_obj.meta['docs_in_ans'] = [orig_name for (orig_name, fmt_name) 
                                    in docs_in_chunks.items() 
                                    if fmt_name in ans_formatted]
        cur_obj.meta['docs_and_page_in_ans'] = [orig_name for (orig_name, fmt_name) 
                                        in docs_page_in_chunks.items() 
                                        if fmt_name in ans_formatted]

class PptrSimpleFactsFR(Prompter):
    """Simple Prompter to generate Facts.
    Asks for 1 to 5 facts in French"""
    def get_prompt(self, answer:Answer) -> Prompt:
        result:Prompt = Prompt()
        result.user = f'{answer.llm_answer.text}'
        result.system = "Extrait entre 3 et 5 faits décrivant le paragraphe fourni."
        return result
    
    def post_process(self, qa:QA, cur_obj:Facts):
        """Processes the answer returned by the LLM to return a list of Fact
        Can be overriden to fit specific prompts"""
        cur_obj.items = [Fact(text=t.strip()) for t in cur_obj.llm_answer.text.split('\n') if t.strip()]

class PptrFactsFRv2(Prompter):
    """New version of Facts Prompters 
    Asks for 1 to 5 facts in French"""
    def get_prompt(self, answer:Answer) -> Prompt:
        result:Prompt = Prompt()
        result.user = f'{answer.text}'
        result.system = """Génère un minimum de phrases numérotées courtes et simples qui décrivent ce paragraphe.
        Chaque phrase doit être indépendante et aucune phrase ne doit contenir la même information qu'une autre phrase.
        Les phrases ne doivent pas contenir de référence au document source ni à sa page.
        Les phrases doivent être compréhensibles seules et donc ne pas contenir de référence aux autres phrases ni nécessiter les autres phrases pour être comprises."""
        return result
    
    def post_process(self, qa:QA, cur_obj:Facts):
        """Processes the answer returned by the LLM to return a list of Fact
        Can be overriden to fit specific prompts"""
        temp_list:list[str] = [t.strip() for t in cur_obj.llm_answer.text.split('\n') if t.strip()]
        temp_list = [Fact(text=f'{i}. {t}' if t[1] != '.' and t[2] != '.' else t) for i, t in enumerate(temp_list, start=1) if len(t)>2]
        cur_obj.items = temp_list

class PptrEvalFRv2(Prompter):
    """
    Prompt: FAITS and REPONSE - expect the REPONSE to be rewritten including the FACTS in the text
    Post_process: analyse cited factsfacts not cited, and facts invented (?)"""
    def get_prompt(self, answer:Answer, facts:Facts) -> Prompt:
        result:Prompt = Prompt()
        facts_as_str:str = '\n'.join(f'{i}. {fact.text}' for i, fact in enumerate(facts, start=1))
        result.user = f'-- FAITS --\n{facts_as_str}\n\n-- REPONSE --\n{answer.text}'
        result.system = """Tu dois comparer une liste numérotée de FAITS avec une REPONSE.
        Tu dois reprendre exactement la REPONSE en insérant dans le texte le numéro du FAIT auquel correspond exactement le passage ou la phrase.
        Si la phrase correspond à plusieurs FAITS, indique les entre parenthèses.
        Il ne faut pas insérer le FAIT s'il est en contradiction avec le passage ou la phrase.
        Si un passage ou une phrase dans la REPONSE ne correspond à aucun FAIT il faut mettre un point d'interrogation entre parenthèses (?) 
        sauf si ce passage fait référence à un emplacement dans le document, auquel cas il ne faut rien indiquer."""
        return result

    def post_process(self, qa:QA, cur_obj:Eval):
        answer:str = cur_obj.llm_answer.text if cur_obj.llm_answer.text != "[]" else ""
        answer = answer.replace('(FAIT ', '(') # removes the word FAIT before the fact number as it is sometimes generated in the answer
        # get the set of facts numbers from answer
        facts_in_answer:set[int] = set([int(s) for s in ','.join(re.findall('\([\d+,+\s+]+\)',answer)).replace('(','').replace(')','').split(',') if s])
        # get the numbers in the true facts
        true_facts:set[int] = set([int(s.text[0] if s.text[1] == '.' else s.text[:2]) for s in qa.facts if s])
        true_facts_in_answer:set[int] = facts_in_answer & true_facts
        true_facts_not_in_answer:set[int] = true_facts - true_facts_in_answer
        # get the number of hallucinations (?)
        nb_false_facts_in_answer:int = len(re.findall("\(\?\)", answer))
        # compute metrics
        precision:float = div0(len(true_facts_in_answer), len(facts_in_answer)+nb_false_facts_in_answer)
        recall:float = div0(len(true_facts_in_answer), len(true_facts))
        cur_obj.meta["precision"] = precision
        cur_obj.meta["recall"] = recall
        cur_obj.meta["hallus"] = nb_false_facts_in_answer
        cur_obj.meta["missing"] = ', '.join(list(true_facts_not_in_answer))
        cur_obj.meta["facts_in_ans"] = str(sorted(facts_in_answer))
        cur_obj.auto = div0(2*precision*recall, precision+recall)
        cur_obj.text = answer

class PptrSimpleEvalFR(Prompter):
    def get_prompt(self, answer:Answer, facts:Facts) -> Prompt:
        result:Prompt = Prompt()
        temp:str = '\n'.join(f'{i}. {fact.text}' for i, fact in enumerate(facts, start=1))
        result.user = f'Réponse: {answer.text}\n\n{temp}'
        result.system = """Tu dois dire pour chaque fait numérotés 1, 2, 3...s'il est présent dans la Réponse.
        Si le fait 1 est présent dans la réponse, renvoie 1. Si le fait 2 est présent dans la réponse, renvoie 2 etc...
        Si le fait est vrai mais qu'il n'est pas présent dans la réponse, tu ne dois pas le renvoyer."""
        return result

    def post_process(self, qa:QA, cur_obj:Eval):
        """Processes the answer returned by the LLM to return an Eval
        Update the previously existing eval associated with the answer, if any - if None, creates a new Eval object
        This is used to save the human eval previously entered, if any
        Can be overriden to fit specific prompts
        By default, the LLM is supposed to return a list of validated facts"""
        text:str = cur_obj.llm_answer.text if cur_obj.llm_answer.text != "[]" else ""
        validated_facts:list[str] = [f.strip() for f in text.split(',') if f.strip()]
        not_validated_facts:list[str] = [str(i) for i, f in enumerate(qa.facts, start=1) if str(i) not in validated_facts]
        cur_obj.text = f'Validated: {validated_facts} - Not validated: {not_validated_facts}'
        cur_obj.auto = len(validated_facts) / len(qa.facts)

class PptrTwoFactsEvalFR(Prompter):
    def get_prompt(self, answer_facts:Facts, gold_facts:Facts) -> Prompt:
        """Compares the facts extracted from the answer to evaluate (answer_facts) with the
        ground truth facts (gold_facts) to evaluate the answer"""
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
        """Processes the answer returned by the LLM to return an Eval
        Assumes a list like A3, B1"""
        text:str = cur_obj.llm_answer.text if cur_obj.llm_answer.text != "[]" else ""
        text_list:list = [t.strip() for t in text.split(',')]
        num_true_facts:int = len(qa.facts)
        num_returned_facts:int = len(cur_obj.meta["answer_facts"])
        num_true_returned:int = len(set(t[1] for t in text_list))
        cur_obj.meta["precision"] = float(num_true_returned / num_returned_facts)
        cur_obj.meta["recall"] = float(num_true_returned / num_true_facts)
        cur_obj.auto = float(2*cur_obj.meta["precision"]*cur_obj.meta["recall"] / (cur_obj.meta["precision"]+cur_obj.meta["recall"]))
        cur_obj.text = text

#################################
## LLM + LLMS
#################################
class StartFrom(IntEnum):
	beginning = 0
	chunks = 1
	prompt = 2
	llm = 3
	post_process = 4

class LLM(RagtimeBase):
    """
    Base class for text to text LLMs.
    Class deriving from LLM must implement `complete`.
    A Prompter must be provided at creation time.
    Instantiates a get_prompt so as to be able change the prompt LLM-wise.
    """
    name:Optional[str] = None
    prompter:Prompter

    async def generate(self, cur_obj:WithLLMAnswer, prev_obj:WithLLMAnswer, qa:QA,
                start_from:StartFrom, b_missing_only:bool, **kwargs) -> WithLLMAnswer:
        """Generate prompt and execute LLM
        Returns the retrieved or created object containing the LLMAnswer
        If None, LLMAnswer retrieval or generation went wrong and post-processing
        must be skipped"""
        
        assert not prev_obj or (cur_obj.__class__ == prev_obj.__class__)
        cur_class_name:str = cur_obj.__class__.__name__
        
        # Get prompt
        if not(prev_obj and prev_obj.llm_answer and prev_obj.llm_answer.prompt) or \
        (start_from <= StartFrom.prompt and not b_missing_only):
            logger.debug(f'Either no {cur_class_name} / LLMAnswer / Prompt exists yet, or you asked to regenerate Prompt ==> generate prompt')
            prompt = self.prompter.get_prompt(**kwargs)
        else:
            logger.debug(f'Reuse existing Prompt')
            prompt = prev_obj.llm_answer.prompt

        # Generates text
        result:WithLLMAnswer = cur_obj
        if not(prev_obj and prev_obj.llm_answer) or (start_from <= StartFrom.llm and not b_missing_only):
            logger.debug(f'Either no {cur_class_name} / LLMAnswer exists yet, or you asked to regenerate it ==> generate LLMAnswer')
            try:
                result.llm_answer = await self.complete(prompt)
            except Exception as e:
                logger.exception(f'Exception while generating - skip it\n{e}')
                result = None
        else:
            logger.debug(f'Reuse existing LLMAnswer in {cur_class_name}')
            result = prev_obj

        # Post-process          
        if result.llm_answer and (not (prev_obj and prev_obj.llm_answer) or not b_missing_only and start_from <= StartFrom.post_process):
            logger.debug(f'Post-process {cur_class_name}')
            self.prompter.post_process(qa=qa, cur_obj=result)
        else:
            logger.debug('Reuse post-processing')            

        return result
    
    @abstractmethod
    async def complete(self, prompt:Prompt) -> LLMAnswer:
        raise NotImplementedError('Must implement this!')

class LiteLLM(LLM):
    """Simple extension of LLM based on the litellm library.
    Allows to call LLMs by their name in a stantardized way.
    The default get_prompt method is not changed.
    The generate method uses the standard litellm completion method.
    Default values of temperature (0.0) and number of retries when calling the API (3) can be changed.
    The proper API keys and endpoints have to be specified in the keys.py module.
    """
    name:str
    temperature:float = 0.0
    num_retries:int = 3

    async def complete(self, prompt:Prompt) -> LLMAnswer:
        messages:list[dict] = [{"content":prompt.system, "role":"system"},
                               {"content":prompt.user, "role":"user"}]
        try:
            ans:dict = await acompletion(messages=messages, model=self.name,
                                    temperature=self.temperature, num_retries=self.num_retries)
        except Exception as e:
            logger.exception(f'The following exception occurred with prompt {prompt}' + '\n' + str(e))
            return None
        
        llm_ans:LLMAnswer = LLMAnswer(prompt=prompt,
                                      text=ans['choices'][0]['message']['content'],
                                      name=self.name,
                                      full_name=ans['model'],
                                      duration=ans._response_ms/1000,
                                      cost=float(completion_cost(ans)))
        return llm_ans

#################################
## TEXT GENERATORS
#################################
class TextGenerator(RagtimeBase, ABC):
    """Abstract class for AnswerGenerator, FactGenerator, EvalGenerator"""
    llms:Optional[list[LLM]] = []
    b_use_chunks:bool = False

    def __init__(self, llms:list[LLM] = None, llm_names:list[str] = None, prompter:Prompter=None):
        """
        Args
            llm_names(str or list[str]): a list of LLM names to be instantiated as LiteLLMs - the names come from https://litellm.vercel.app/docs/providers
            llms(LLM or list[LLM]) : list of LLM objects
            Either llms or llm_names or both can be used but at least one must be provided
        """
        super().__init__()
        if (not llm_names) and (not llms):
            raise RagtimeException('Both llms and llm_names lists are empty! Please provide at least one.')        
        # First add the LLM by their names as LiteLLMs
        if llm_names:
            if prompter:
                if isinstance(llm_names, str): llm_names = [llm_names]
                self.llms = [LiteLLM(name=llm_name, prompter=prompter) for llm_name in llm_names]
            else:
                raise RagtimeException('You have to provide a Prompter if you use llm_names.')
        # Then add the LLM object
        if llms:
            if isinstance(llms, LLM): llms = [llms]
            self.llms +=  llms
    
    @property
    def llm(self) -> LLM:
        """Helper function to get the first LLM when only one is provided (like for EvalGenerator and FactGenerator)"""
        if self.llms:
            return self.llms[0]
        else:
            return None
    
    def generate(self, expe:Expe, start_from:StartFrom=StartFrom.beginning, b_missing_only:bool = False, 
                 only_llms:list[str] = None, save_every:int=0) -> bool:
        """Main method calling "gen_for_qa" for each QA in an Expe. Returns False if completed with error, True otherwise
        The main step in generation are :
        - beginning: start of the process - when start_from=beginning, the whole process is executed
	    - chunks: only for Answer generation - chunk retrieval, if a Retriever is associated with the Answer Generator object
        Takes a Question and returns the Chunks
        - prompt: prompt generation, either directly using the question or with the chunks if any
        Takes a Question + optional Chunks and return a Prompt
        - llm: calling the LLM(s) with the generated prompts
        Takes a Prompt and return a LLMAnswer
        - post_process: post-processing the aswer returned by the LLM(s)
        Takes LLMAnswer + other information and updates the Answer object
        Args:
            - expe: Expe object to generate for
            - start_from: allows to start generation from a specific step in the process
            - b_missing_only: True to execute the steps only when the value is absent, False to execute everything
            even if a value already exists
            - only_llms: restrict the llms to be computed again - used in conjunction with start_from -
            if start from beginning, chunks or prompts, compute prompts and llm answers for the list only -
            if start from llm, recompute llm answers for these llm only - has not effect if start 
            """

        nb_q:int = len(expe)
        async def generate_for_qa(num_q:int, qa:QA):
            logger.prefix = f"({num_q}/{nb_q})"
            logger.info(f'*** {self.__class__.__name__} for question "{qa.question.text}"')
            try:
                await self.gen_for_qa(qa=qa, start_from=start_from,  b_missing_only=b_missing_only, only_llms=only_llms)
            except Exception as e:
                logger.exception(f"Exception caught - saving what has been done so far:\n{e}")
                expe.save_temp(name=f"Stopped_at_{num_q}_of_{nb_q}_")
                return False
            logger.info(f'End question "{qa.question.text}"')
            if save_every and (num_q % save_every == 0): expe.save_to_json()
            return True

        loop = asyncio.get_event_loop()
        tasks = [generate_for_qa(num_q, qa) for num_q, qa in enumerate(expe, start=1)]
        logger.info(f'tasks created {len(tasks)}')
        all_qa = loop.run_until_complete(asyncio.gather(*tasks))
        return all(all_qa)

    def write_chunks(self, qa:QA):
        """Write chunks in the current qa if a Retriever has been given when creating the object. Ignore otherwise"""
        raise NotImplementedError('Must implement this if you want to use it!')
    
    @abstractmethod
    async def gen_for_qa(self, qa:QA, start_from:StartFrom=StartFrom.beginning, 
                   b_missing_only:bool = True, only_llms:list[str] = None):
        """Method to be implemented to generate Answer, Fact and Eval"""
        raise NotImplementedError('Must implement this!')

class AnsGenerator(TextGenerator):
    """Object to write answers in the expe
    To use a Retriever, first implement one and give it as parameter when constructing the object
    Besides, subclasses can override the following methods:
    - post_process : to add "meta" fields based on the llm_answer
    Prompts can be changed in the LLM subclass"""
    retriever:Optional[Retriever] = None

    def __init__(self, retriever:Retriever = None, llms:list[LLM] = None, llm_names:list[str] = None, prompter:Prompter=None):
        """
        Args
            retriever(Retriever): the retriever to used to get the chunks before generating the answer - can be None if no Retriever is used
            llm_names(list[str]): a list of LLM names to be instantiated as LiteLLMs - the names come from https://litellm.vercel.app/docs/providers
            llms(list[LLM]) : list of LLM objects
            Either llms or llm_names or both can be used but at least one must be provided
        """
        super().__init__(llm_names=llm_names, llms=llms, prompter=prompter)
        if retriever:
            self.retriever = retriever

    def write_chunks(self, qa:QA):
        """Write chunks in the current qa if a Retriever has been given when creating the object. Ignore otherwise"""
        if self.retriever:
            qa.chunks.empty()
            self.retriever.retrieve(qa=qa)
    
    async def gen_for_qa(self, qa:QA, start_from:StartFrom=StartFrom.beginning, b_missing_only:bool=False, only_llms:list[str] = None):
        """
        Args
        - qa (QA) : the QA (expe row) to work on
        - start_from : a value in the StartFrom Enum, among:
            - beginning: retrieve chunks (if a Retriever is given, ignore otherwise), compute prompts,
        computer llm answers, compute meta on answers
            - prompt: reuse chunks, compute prompts, llm answers and meta
            - llm: reuse chunks and prompts, compute llm answers and meta
            - post_process: reuse chunks, prompts and llm answers, compute meta only
        - b_missing_only: True to generate LLM Answers only when the Answer object has no "llm_answer"
        Useful to complete a previous experiment where all the Answers have not been generated (happens sometimes due
        to external server failures)
        - only_llms: restrict the llms to be computed again - used in conjunction with start_from - if start from beginning, chunks or prompts, compute prompts and llm answers for the list only - if start from llm, recompute llm answers for these llm only - has not effect if start 
        """
        # Get chunks -> fills the Chunks in the QA
        logger.prefix += '[AnsGen]'
        if self.retriever:
            # Compute chunks if there are not any or there are some and user asked to start à Chunks step or before and did not mention to
            # complete only the missing ones
            if (not qa.chunks) or (qa.chunks and start_from <= StartFrom.chunks and not b_missing_only):
                logger.info(f'Compute chunks')
                self.write_chunks(qa=qa)
            else: # otherwise reuse the chunks already in the QA object
                logger.info(f'Reuse existing chunks')

        # Generation loop, for each LLM -> fills the Answers in the QA
        # Get list of LLMs sto actually use, if only_llms defined
        new_answers:Answer = Answers()
        actual_llms:list[LLM] = [l for l in self.llms if l in only_llms] if only_llms else self.llms
        original_prefix:str = logger.prefix
        for llm in actual_llms:
            logger.prefix = f'{original_prefix}[{llm.name}]'
            logger.info(f'* Start with LLM')

            # Get existing Answer if any
            prev_ans:Optional[Answer] = [a for a in qa.answers if a.llm_answer and (a.llm_answer.name == llm.name or a.llm_answer.full_name == llm.name)]
            if prev_ans:
                prev_ans = prev_ans[0] # prev_ans is None if no previous Answer has been generated for the current LLM
                logger.debug(f'An Answer has already been generated with this LLM')
            else:
                prev_ans = None

            # Get Answer from LLM
            ans:Answer = await llm.generate(cur_obj=Answer(), prev_obj=prev_ans,
                                      qa=qa, start_from=start_from,
                                      b_missing_only=b_missing_only,
                                      question=qa.question,
                                      chunks=qa.chunks)
           
            # get previous human eval if any
            if prev_ans and prev_ans.eval:
                ans.eval.human = prev_ans.eval.human

            new_answers.append(ans)
       
        # end of the per LLM loop, answers have been generated or retrieved, write them in qa
        qa.answers = new_answers

class FactGenerator(TextGenerator):
    """Generate Facts from existing Answers"""

    async def gen_for_qa(self, qa:QA, start_from:StartFrom=StartFrom.beginning, b_missing_only:bool=False, only_llms:list[str] = None):
        """Create Facts based on the first Answer in the QA having human Eval equals 1 """
       
        ans:Answer = next((a for a in qa.answers if a.eval and a.eval.human == 1.0))
        if ans:
            logger.prefix += f'[FactGen][{self.llm.name}]'
            model_str:str = f" associated with answer from model {ans.llm_answer.full_name}" if ans.llm_answer else ""
            logger.info(f'Generate Facts since it has a human validated answer (eval.human == 1.0){model_str}')
            prev_facts:Facts = qa.facts

            #2.a. and 2.b : prompt generation + Text generation with LLM 
            qa.facts = await self.llm.generate(cur_obj=Facts(), prev_obj=prev_facts,
                                    qa=qa, start_from=start_from,
                                    b_missing_only=b_missing_only,
                                    answer=ans)
        else:
            logger.debug(f'No fact has been generated since no answer has been validated (human=1.0) for this question')

class EvalGenerator(TextGenerator):
    """Generate Eval from Answers and Facts.
    For a given QA, send the Answer and the Facts to the LLM to get the prompt back
    The default prompt returns all the valid facts given an answer, i.e. 1 prompt -> 1 Eval
    That could be overridden to have e.g. 1 prompt per Fact, i.e. N prompt -> 1 Eval
    The conversion between the LLM answer and the Eval is made in post_process"""

    async def gen_for_qa(self, qa:QA, start_from:StartFrom=StartFrom.beginning, b_missing_only:bool=False, only_llms:list[str] = None):
        """Create Eval for each QA where Facts are available"""

        if len(qa.answers) == 0:
            logger.error(f'No Answers, cannot generate Evals'); return
        if len(qa.facts) == 0:
            logger.error(f'No Facts, cannot generate Evals'); return
        
        # Eval loop
        logger.prefix += f'[EvalGen][{self.llm.name}]'
        for ans in (a for a in qa.answers if a.text):
            llm_name:str = ans.llm_answer.name if ans.llm_answer else UNKOWN_LLM
            if only_llms and llm_name not in only_llms and llm_name != UNKOWN_LLM: continue
            logger.debug(f'Generate Eval for answer generated with "{llm_name}"')
            prev_eval:Eval = ans.eval
    
            #2.a. and 2.b : prompt generation + Text generation with LLM 
            ans.eval = await self.llm.generate(cur_obj=Eval(), prev_obj=prev_eval,
                                    qa=qa, start_from=start_from,
                                    b_missing_only=b_missing_only,
                                    answer=ans, facts=qa.facts)          

            # save previous human eval if any
            if prev_eval and prev_eval.human: ans.eval.human = prev_eval.human

class TwoFactsEvalGenerator(TextGenerator):
    """Generate Eval from Answers and Facts. Converts first the Answer to a list of Facts and
    perform evaluation"""

    def __init__(self, llms:list[LLM] = None):
        super().__init__(llms=llms)
        if len(self.llms) < 2:
            raise RagtimeException("""Need at least 2 LLMs to run this generator!
                                   1st LLM is used to generate Facts from the Answer.
                                   2nd LLM is used to generate Eval from the golden Facts and the Facts from the Answer.""")

    async def gen_for_qa(self, qa:QA, start_from:StartFrom=StartFrom.beginning, b_missing_only:bool=False):
        """Create Eval for each QA where Facts are available"""

        if len(qa.answers) == 0:
            logger.error(f'No Answers, cannot generate Evals'); return
        if len(qa.facts) == 0:
            logger.error(f'No Facts, cannot generate Evals'); return
        
        # Eval loop
        for ans in (a for a in qa.answers if a.text):
            llm_name:str = ans.llm_answer.name if ans.llm_answer else "unkown LLM (manual ?)"
            logger.debug(f'Generate Facts for answer generated with "{llm_name}"')
            prev_eval:Eval = ans.eval
    
            # Use 1st LLM to generate facts from the Answer
            ans_facts:Facts = await self.llms[0].generate(cur_obj=Facts(), prev_obj=None,
                                    qa=qa, start_from=start_from,
                                    b_missing_only=b_missing_only,
                                    answer=ans)    
                      
            # Use 2nd LLM to generate Eval
            logger.debug(f'Then generate Eval using answer facts and gold facts')
            cur_eval:Eval = Eval()
            cur_eval.meta['answer_facts'] = [af.text for af in ans_facts] # stores the answer's facts in the current eval
            ans.eval = await self.llms[1].generate(cur_obj=cur_eval, prev_obj=prev_eval,
                                    qa=qa, start_from=start_from,
                                    b_missing_only=b_missing_only,
                                    answer_facts=ans_facts, gold_facts=qa.facts)

            # save previous human eval if any
            if prev_eval and prev_eval.human: ans.eval.human = prev_eval.human

def gen_Answers(folder_in:Path, folder_out:Path, json_file: Union[Path,str], prompter:Prompter, llm_names:list[str], retriever:Retriever=None, 
                start_from:StartFrom=StartFrom.beginning, b_missing_only:bool = False, only_llms:list[str] = None, save_every:int=0) -> Expe:
  """Standard function to generate answers - returns the updated Expe or None if an error occurred"""
  expe:Expe = Expe(json_path=folder_in / json_file)
  ans_gen:AnsGenerator = AnsGenerator(retriever=retriever, llm_names=llm_names, prompter=prompter)
  if ans_gen.generate(expe, start_from=start_from,  b_missing_only=b_missing_only, only_llms=only_llms,
                      save_every=save_every):
    expe.save_to_json(path=folder_out / json_file)
    return expe
  else:
    return None
  

def gen_Facts(folder_in:Path, folder_out:Path, json_file: Union[Path,str], prompter:Prompter, llm_names:list[str],
                start_from:StartFrom=StartFrom.beginning, b_missing_only:bool = False, only_llms:list[str] = None, save_every:int=0) -> Expe:
  """Standard function to generate facts - returns the updated Expe or None if an error occurred"""
  expe:Expe = Expe(json_path=folder_in / json_file)
  fact_gen:FactGenerator = FactGenerator(llm_names=llm_names, prompter=prompter)
  if fact_gen.generate(expe, start_from=start_from,  b_missing_only=b_missing_only, only_llms=only_llms, save_every=save_every):
    expe.save_to_json(path=folder_out / json_file)
    return expe
  else:
    return None

def gen_Evals(folder_in:Path, folder_out:Path, json_file: Union[Path,str], prompter:Prompter, llm_names:list[str],
                start_from:StartFrom=StartFrom.beginning, b_missing_only:bool = False, only_llms:list[str] = None, save_every:int=0) -> Expe:
  """Standard function to generate evals - returns the updated Expe or None if an error occurred"""
  expe:Expe = Expe(json_path=folder_in / json_file)
  eval_gen:EvalGenerator = EvalGenerator(llm_names=llm_names, prompter=prompter)
  if eval_gen.generate(expe, start_from=start_from,  b_missing_only=b_missing_only, only_llms=only_llms, save_every=save_every):
    expe.save_to_json(path=folder_out / json_file)
    return expe
  else:
    return None
