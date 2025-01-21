import os
import streamlit as st
from dotenv import load_dotenv
from src.SimpleRAG import SimpleRAG
from src.config import sessionSetup
from llama_index.core import Settings
from src.SnowflakeLLM import SnowflakeLLM
from src.SnowflakeEmbedding import SnowflakeEmbedding

load_dotenv(".env")

lens_session = sessionSetup()
Settings.llm = SnowflakeLLM()
Settings.embed_model = SnowflakeEmbedding()


def main(rag):
    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Accept user input
    if question := st.chat_input("Ask anything you want to know about NextJS?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": question})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(question)
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            question = question.replace("'","") 
            progress_container = st.empty()
            with progress_container.container():
                with st.status("Looking for Answer", expanded=True):
                    response = rag.query(question)

            progress_container.empty()

            response, relative_paths = response["result"], response["references"]

            answer = ""
            references = "" if len(relative_paths.keys()) == 0 else "\n### References: \n" + "\n".join([f"- [{key}]({relative_paths[key]})" for key in relative_paths.keys()])
            for ans in response:
                answer = ans.text.replace("'", "")
                message_placeholder.markdown(answer)
        
            message_placeholder.markdown(answer + references)
        st.session_state.messages.append({"role": "assistant", "content": answer + references})


if __name__ == "__main__":
    from src.RAGQueryEngine import RAGQueryEngine

    rag = RAGQueryEngine()
    # rag = SimpleRAG()
    main(rag)
