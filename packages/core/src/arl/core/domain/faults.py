"""
Agent Reliability Lab — Fault Domain Entities.

Every injected fault creates a FaultEvent. The same scenario version +
seed always produces the same fault schedule (deterministic).
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class FaultType(str, enum.Enum):
    """Enumeration of all supported fault types.

    Values stored in DB — do not rename existing entries.
    """

    CONNECTION_REFUSED = "connection_refused"
    DNS_FAILURE = "dns_failure"
    TIMEOUT_BEFORE_EXECUTION = "timeout_before_execution"
    TIMEOUT_AFTER_EXECUTION = "timeout_after_execution"
    HTTP_429 = "http_429"
    HTTP_500 = "http_500"
    HTTP_503 = "http_503"
    MALFORMED_JSON = "malformed_json"
    SCHEMA_INVALID_RESULT = "schema_invalid_result"
    EMPTY_RESULT = "empty_result"
    DELAYED_RESULT = "delayed_result"
    DUPLICATED_RESULT = "duplicated_result"
    STALE_RESULT = "stale_result"
    PARTIAL_SUCCESS = "partial_success"
    DROPPED_RESPONSE = "dropped_response"
    REORDERED_CONCURRENT_RESPONSES = "reordered_concurrent_responses"
    CANCELLATION_DURING_EXECUTION = "cancellation_during_execution"
    WORKER_TERMINATION = "worker_termination"
    DATABASE_DEADLOCK = "database_deadlock"
    REDIS_UNAVAILABILITY = "redis_unavailability"


class FaultTrigger(BaseModel):
    """When to trigger a fault."""

    model_config = {"frozen": True}

    # Trigger on the Nth invocation of the target tool (1-based)
    invocation: int | None = Field(default=None, ge=1)
    # Trigger after N seconds of trial execution
    after_seconds: float | None = Field(default=None, ge=0.0)
    # Trigger when arguments contain this pattern
    argument_contains: dict[str, Any] | None = Field(default=None)


class FaultBehaviour(BaseModel):
    """How the fault manifests."""

    model_config = {"frozen": True}

    fault_type: FaultType
    delay_ms: int = Field(
        default=0,
        ge=0,
        description="Delay before the fault response (e.g. for timeout simulation)",
    )
    # For HTTP faults
    http_status: int | None = Field(default=None)
    retry_after_seconds: int | None = Field(default=None)
    # For timeout_after_execution: the side effect is committed before the timeout
    side_effect_committed: bool = Field(
        default=False,
        description=(
            "True for timeout_after_execution faults. "
            "The tool's side effect has been applied before the error is returned. "
            "This is the core scenario for idempotency testing."
        ),
    )
    # For malformed / schema-invalid responses
    response_body: str | None = Field(default=None)
    extra_config: dict[str, Any] = Field(default_factory=dict)


class FaultPlan(BaseModel):
    """The complete fault injection plan for a scenario trial.

    A plan contains multiple fault specifications. The scheduler applies
    them deterministically based on the trial's fault_seed.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID")
    scenario_version_id: str
    entries: list[FaultPlanEntry] = Field(default_factory=list)


class FaultPlanEntry(BaseModel):
    """A single entry in a FaultPlan."""

    model_config = {"frozen": True}

    target: str = Field(
        ...,
        description="Tool name to inject the fault into (e.g. 'refund.create')",
    )
    trigger: FaultTrigger
    behaviour: FaultBehaviour


class FaultEvent(BaseModel):
    """A recorded occurrence of an injected fault.

    Every injected fault creates a FaultEvent. Reports link to FaultEvents
    as evidence for fault-recovery grading.

    A trial that claims 'recovered' must link to FaultEvents proving what
    was injected and WorldStateSnapshots proving final state is correct.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID fault event identifier")
    trial_id: str
    tool_call_id: str | None = Field(
        default=None,
        description="Tool call that triggered this fault, if applicable",
    )
    fault_type: FaultType
    target_tool: str
    trigger_invocation: int | None = Field(
        default=None,
        description="Which invocation number triggered this fault",
    )
    behaviour: FaultBehaviour
    fault_seed: int = Field(..., description="Trial's fault seed — for reproducibility")
    injected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    agent_observed_error: bool | None = Field(
        default=None,
        description="Whether the agent received an error response (True) or a silent fault",
    )
