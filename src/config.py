import os
import streamlit as st
from functools import lru_cache
from trulens.core import TruSession
from snowflake.snowpark import Session
from trulens.dashboard import run_dashboard
from snowflake.snowpark.context import get_active_session
from trulens.connectors.snowflake import SnowflakeConnector

def sessionSetup():
    st.set_page_config(
        page_title=os.getenv("APP_NAME"),
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.title(f":speech_balloon: {os.getenv('APP_NAME')}")
    st.session_state.debug = os.getenv("APP_ENV") != 'production'

    connection_parameters = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "database": os.getenv("SNOWFLAKE_DB"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
    }

    # tru_snowflake_connector = SnowflakeConnector(
    #     warehouse = os.getenv("SNOWFLAKE_WAREHOUSE"),
    #     role = os.getenv("SNOWFLAKE_ROLE"),
    #     **connection_parameters
    # )
    # lens_session = TruSession(connector=tru_snowflake_connector)

    # run_dashboard(session, port=os.getenv("TRULENS_PORT"))

    try:
        session = get_active_session()
    except:
        print("No Active Session Found. Creating Session.")
        session = Session.builder.configs(connection_parameters).create()

    categories = get_doc_versions()
    print(categories)

    cat_list = []
    for cat in categories:
        cat_list.append(cat)

    st.sidebar.selectbox('Next Version', cat_list, key = "version")
    st.sidebar.button("Start Over", key="clear_conversation", on_click=init_messages)
    init_messages()

    # return lens_session


@lru_cache(maxsize=1)
def get_doc_versions():
    session = get_active_session()
    return [
        row['VERSION'] for row in (
            session.table(os.getenv("SNOWFLAKE_DOC_TABLE_NAME"))
            .select('version')
            .distinct()
            .sort('version', ascending=False)
            .collect()
        )
    ]


def init_messages():
    # Initialize chat history
    if st.session_state.clear_conversation or "messages" not in st.session_state:
        st.session_state.messages = []