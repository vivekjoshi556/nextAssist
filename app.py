import os
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from src.config import sessionSetup
from snowflake.cortex import Complete

load_dotenv(".env")

NUM_CHUNKS = 3
SLIDE_WINDOW = 7

CORTEX_SEARCH_DATABASE = os.getenv("SNOWFLAKE_DB")
CORTEX_SEARCH_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
CORTEX_DOC_SEARCH_SERVICE = os.getenv("CORTEX_DOC_SEARCH_SERVICE")

COLUMNS = [
    "file_content",
    "relative_path",
    "version"
]

session, svc = sessionSetup()


def get_similar_chunks_search_service(query):
    filter_obj = {"@eq": {"version": st.session_state.version} }
    response = svc.search(query, COLUMNS, filter=filter_obj, limit=NUM_CHUNKS)


    if st.session_state.debug:
        st.sidebar.text("Relevant Chunks:")
        st.sidebar.json(response.model_dump_json())
    
    return response.model_dump_json()  

def get_chat_history():
    chat_history = []

    start_index = max(0, len(st.session_state.messages) - SLIDE_WINDOW)
    for i in range (start_index , len(st.session_state.messages) -1):
         chat_history.append(st.session_state.messages[i])

    return chat_history


def summarize_question_with_history(chat_history, question):
    prompt = f"""
        Based on the chat history below and the question, generate a query that extend the question with the chat history provided. The query should be in natural language. 
        Answer with only the query. Do not add any explanation.
        
        <chat_history>
        {chat_history}
        </chat_history>
        <question>
        {question}
        </question>
    """
    
    summary = Complete(st.session_state.model_name, prompt)

    if st.session_state.debug:
        st.sidebar.text("Summary to be used to find similar chunks in the docs:")
        st.sidebar.caption(summary)

    summary = summary.replace("'", "")

    return summary


def create_prompt(query):
    chat_history = get_chat_history()
    if chat_history != []:
        question_summary = summarize_question_with_history(chat_history, query)
        prompt_context =  get_similar_chunks_search_service(question_summary)
    else:
        prompt_context = get_similar_chunks_search_service(query) #First question when using history
  
    prompt = f"""
        You are an expert chat assistance that extracts information from the CONTEXT provided
        between <context> and </context> tags.
        You offer a chat experience considering the information included in the CHAT HISTORY
        provided between <chat_history> and </chat_history> tags..
        When answering the question contained between <question> and </question> tags
        give detailed answers but do not hallucinate. 
        If you don´t have the information just say so.
        
        Do not mention the CONTEXT used in your answer.
        Do not mention the CHAT HISTORY used in your answer.

        Only answer the question if you can extract it from the CONTEXT provided.
        
        <chat_history>
        {chat_history}
        </chat_history>
        <context>          
        {prompt_context}
        </context>
        <question>  
        {query}
        </question>
        Answer: 
    """
    
    json_data = json.loads(prompt_context)

    relative_paths = set(item['relative_path'] for item in json_data['results'])

    return prompt, relative_paths


def answer_question(query):
    prompt, relative_paths = create_prompt(query)
    response = Complete(st.session_state.model_name, prompt, stream = True)
    return response, relative_paths


def main():
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
    
            with st.spinner(f"{st.session_state.model_name} thinking..."):
                response, relative_paths = answer_question(question)

            answer = ""
            for ans in response:
                answer += ans.replace("'", "")
                message_placeholder.markdown(answer)
            # if relative_paths != "None":
            #     with st.sidebar.expander("Related Documents"):
            #         for path in relative_paths:
            #             cmd2 = f"select GET_PRESIGNED_URL(@docs, '{path}', 360) as URL_LINK from directory(@docs)"
            #             df_url_link = session.sql(cmd2).to_pandas()
            #             url_link = df_url_link._get_value(0,'URL_LINK')
            
            #             display_url = f"Doc: [{path}]({url_link})"
            #             st.sidebar.markdown(display_url)

        
        st.session_state.messages.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
