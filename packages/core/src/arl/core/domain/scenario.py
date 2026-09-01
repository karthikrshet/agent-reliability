"""Agent Reliability Lab — Scenario Domain Entities."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class Scenario(BaseModel):
    """A scenario definition — stable identity across versions."""

    model_config = {"frozen": True}

    id: str
    project_id: str
    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(
        ...,
        description=(
            "Scenario category: tool-correctness | failure-recovery | "
            "state-and-memory | security | resource-control"
        ),
    )
    description: str = Field(default="", max_length=5000)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = Field(default=True)


class ScenarioVersion(BaseModel):
    """An immutable versioned snapshot of a scenario.

    Scenario versions are immutable once created. Historical runs reference
    specific versions so that results remain reproducible even after
    scenario updates.

    The full scenario YAML is stored as a string (schema-validated on load).
    """

    model_config = {"frozen": True}

    id: str
    scenario_id: str
    version_tag: str = Field(..., min_length=1, max_length=64)
    schema_version: str = Field(..., description="Scenario schema version (e.g. '1.0')")
    environment_name: str
    environment_version: str
    seed: int = Field(..., description="Default scenario seed for deterministic fault injection")
    # Stored YAML source (schema-validated before storage)
    source_yaml: str = Field(..., description="Full scenario YAML, validated against schema")
    source_hash: str = Field(..., description="SHA-256 of source_yaml for integrity checks")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tags: list[str] = Field(default_factory=list)
    severity: str = Field(
        default="medium",
        pattern=r"^(critical|high|medium|low|info)$",
    )
    metadata: dict[str, str] = Field(default_factory=dict)
