import os
import json
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from snowflake.core import Root
from snowflake.cortex import Complete
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session

load_dotenv(".env")

st.set_page_config(
    page_title=os.getenv("APP_NAME"),
    layout="wide",
    initial_sidebar_state="collapsed",
)

NUM_CHUNKS = 3
slide_window = 7

CORTEX_SEARCH_DATABASE = os.getenv("SNOWFLAKE_DB")
CORTEX_SEARCH_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
CORTEX_SEARCH_SERVICE = os.getenv("CORTEX_SEARCH_SERVICE")

COLUMNS = [
    "file_content",
    "relative_path",
    "version"
]

connection_parameters = {
   "account": os.getenv("SNOWFLAKE_ACCOUNT"),
   "user": os.getenv("SNOWFLAKE_USER"),
   "password": os.getenv("SNOWFLAKE_PASSWORD"),
   "database": os.getenv("SNOWFLAKE_DB"),
   "schema": os.getenv("SNOWFLAKE_SCHEMA"),
}

st.session_state.debug = os.getenv("APP_ENV") != 'production'

try:
    session = get_active_session()
except:
    session = Session.builder.configs(connection_parameters).create()

root = Root(session)                         

svc = root.databases[CORTEX_SEARCH_DATABASE].schemas[CORTEX_SEARCH_SCHEMA].cortex_search_services[CORTEX_SEARCH_SERVICE]
   
### Functions
     
def config_options():
    st.session_state.model_name = 'mistral-large2'

    categories = session.table(
        os.getenv("SNOWFLAKE_TABLE_NAME")
    ).select('version').distinct().sort('version', ascending=False).collect()

    cat_list = []
    for cat in categories:
        cat_list.append(cat.VERSION)
            
    st.sidebar.selectbox('Next Version', cat_list, key = "version")
    st.session_state.use_chat_history = True
    st.sidebar.button("Start Over", key="clear_conversation", on_click=init_messages)


def init_messages():
    # Initialize chat history
    if st.session_state.clear_conversation or "messages" not in st.session_state:
        st.session_state.messages = []


def get_similar_chunks_search_service(query):
    filter_obj = {"@eq": {"version": st.session_state.version} }
    response = svc.search(query, COLUMNS, filter=filter_obj, limit=NUM_CHUNKS)


    if st.session_state.debug:
        st.sidebar.text("Relevant Chunks:")
        st.sidebar.json(response.model_dump_json())
    
    return response.model_dump_json()  

def get_chat_history():
    chat_history = []

    start_index = max(0, len(st.session_state.messages) - slide_window)
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
    if st.session_state.use_chat_history:
        chat_history = get_chat_history()
        if chat_history != []:
            question_summary = summarize_question_with_history(chat_history, query)
            prompt_context =  get_similar_chunks_search_service(question_summary)
        else:
            prompt_context = get_similar_chunks_search_service(query) #First question when using history
    else:
        prompt_context = get_similar_chunks_search_service(query)
        chat_history = ""
  
    prompt = f"""
           You are an expert chat assistance that extracts information from the CONTEXT provided
           between <context> and </context> tags.
           You offer a chat experience considering the information included in the CHAT HISTORY
           provided between <chat_history> and </chat_history> tags..
           When answering the question contained between <question> and </question> tags
           be concise and do not hallucinate. 
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
    response = Complete(st.session_state.model_name, prompt)   
    return response, relative_paths


def main():
    
    st.title(f":speech_balloon: NextAssist")

    config_options()
    init_messages()
     
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
                response = response.replace("'", "")
                message_placeholder.markdown(response)

                # if relative_paths != "None":
                #     with st.sidebar.expander("Related Documents"):
                #         for path in relative_paths:
                #             cmd2 = f"select GET_PRESIGNED_URL(@docs, '{path}', 360) as URL_LINK from directory(@docs)"
                #             df_url_link = session.sql(cmd2).to_pandas()
                #             url_link = df_url_link._get_value(0,'URL_LINK')
                
                #             display_url = f"Doc: [{path}]({url_link})"
                #             st.sidebar.markdown(display_url)

        
        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
