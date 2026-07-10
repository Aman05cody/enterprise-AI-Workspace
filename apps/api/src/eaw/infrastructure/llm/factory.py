"""LLM factory."""

from functools import lru_cache

from eaw.application.ports.llm import LLMPort
from eaw.core.config import get_settings
from eaw.infrastructure.llm.echo_llm import EchoLLMAdapter
from eaw.infrastructure.llm.openai_llm import OpenAILLMAdapter


@lru_cache
def get_llm_adapter() -> LLMPort:
    settings = get_settings()
    provider = (settings.llm_provider or "echo").lower()
    if provider == "openai":
        return OpenAILLMAdapter(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
            api_base=settings.openai_api_base,
        )
    return EchoLLMAdapter(model="echo-grounded-v1")
