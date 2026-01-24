"""Module Builder AI agent implementation using LangChain and OpenRouter.

This agent generates structured metadata (templates, entities, projections, etc.)
and can query the vector store for existing entities to build relationships.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import OpenAIEmbeddings
from openai import APIConnectionError, APIError, RateLimitError

from ai_agent.config import Settings
from ai_agent.exceptions import (
    LLMProviderError,
    TemplateGenerationError,
    TemplateParsingError,
)
from ai_agent.schemas.response import TemplateResponse

from .base import BaseAgent
from .prompts import SYSTEM_PROMPT, TEMPLATE_GENERATION_PROMPT
from .registry import AgentRegistry

logger = logging.getLogger(__name__)


@AgentRegistry.register("module-builder")
class ModuleBuilderAgent(BaseAgent):
    """AI Agent for building module metadata with entity relationship awareness.

    This agent:
    - Generates structured JSON templates/metadata
    - Queries the metadata vector store to find related existing entities
    - Maintains conversation context for relating new entities to each other

    Has READ access to metadata_index only (not data_index).
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the agent with OpenRouter configuration.

        Args:
            settings: Application settings containing OpenRouter and vector store config.
        """
        super().__init__(settings)
        self._parser = PydanticOutputParser(pydantic_object=TemplateResponse)
        self._embeddings = self._create_embeddings()
        self._metadata_store: Optional[FAISS] = None
        self._context_memory: list[dict[str, Any]] = []  # Conversation context for new entities

        # Lazy load vector store
        self._load_metadata_store()

    def _create_embeddings(self) -> OpenAIEmbeddings:
        """Create embeddings model for vector store."""
        return OpenAIEmbeddings(
            api_key=self._settings.openrouter.api_key.get_secret_value(),
            base_url=self._settings.openrouter.base_url,
            model=self._settings.vector_store.embedding_model,
        )

    def _load_metadata_store(self) -> None:
        """Load shared FAISS metadata vector store for entity lookups."""
        try:
            self._metadata_store = FAISS.load_local(
                self._settings.vector_store.metadata_index_path,
                self._embeddings,
                allow_dangerous_deserialization=True,
            )
            logger.info("Loaded metadata vector store from %s", self._settings.vector_store.metadata_index_path)
        except Exception as e:
            logger.warning("Could not load metadata store, creating empty: %s", e)
            # Create empty vector store - will be populated when metadata is indexed
            self._metadata_store = None

    @property
    def agent_type(self) -> str:
        """Return the agent type identifier."""
        return "module-builder"

    async def find_related_entities(self, entity_description: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Find existing entities that may relate to the one being created.

        Args:
            entity_description: Description of the entity being created.
            top_k: Number of related entities to return.

        Returns:
            List of potentially related existing entities.
        """
        if self._metadata_store is None:
            return []

        try:
            docs = self._metadata_store.similarity_search(
                entity_description,
                k=top_k,
                filter={"type": "entity"},
            )
            return [doc.metadata.get("raw", {}) for doc in docs]
        except Exception as e:
            logger.warning("Failed to search metadata store: %s", e)
            return []

    def add_to_context(self, entity: dict[str, Any]) -> None:
        """Add a newly created entity to the conversation context.

        Used for establishing relationships between new entities in the same session.

        Args:
            entity: The entity metadata to add to context.
        """
        self._context_memory.append(entity)

    def get_context_entities(self) -> list[dict[str, Any]]:
        """Get all entities created in this conversation context.

        Returns:
            List of entities in the current conversation.
        """
        return self._context_memory.copy()

    def clear_context(self) -> None:
        """Clear the conversation context."""
        self._context_memory.clear()

    async def process(self, request: Any) -> TemplateResponse:
        """Process a generation request.

        Args:
            request: The request containing the prompt.

        Returns:
            Generated TemplateResponse.
        """
        # Extract prompt from request
        prompt = request.prompt if hasattr(request, "prompt") else str(request)
        return await self.generate_template(prompt)

    async def generate_template(self, prompt: str) -> TemplateResponse:
        """Generate a template based on the user prompt.

        Args:
            prompt: User's description of the template they want.

        Returns:
            A structured TemplateResponse object.

        Raises:
            LLMProviderError: If communication with LLM provider fails.
            TemplateParsingError: If the LLM response cannot be parsed.
            TemplateGenerationError: For other generation failures.
        """
        logger.info("Generating template for prompt: %s", prompt[:100])

        # Find related entities for context
        related_entities = await self.find_related_entities(prompt)
        context_entities = self.get_context_entities()

        # Build context string if we have related entities
        context_str = ""
        if related_entities or context_entities:
            all_entities = related_entities + context_entities
            entity_names = [e.get("name", e.get("id", "unknown")) for e in all_entities]
            context_str = f"\n\nExisting related entities: {', '.join(entity_names)}"

        # Build messages
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=TEMPLATE_GENERATION_PROMPT.format(prompt=prompt)
                + context_str
                + f"\n\n{self._parser.get_format_instructions()}"
            ),
        ]

        try:
            # Invoke LLM with structured output
            response = await self._llm.ainvoke(messages)

            # Parse response to TemplateResponse
            template = self._parser.parse(response.content)
            logger.info("Successfully generated template: %s", template.template_id)

            return template

        except (APIConnectionError, APIError, RateLimitError) as e:
            logger.exception("LLM provider communication failed")
            raise LLMProviderError("Unable to communicate with AI provider") from e

        except OutputParserException as e:
            logger.exception("Failed to parse LLM response")
            raise TemplateParsingError("Unable to parse the generated template response") from e

        except Exception as e:
            logger.exception("Unexpected error during template generation")
            raise TemplateGenerationError("An unexpected error occurred during template generation") from e


# Backward compatibility aliases
TemplateAgent = ModuleBuilderAgent


_agent_instance: Optional[ModuleBuilderAgent] = None


def create_template_agent(settings: Settings) -> ModuleBuilderAgent:
    """Create or return the singleton ModuleBuilderAgent instance.

    Args:
        settings: Application settings.

    Returns:
        The ModuleBuilderAgent instance.

    Note:
        This function is maintained for backward compatibility.
        Prefer using AgentRegistry.get_agent("module-builder", settings) instead.
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ModuleBuilderAgent(settings)
    return _agent_instance
