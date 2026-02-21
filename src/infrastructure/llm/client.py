"""LLM and embeddings client factory.

Centralises all LangChain OpenAI client construction so every agent or
service consistently uses the same configuration sourced from Settings.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from shared.config import Settings


def create_llm(settings: Settings, *, streaming: bool = False) -> ChatOpenAI:
    """Create a configured ChatOpenAI instance.

    Args:
        settings: Application settings.
        streaming: Whether to enable token-level streaming.

    Returns:
        Configured ChatOpenAI instance pointing at OpenRouter.
    """
    return ChatOpenAI(
        api_key=settings.openrouter.api_key.get_secret_value(),
        base_url=settings.openrouter.base_url,
        model=settings.openrouter.model,
        temperature=0,
        streaming=streaming,
    )


def create_embeddings(settings: Settings) -> OpenAIEmbeddings:
    """Create a configured OpenAIEmbeddings instance.

    Args:
        settings: Application settings.

    Returns:
        Configured OpenAIEmbeddings instance.
    """
    return OpenAIEmbeddings(
        api_key=settings.openrouter.api_key.get_secret_value(),
        base_url=settings.openrouter.base_url,
        model=settings.vector_store.embedding_model,
    )
