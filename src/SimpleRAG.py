import os
import numpy as np
import streamlit as st
from llama_index.core import Settings
from trulens.core import Select, Feedback
from trulens.apps.custom import instrument
from trulens.providers.openai.provider import OpenAI
from trulens.providers.cortex.provider import Cortex
from src.prompts import query_prompt, summary_prompt
from snowflake.snowpark.context import get_active_session
from src.CortexSearchRetriever import CortexSearchRetriever


class SimpleRAG:
    def __init__(self):
        session = get_active_session()
        NUM_CHUNKS = int(os.getenv("NUM_CHUNKS"))
        POSTS_COLUMNS = ["title", "url", "type"]
        DOCS_COLUMNS = ["title", "relative_path", "version", "file_content"]

        self.llm = Settings.llm
        self.retriever = [
            CortexSearchRetriever(session, os.getenv("CORTEX_DOC_SEARCH_SERVICE"), DOCS_COLUMNS, NUM_CHUNKS),
            CortexSearchRetriever(session, os.getenv("CORTEX_POSTS_SEARCH_SERVICE"), POSTS_COLUMNS, NUM_CHUNKS)
        ]


    @instrument
    def retrieve_context(self, query: str):
        """
        Retrieve relevant text from vector store.
        """
        docs, posts = self.retriever[0].retrieve(query), self.retriever[1].retrieve(query)
        docs.extend(posts)

        return docs


    def get_chat_history(self):
        SLIDE_WINDOW = 7
        chat_history = []

        if "messages" not in st.session_state:
            return []
        
        start_index = max(0, len(st.session_state.messages) - SLIDE_WINDOW)
        for i in range (start_index , len(st.session_state.messages) - 1):
            chat_history.append(st.session_state.messages[i])

        return chat_history
    

    def create_prompt(self, query, context):
        chat_history = self.get_chat_history()
        if chat_history != []:
            # Re-write query if there is history.
            prompt = summary_prompt.format(chat_history=chat_history, query=query)
            query = self.llm.complete(prompt).text.replace("'", "")
        
        prompt = query_prompt.format(
            chat_history=chat_history,
            context=context,
            query=query
        )

        return prompt


    @instrument
    def generate_completion(self, query: str, context: list) -> str:
        prompt = self.create_prompt(query, context)
        response = self.llm.stream_complete(prompt)
        return response


    @instrument
    def query(self, query: str) -> str:
        context = self.retrieve_context(query)
        
        relative_paths = {
            item['title']: f"https://github.com/{os.getenv('REPO_NAME')}/blob/{item['version']}/docs/" + item["relative_path"].replace("\\", "/") for item in context if "version" in item.keys()
        }

        return {
            "result": self.generate_completion(query, context),
            "references": relative_paths
        }
    

    @property
    def version(self):
        return "v1"


    def eval_metrics(self):
        # provider = OpenAI()
        provider = Cortex(
            get_active_session(), 
            model_engine=os.getenv("SNOWFLAKE_EVAL_LLM")
        )

        f_groundedness = (
            Feedback(provider.groundedness_measure_with_cot_reasons, name="Groundedness")
            .on(Select.RecordCalls.retrieve_context.rets[:].collect())
            .on_output()
        )

        f_context_relevance = (
            Feedback(provider.context_relevance, name="Context Relevance")
            .on_input()
            .on(Select.RecordCalls.retrieve_context.rets[:])
            .aggregate(np.mean)
        )

        f_answer_relevance = (
            Feedback(provider.relevance, name="Answer Relevance")
            .on_input()
            .on_output()
            .aggregate(np.mean)
        )

        f_harmful = (
            Feedback(provider.harmfulness_with_cot_reasons, name="Harmful")
            .on_output()
        )

        f_malicious = (
            Feedback(provider.maliciousness_with_cot_reasons, name="Malicious", higher_is_better=False)
            .on_output()
        )

        f_concise = (
            Feedback(provider.conciseness_with_cot_reasons, name="Conciseness")
            .on_output()
        )

        f_coherent = (
            Feedback(provider.coherence_with_cot_reasons, name="Coherence")
            .on_output()
        )

        return {
            "honest": [f_groundedness, f_context_relevance, f_answer_relevance],
            "harmless": [f_harmful, f_malicious],
            "helpful": [f_concise, f_coherent, f_answer_relevance]
        }