"""Schemas module."""

from .errors import ProblemDetails

# Persona schemas
from .persona import (
    DataChange,
    DataIndexRequest,
    DataIndexResponse,
    FormViewResolution,
    MetadataIndexRequest,
    MetadataIndexResponse,
    PersonaRequest,
    PersonaResponse,
)
from .request import GenerateRequest
from .response import TemplateResponse
from .streaming import StreamEvent, StreamEventType, StreamingTemplateResponse

__all__ = [
    # Existing schemas
    "GenerateRequest",
    "TemplateResponse",
    "StreamEvent",
    "StreamEventType",
    "StreamingTemplateResponse",
    "ProblemDetails",
    # Persona schemas
    "PersonaRequest",
    "PersonaResponse",
    "FormViewResolution",
    "DataChange",
    "MetadataIndexRequest",
    "MetadataIndexResponse",
    "DataIndexRequest",
    "DataIndexResponse",
]
