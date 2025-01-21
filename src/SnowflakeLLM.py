import os
from typing import Any, Dict
from snowflake.cortex import Complete
from llama_index.core.llms.callbacks import llm_completion_callback
from llama_index.core.llms import CustomLLM, CompletionResponse, CompletionResponseGen, LLMMetadata


class SnowflakeLLM(CustomLLM):
    context_window: int = 128000
    num_output: int = 256
    model_name: str = os.getenv('CORTEX_LLM_MODEL')
    config: Dict[str, Any]

    def __init__(self, temperature=0.2, max_tokens=4096):
        super().__init__(config = {
            'temperature': temperature,
            'max_tokens': max_tokens,
        })


    @property
    def metadata(self) -> LLMMetadata:
        """Get LLM metadata."""
        return LLMMetadata(
            context_window=self.context_window,
            num_output=self.num_output,
            model_name=os.getenv('CORTEX_LLM_MODEL'),
        )


    @llm_completion_callback()
    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        return CompletionResponse(text=Complete(os.getenv('CORTEX_LLM_MODEL'), prompt, options=self.config))


    @llm_completion_callback()
    def stream_complete(
        self, prompt: str, **kwargs: Any
    ) -> CompletionResponseGen:
        response = ""
        response_stream = Complete(os.getenv('CORTEX_LLM_MODEL'), prompt, stream = True, options=self.config)
        for token in response_stream:
            response += token
            yield CompletionResponse(text=response, delta=token)
