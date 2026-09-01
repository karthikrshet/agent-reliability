"""
Agent Reliability Lab — Agent Domain Entities.

Entities: AgentDefinition, AgentVersion, ModelConfiguration, AgentTurn.

Every run records the exact agent version, model configuration, and
model provider metadata at execution time. Historical runs must be
reproducible even after the agent configuration changes.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class AgentFramework(str, enum.Enum):
    """Supported agent frameworks.

    HTTP is the universal adapter; others are native adapters.
    """

    HTTP = "http"
    OPENAI_AGENTS = "openai-agents"
    LANGGRAPH = "langgraph"
    REFERENCE = "reference"  # internal deterministic reference adapter
    UNKNOWN = "unknown"


class ModelProvider(str, enum.Enum):
    """Known model providers.

    UNKNOWN is used when the provider cannot be determined from the adapter.
    """

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    COHERE = "cohere"
    LOCAL = "local"
    UNKNOWN = "unknown"


class ModelConfiguration(BaseModel):
    """Captures the full model configuration at execution time.

    All fields that affect output distribution must be recorded so that
    runs can be reproduced with the same settings.
    """

    model_config = {"frozen": True}

    provider: ModelProvider = Field(..., description="Model provider")
    model_name: str = Field(..., min_length=1, description="Model identifier")
    model_version: str | None = Field(
        default=None,
        description="Provider-reported model version or snapshot date, if available",
    )
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    max_tokens: int | None = Field(default=None, gt=0)
    seed: int | None = Field(default=None, description="Sampling seed, if the provider supports it")
    extra_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific parameters not captured above",
    )


class AgentDefinition(BaseModel):
    """Stable definition of an agent under test.

    An AgentDefinition is created once and has many AgentVersions.
    The definition captures the agent's identity and framework;
    configuration details are in AgentVersion.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID agent identifier")
    project_id: str = Field(..., description="Owning project ID")
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    framework: AgentFramework = Field(..., description="Adapter framework")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    is_active: bool = Field(default=True)
    version: int = Field(default=0, ge=0)


class AgentVersion(BaseModel):
    """A specific versioned snapshot of an agent configuration.

    Immutable after creation. Evaluation runs reference a specific
    AgentVersion so that results remain tied to an exact configuration.

    Security note: endpoint is validated at evaluation time to prevent
    SSRF. The stored value may be localhost for development agents, but
    production deployment must run SSRF validation before any HTTP call.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID version identifier")
    agent_id: str = Field(..., description="Parent AgentDefinition ID")
    version_tag: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Human-readable version tag (e.g. v1.2.0, git-sha)",
    )
    endpoint: HttpUrl | None = Field(
        default=None,
        description=(
            "HTTP endpoint for HTTP adapter agents. "
            "SSRF validation is enforced at call time, not storage time."
        ),
    )
    model_configuration: ModelConfiguration | None = Field(
        default=None,
        description="Model configuration, if known at registration time",
    )
    prompt_version: str | None = Field(
        default=None,
        description="Prompt or system-message version identifier",
    )
    system_prompt_hash: str | None = Field(
        default=None,
        description="SHA-256 hash of the system prompt for change detection",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notes: str = Field(default="", max_length=2000)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("version_tag")
    @classmethod
    def validate_version_tag(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            msg = "version_tag must not be blank"
            raise ValueError(msg)
        return stripped


class AgentTurn(BaseModel):
    """A single conversational turn from the agent.

    Records the agent's response, all tool calls made, token usage,
    and latency. This is the primary unit of trajectory analysis.

    Security note: raw_response is stored as-is from the agent. It must
    be treated as untrusted content in all rendering contexts.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID turn identifier")
    trial_id: str = Field(..., description="Parent trial ID")
    turn_index: int = Field(..., ge=0, description="Zero-based turn sequence number")
    agent_version_id: str = Field(..., description="Agent version that produced this turn")
    # Content — treated as untrusted; never rendered without escaping
    raw_response: str | None = Field(
        default=None,
        description=(
            "Raw text response from the agent. "
            "SECURITY: treat as untrusted; always HTML-escape before rendering."
        ),
    )
    finish_reason: str | None = Field(
        default=None,
        description="Provider finish_reason (stop, tool_calls, length, content_filter, etc.)",
    )
    # Usage metrics — used by budget grader and cost reporting
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0.0)
    latency_ms: int | None = Field(default=None, ge=0)
    # Timing
    started_at: datetime = Field(...)
    ended_at: datetime | None = Field(default=None)
    # Error state
    error: str | None = Field(
        default=None,
        description="Error message if the turn failed. Must not contain secrets.",
    )
    metadata: dict[str, str] = Field(default_factory=dict)
