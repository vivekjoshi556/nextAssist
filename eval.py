import os
import json
from dotenv import load_dotenv
from trulens.core import TruSession
from src.SimpleRAG import SimpleRAG
from snowflake.snowpark import Session
from trulens.dashboard import run_dashboard
from trulens.apps.custom import TruCustomApp
from src.RAGQueryEngine import RAGQueryEngine
from snowflake.snowpark.context import get_active_session

print("Load Env Variables:", load_dotenv(".env"))


connection_parameters = {
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "database": os.getenv("SNOWFLAKE_DB"),
    "schema": os.getenv("SNOWFLAKE_SCHEMA"),
}

session = TruSession()


def runEval(rag, app_name):
    tests = {}

    with open("./tests/test.json", "r") as fp:
        tests = json.load(fp)

    metrics = rag.eval_metrics()

    for category in tests.keys():
        tru_rag = TruCustomApp(
            rag,
            app_name=app_name,
            app_version=rag.version,
            feedbacks=metrics[category],
        )

        with tru_rag as recording:
            for ques in tests[category]:
                recording.record_metadata={"eval_category": f"{category}"}
                rag.query(ques)
                print("-" * 80)


app_name = f"{os.getenv("APP_NAME")} Eval"
try:
    snowpark_session = get_active_session()
except:
    snowpark_session = Session.builder.configs(connection_parameters).create()

run_dashboard(session, port=os.getenv("TRULENS_PORT"))


rag = RAGQueryEngine()
runEval(rag, app_name)

snowpark_session.close()