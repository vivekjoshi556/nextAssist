import os
import streamlit as st
from snowflake.core import Root
from snowflake.snowpark import Session
from snowflake.snowpark.context import get_active_session

def sessionSetup():
    st.set_page_config(
        page_title=os.getenv("APP_NAME"),
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.title(f":speech_balloon: NextAssist")
    st.session_state.model_name = 'mistral-large2'
    st.session_state.debug = os.getenv("APP_ENV") != 'production'

    connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "database": os.getenv("SNOWFLAKE_DB"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    }

    try:
        session = get_active_session()
    except:
        session = Session.builder.configs(connection_parameters).create()

    root = Root(session)                         

    svc = root.databases[os.getenv("SNOWFLAKE_DB")].schemas[os.getenv("SNOWFLAKE_SCHEMA")].cortex_search_services[os.getenv("CORTEX_DOC_SEARCH_SERVICE")]


    categories = session.table(
        os.getenv("SNOWFLAKE_DOC_TABLE_NAME")
    ).select('version').distinct().sort('version', ascending=False).collect()

    cat_list = []
    for cat in categories:
        cat_list.append(cat.VERSION)

    st.sidebar.selectbox('Next Version', cat_list, key = "version")
    st.sidebar.button("Start Over", key="clear_conversation", on_click=init_messages)
    init_messages()

    return session, svc


def init_messages():
    # Initialize chat history
    if st.session_state.clear_conversation or "messages" not in st.session_state:
        st.session_state.messages = []