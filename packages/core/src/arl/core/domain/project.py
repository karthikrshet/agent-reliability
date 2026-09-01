"""
Agent Reliability Lab — Project Domain Entity.

A Project is the top-level organisational unit. All agents, scenarios,
and runs belong to a project. Projects enforce namespace isolation.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator


class Project(BaseModel):
    """Top-level organisational container.

    Attributes:
        id: Stable project identifier (ULID).
        name: Human-readable project name (unique within the system).
        description: Optional project description.
        owner_id: User or service account that owns this project.
        created_at: UTC timestamp of project creation.
        updated_at: UTC timestamp of last modification.
        is_active: Soft-delete flag. Inactive projects reject new runs.
        version: Optimistic concurrency version counter.
        metadata: Arbitrary string key-value pairs for extensibility.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID project identifier")
    name: str = Field(..., min_length=1, max_length=120, description="Unique project name")
    description: str = Field(default="", max_length=1000)
    owner_id: str = Field(..., description="Owner user or service-account ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = Field(default=True)
    version: int = Field(default=0, ge=0, description="Optimistic concurrency version")
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def name_must_be_slug_compatible(cls, v: str) -> str:
        """Names must be safe for use in URLs and file paths."""
        stripped = v.strip()
        if not stripped:
            msg = "Project name must not be blank"
            raise ValueError(msg)
        return stripped

    def with_update(self, **kwargs: object) -> Project:
        """Return a new Project instance with updated fields and bumped version."""
        data = self.model_dump()
        data.update(kwargs)
        data["updated_at"] = datetime.now(UTC)
        data["version"] = self.version + 1
        return Project(**data)
