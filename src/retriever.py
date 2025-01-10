import os
from typing import List
from snowflake.core import Root
from snowflake.snowpark import Session


class CortexSearchRetriever:
    def __init__(self, session: Session, service: str, top_k: int = 4):
        self._session = session
        self._service = service
        self._top_k = top_k

    
    def retrieve(self, query: str) -> List[str]:
        root = Root(self._session)
        cortex_search_service = (
            root.databases[os.getenv["SNOWFLAKE_DATABASE"]]
            .schemas[os.getenv["SNOWFLAKE_SCHEMA"]]
            .cortex_search_services[self._services]
        )

        resp = cortex_search_service.search(
            query=query,
            columns=["doc_text"],
            limit=self._top_k,
        )

        if resp.results:
            return [curr["doc_text"] for curr in resp.results]
        else:
            return []
