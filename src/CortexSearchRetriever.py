import os
import json
from typing import List
from snowflake.core import Root
from snowflake.snowpark import Session


class CortexSearchRetriever:
    def __init__(self, session: Session, service: str, columns: List[str], top_k: int = 4):
        self._session = session
        self._service = service
        self._top_k = top_k
        self._columns = columns

        root = Root(self._session)
        self._service = (
            root.databases[os.getenv("SNOWFLAKE_DB")]
            .schemas[os.getenv("SNOWFLAKE_SCHEMA")]
            .cortex_search_services[service]
        )


    def retrieve(self, query: str, filter_obj = {}) -> List[str]:
        response = self._service.search(
            filter=filter_obj,
            query=query,
            columns=self._columns,
            limit=self._top_k,
        )

        response = json.loads(response.to_json())
        return response["results"]