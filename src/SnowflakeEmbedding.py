import os
from snowflake.snowpark import Session
from typing import Any, List, Callable
from llama_index.core.embeddings import BaseEmbedding
from snowflake.cortex import EmbedText768, EmbedText1024
from snowflake.snowpark.context import get_active_session


class SnowflakeEmbedding(BaseEmbedding):
    session: Session
    embed: Callable[[str], List[float]]

    def __init__(
        self,
        **kwargs: Any,
    ):
        super().__init__(
            model_name = os.getenv('CORTEX_EMBEDDING_MODEL'),
            session=get_active_session(),
            embed = EmbedText768 if os.getenv('CORTEX_EMBEDDING_DIMS') == '768' else EmbedText1024,
            **kwargs
        )
        
        if os.getenv('CORTEX_EMBEDDING_DIMS') not in ['768', '1024']:
            raise "Invalid Embedding Dims for Snowflake"


    def _get_query_embedding(self, query: str) -> List[float]:
        return self.embed(self.model_name, query, self.session)


    def _get_text_embedding(self, text: str) -> List[float]:
        return self.embed(self.model_name, text, self.session)


    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(self.model_name, text, self.session) for text in texts]


    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)


    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)