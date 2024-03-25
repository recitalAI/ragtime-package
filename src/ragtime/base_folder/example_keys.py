"""
Fill in the values in this file according to the credentials you need
Also make sure keys.py is listed in .gitignore, so not on the repo
"""

import os

RETRIEVER_USER:str = "user"
RETRIEVER_PWD:str = "password"
RETRIEVER_URL_LOGIN:str = "https://..."
RETRIEVER_URL_SEARCH:str = "https://..."

API_OPENAI:str = "..."
API_ANTHROPIC:str = "..."
API_HF:str = "..."
API_VERTEX_PROJECT:str = "project name"
API_VERTEX_LOCATION:str = "location"

os.environ["OPENAI_API_KEY"] = API_OPENAI
os.environ["ANTHROPIC_API_KEY"] = API_ANTHROPIC
os.environ["HUGGINGFACE_API_KEY"] = API_HF
os.environ["VERTEX_PROJECT"] = API_VERTEX_PROJECT
os.environ["VERTEX_LOCATION"] = API_VERTEX_LOCATION