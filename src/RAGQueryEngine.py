import os
import json
import numpy as np
import streamlit as st
from json_repair import repair_json
from .config import get_doc_versions
from llama_index.core import Settings
from trulens.core import Select, Feedback
from trulens.apps.custom import instrument
from trulens.providers.cortex.provider import Cortex
from trulens.providers.openai.provider import OpenAI
from snowflake.snowpark.context import get_active_session
from src.CortexSearchRetriever import CortexSearchRetriever
from src.prompts import query_prompt_v2, decomposition_prompt
from trulens.core.guardrails.base import context_filter, block_output

# provider = OpenAI()
provider = Cortex(
    get_active_session(),
    model_engine=os.getenv("SNOWFLAKE_EVAL_LLM")
)

context_filter_feedback = (
    Feedback(provider.context_relevance, name="Context Relevance Filter")
    .on_input()
    .on(Select.RecordCalls.filter_context.rets)
)


class RAGQueryEngine():
    def __init__(self):
        session = get_active_session()
        NUM_CHUNKS = int(os.getenv("NUM_CHUNKS"))
        POSTS_COLUMNS = ["title", "url", "type"]
        DOCS_COLUMNS = ["title", "relative_path", "version", "file_content"]

        self.llm = Settings.llm
        self.doc_retriever = CortexSearchRetriever(
            session, os.getenv("CORTEX_DOC_SEARCH_SERVICE"), DOCS_COLUMNS, NUM_CHUNKS
        )
        self.post_retriever = CortexSearchRetriever(
            session, os.getenv("CORTEX_POSTS_SEARCH_SERVICE"), POSTS_COLUMNS, NUM_CHUNKS
        )


    @instrument
    @context_filter(context_filter_feedback, 0.7, 'query')
    def filter_context(self, query: str, docs):
        contents = []
        results = []
        # Need a better way to do this.
        # Deduplication for duplication content from 2 routers.
        for doc in docs:
            if "version" in doc.keys():
                if doc['file_content'] not in contents:
                    contents.append(doc['file_content'])
                    results.append(doc)
            else:
                results.append(doc)

        return results


    @instrument
    def retrieve_context(self, query: str, version: str):
        """
        Retrieve relevant text from vector store.
        """
        docs = self.doc_retriever.retrieve(query, {"@eq": {"version": version}})
        posts = self.post_retriever.retrieve(query)
        docs.extend(posts)

        return self.filter_context(query, docs)


    def get_chat_history(self):
        SLIDE_WINDOW = 7
        chat_history = []

        if "messages" not in st.session_state:
            return []
        
        start_index = max(0, len(st.session_state.messages) - SLIDE_WINDOW)
        for i in range (start_index , len(st.session_state.messages) - 1):
            chat_history.append(st.session_state.messages[i])

        return chat_history


    @instrument
    def get_completion_prompt(self, query, context):
        return query_prompt_v2.format(
            context=context,
            query=query
        )


    @instrument
    def generate_completion(self, query: str, context: list) -> str:
        prompt = self.get_completion_prompt(query, context)
        response = self.llm.stream_complete(prompt)
        return response


    @instrument
    def decompose(self, query: str):
        prompt = decomposition_prompt.format(
            versions = get_doc_versions(),
            latest_version = get_doc_versions()[0],
            query = query,
            chat_history = self.get_chat_history()
        )

        queries = json.loads(repair_json(self.llm.complete(prompt).text))

        return queries


    @instrument
    def query(self, query: str) -> str:
        queries = self.decompose(query)

        contexts = []
        relative_paths = {}
        # Maybe we can make these calls async.
        for q in queries:
            context = self.retrieve_context(q["query"], q["version"])

            contexts.extend(context)
            for item in context:
                if "version" in item.keys():
                    relative_paths[item['title']] = f"https://github.com/{os.getenv('REPO_NAME')}/blob/{item['version']}/docs/" + item["relative_path"].replace("\\", "/")

        return {
            "result": self.generate_completion(query, contexts),
            "references": relative_paths
        }


    @property
    def version(self):
        return "v3"


    def eval_metrics(self):
        f_groundedness = (
            Feedback(provider.groundedness_measure_with_cot_reasons, name="Groundedness")
            .on(Select.RecordCalls.retrieve_context[:].rets[:].collect())
            .on_output()
        )

        f_context_relevance = (
            Feedback(provider.context_relevance, name="Context Relevance")
            .on_input()
            .on(Select.RecordCalls.retrieve_context[:].rets[:])
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