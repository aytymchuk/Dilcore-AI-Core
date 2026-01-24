"""Schemas for the Persona-based agent."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class PersonaRequest(BaseModel):
    """Request for persona-based agent."""

    user_request: str = Field(..., description="Natural language user request")
    context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Additional context (user session, previous interactions, etc.)",
    )


class FormViewResolution(BaseModel):
    """Resolved form or view information."""

    type: Literal["form", "view"] = Field(..., description="'form' or 'view'")
    id: str = Field(..., description="Form or view identifier")
    name: str = Field(..., description="Human-readable name")
    operation: Literal["create", "read", "update", "delete"] = Field(..., description="The operation to perform")


class DataChange(BaseModel):
    """Suggested data change."""

    field: str = Field(..., description="Field name")
    current_value: Optional[Any] = Field(None, description="Current value if exists")
    suggested_value: Any = Field(..., description="Suggested new value")
    reason: Optional[str] = Field(None, description="Reason for change")


class PersonaResponse(BaseModel):
    """Response from persona-based agent."""

    resolution: FormViewResolution = Field(..., description="Resolved form/view")
    existing_data: Optional[dict[str, Any]] = Field(
        None,
        description="Existing data if found",
    )
    suggested_changes: list[DataChange] = Field(
        default_factory=list,
        description="Suggested data changes",
    )
    explanation: str = Field(..., description="Human-readable explanation")


class MetadataIndexRequest(BaseModel):
    """Request to index metadata into vector store."""

    metadata: dict[str, Any] = Field(..., description="JSON metadata to index")
    metadata_type: Literal["form", "view", "entity", "projection", "relationship", "workflow"] = Field(
        ..., description="Type of metadata being indexed"
    )


class MetadataIndexResponse(BaseModel):
    """Response from metadata indexing."""

    success: bool = Field(..., description="Whether indexing was successful")
    message: str = Field(..., description="Status message")
    metadata_id: str = Field(..., description="ID of the indexed metadata")


class DataIndexRequest(BaseModel):
    """Request to index data into vector store."""

    data: dict[str, Any] = Field(..., description="Data record to index")
    entity_type: str = Field(..., description="Type of entity this data belongs to")


class DataIndexResponse(BaseModel):
    """Response from data indexing."""

    success: bool = Field(..., description="Whether indexing was successful")
    message: str = Field(..., description="Status message")
    data_id: str = Field(..., description="ID of the indexed data")
