"""Static JSON response structure for template generation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TemplateStatus(str, Enum):
    """Template lifecycle status."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class TemplateField(BaseModel):
    """Individual field within a template section."""

    name: str = Field(..., description="Field identifier")
    type: str = Field(
        ...,
        description="Data type (string, number, boolean, array, object)",
    )
    required: bool = Field(default=True, description="Whether field is required")
    description: Optional[str] = Field(default=None, description="Field description")
    default_value: Any = Field(
        default=None,
        description="Default value (can be string, number, boolean, etc.)",
    )


class TemplateSection(BaseModel):
    """Logical grouping of fields within a template."""

    section_id: str = Field(..., description="Unique section identifier")
    title: str = Field(..., description="Section display title")
    description: Optional[str] = Field(default=None, description="Section description")
    fields: list[TemplateField] = Field(
        default_factory=list,
        description="Fields in this section",
    )


class TemplateMetadata(BaseModel):
    """Template metadata information."""

    version: str = Field(default="1.0.0", description="Template version")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp",
    )
    author: str = Field(default="AI Agent", description="Template author")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")


class TemplateResponse(BaseModel):
    """Main response structure for generated templates.

    This is the static structure that all AI-generated templates must follow.
    """

    template_id: str = Field(..., description="Unique identifier for the template")
    template_name: str = Field(..., description="Human-readable template name")
    description: str = Field(..., description="Template purpose description")
    status: TemplateStatus = Field(
        default=TemplateStatus.DRAFT,
        description="Template lifecycle status",
    )
    metadata: TemplateMetadata = Field(
        default_factory=TemplateMetadata,
        description="Template metadata",
    )
    sections: list[TemplateSection] = Field(
        default_factory=list,
        description="Template sections containing fields",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "template_id": "usr-reg-001",
                    "template_name": "User Registration Form",
                    "description": "Template for collecting user registration data",
                    "status": "draft",
                    "metadata": {
                        "version": "1.0.0",
                        "created_at": "2026-01-14T23:24:00Z",
                        "author": "AI Agent",
                        "tags": ["user", "registration", "form"],
                    },
                    "sections": [
                        {
                            "section_id": "personal-info",
                            "title": "Personal Information",
                            "description": "Basic user details",
                            "fields": [
                                {
                                    "name": "email",
                                    "type": "string",
                                    "required": True,
                                    "description": "User email address",
                                },
                                {
                                    "name": "full_name",
                                    "type": "string",
                                    "required": True,
                                },
                            ],
                        }
                    ],
                }
            ]
        }
    }
