"""LLM connectivity — factory for LangChain LLM and embeddings clients."""

from .client import create_embeddings, create_llm

__all__ = ["create_llm", "create_embeddings"]
