"""Agent Reliability Lab — Environment Domain Entities."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class Environment(BaseModel):
    """A named stateful testing environment.

    Environments are containerised services that provide tools and
    world-state for scenario execution (e.g. customer-support).
    """

    model_config = {"frozen": True}

    id: str
    project_id: str
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = Field(default=True)


class EnvironmentVersion(BaseModel):
    """An immutable versioned snapshot of an environment.

    Pinned by scenario versions so historical runs are reproducible.
    Schema changes require a new version — never mutate an existing one.
    """

    model_config = {"frozen": True}

    id: str
    environment_id: str
    version_tag: str = Field(..., min_length=1, max_length=64)
    schema_version: str = Field(..., description="World-state snapshot schema version")
    docker_image: str | None = Field(
        default=None,
        description="Docker image digest (not tag) for reproducible builds",
    )
    tool_count: int = Field(default=0, ge=0)
    default_seed: int = Field(
        ...,
        description="Default deterministic seed for data generation in this environment version",
    )
    world_state_schema: dict[str, Any] = Field(
        ...,
        description="JSON Schema that world-state snapshots must conform to",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    release_notes: str = Field(default="", max_length=2000)
    metadata: dict[str, str] = Field(default_factory=dict)
