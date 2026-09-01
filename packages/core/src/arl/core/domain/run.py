"""
Agent Reliability Lab — EvaluationRun, Budget, and Effect Domain Entities.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from arl.core.state_machine import EvaluationRunState


class EffectOperator(str, enum.Enum):
    """Comparison operator for world-state effect assertions."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    MATCHES_REGEX = "matches_regex"


class ToolCallConstraint(BaseModel):
    """A constraint on tool call behaviour used in forbidden effects."""

    model_config = {"frozen": True}

    name: str = Field(..., description="Tool name to constrain")
    argument_match: dict[str, Any] | None = Field(
        default=None,
        description="If set, only match calls where arguments contain this subset",
    )


class ExpectedEffect(BaseModel):
    """An expected world-state assertion that must be true after a trial.

    Verified by the deterministic world-state grader.
    A trial FAILS if any expected effect is not satisfied.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID")
    scenario_version_id: str
    # JMESPath expression evaluated against the world-state snapshot
    path: str = Field(..., description="JMESPath expression for world-state assertion")
    operator: EffectOperator
    value: Any = Field(..., description="Expected value to compare against")
    description: str = Field(default="", max_length=500)
    is_required: bool = Field(default=True, description="If False, failure is a warning only")


class ForbiddenEffect(BaseModel):
    """A world-state assertion or tool call that must NOT occur.

    Verified by the deterministic forbidden-effect grader.
    Any forbidden effect causes a NOT_READY verdict regardless of other scores.

    Forbidden effects cover two categories:
    1. World-state paths: e.g. refund count > 1
    2. Tool call constraints: e.g. customer.delete was called
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID")
    scenario_version_id: str
    # One of path or tool_call must be set
    path: str | None = Field(
        default=None,
        description="JMESPath expression; if set, checked against world-state snapshot",
    )
    operator: EffectOperator | None = Field(default=None)
    value: Any = Field(default=None)
    tool_call: ToolCallConstraint | None = Field(
        default=None,
        description="If set, checked against tool call log",
    )
    description: str = Field(default="", max_length=500)
    severity: str = Field(default="critical", pattern=r"^(critical|high|medium|low)$")

    @field_validator("path", "tool_call", mode="before")
    @classmethod
    def at_least_one_constraint(cls, v: Any, _info: Any) -> Any:
        return v  # cross-field validation is done in model_validator

    def model_post_init(self, __context: Any) -> None:
        if self.path is None and self.tool_call is None:
            msg = "ForbiddenEffect must specify either 'path' or 'tool_call'"
            raise ValueError(msg)


class Budget(BaseModel):
    """Resource budget limits for a trial.

    All budget checks are deterministic. Budget violations trigger NOT_READY.
    """

    model_config = {"frozen": True}

    max_turns: int = Field(default=20, gt=0, description="Maximum agent turns")
    max_tool_calls: int = Field(default=30, gt=0, description="Maximum total tool invocations")
    max_duration_seconds: int = Field(
        default=300, gt=0, description="Maximum trial wall-clock time"
    )
    max_cost_usd: float = Field(default=1.0, gt=0.0, description="Maximum total model cost in USD")
    max_prompt_tokens: int | None = Field(
        default=None, gt=0, description="Maximum prompt tokens across all turns"
    )
    max_completion_tokens: int | None = Field(
        default=None, gt=0, description="Maximum completion tokens across all turns"
    )


class EvaluationRun(BaseModel):
    """A complete evaluation run.

    An EvaluationRun contains many Trials. Each trial is an independent
    execution of the scenario. Multiple trials enable statistical analysis.

    State is managed by EvaluationRunStateMachine. Direct state mutation
    is prohibited — all changes go through the state machine.

    Security note: Every run is tied to a project and agent version.
    Cross-run data access is controlled by project-level authorization.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID run identifier")
    project_id: str = Field(..., description="Owning project")
    agent_version_id: str = Field(..., description="Agent version under test")
    scenario_version_id: str = Field(..., description="Scenario version being executed")
    environment_version_id: str = Field(..., description="Environment version")

    state: EvaluationRunState = Field(default=EvaluationRunState.CREATED)
    version: int = Field(default=0, ge=0, description="Optimistic concurrency version")

    # Configuration
    trial_count: int = Field(default=1, ge=1, le=1000, description="Number of trials to execute")
    budget: Budget = Field(default_factory=Budget)
    random_seed: int = Field(..., description="Seed for deterministic fault injection")

    # Correlation and tracing
    correlation_id: str = Field(..., description="Correlation ID for log correlation")
    trace_id: str | None = Field(default=None, description="OpenTelemetry trace ID")

    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    # Cancellation
    cancel_requested_by: str | None = Field(default=None)
    cancel_reason: str | None = Field(default=None)

    # Failure
    failure_reason: str | None = Field(
        default=None,
        description="Human-readable reason for failure. Must not contain secrets.",
    )
    failure_code: str | None = Field(
        default=None,
        description="Machine-readable failure code for programmatic handling",
    )

    metadata: dict[str, str] = Field(default_factory=dict)
