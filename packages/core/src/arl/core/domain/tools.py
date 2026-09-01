"""
Agent Reliability Lab — Tool Domain Entities.

Entities: ToolDefinition, ToolCall, ToolResult.

Tool calls are the primary unit of observable agent behaviour. Every
tool call is persisted with its arguments, result, timing, fault events,
and idempotency state. Graders operate on this record.

Security note: tool arguments and results must be treated as untrusted.
They may contain prompt injection payloads or exfiltration attempts.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class SideEffectClassification(str, enum.Enum):
    """Whether a tool produces an external observable side effect.

    Used by graders to determine which calls require idempotency checking
    and which require world-state verification.
    """

    NONE = "none"          # read-only (lookups, searches)
    REVERSIBLE = "reversible"    # effect can be undone (e.g. cancel order)
    IRREVERSIBLE = "irreversible"  # effect cannot be undone (e.g. send email)


class IdempotencyBehaviour(str, enum.Enum):
    """How the tool handles duplicate calls.

    IDEMPOTENT: same arguments + idempotency key → same result, no new effect.
    NON_IDEMPOTENT: each call produces a new effect (unsafe without deduplication).
    CONDITIONAL: idempotent only when idempotency key is provided.
    """

    IDEMPOTENT = "idempotent"
    NON_IDEMPOTENT = "non_idempotent"
    CONDITIONAL = "conditional"


class ToolDefinition(BaseModel):
    """A declared tool available in an environment.

    Tool definitions are part of the environment specification.
    They are versioned alongside the environment. Graders use the definition
    to validate that the agent used the correct tool with valid arguments.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID tool definition identifier")
    environment_version_id: str
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., max_length=2000)
    input_schema: dict[str, Any] = Field(..., description="JSON Schema for tool input")
    output_schema: dict[str, Any] = Field(..., description="JSON Schema for tool output")
    side_effect: SideEffectClassification
    idempotency_behaviour: IdempotencyBehaviour
    requires_authentication: bool = Field(default=True)
    requires_authorization: list[str] = Field(
        default_factory=list,
        description="Required permission scopes",
    )
    error_taxonomy: list[str] = Field(
        default_factory=list,
        description="Documented error codes this tool may return",
    )


class ToolCallStatus(str, enum.Enum):
    """Execution status of a tool call."""

    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    FAULT_INJECTED = "fault_injected"


class ToolCall(BaseModel):
    """A single tool invocation by the agent.

    Security note: call_arguments and raw_result are untrusted agent/
    environment content. They must never be eval'd, exec'd, or deserialized
    without schema validation.

    Idempotency: the idempotency_key field allows graders to detect
    duplicate calls that bypass the agent's intended deduplication.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID tool call identifier")
    agent_turn_id: str = Field(..., description="Parent AgentTurn")
    trial_id: str = Field(..., description="Parent Trial")
    sequence_index: int = Field(..., ge=0, description="Call order within the trial")
    tool_name: str = Field(
        ...,
        description=(
            "Tool name as requested by the agent. May differ from any registered "
            "tool — hallucinated tool names are detected by the trajectory grader."
        ),
    )
    # SECURITY: treat as untrusted input
    call_arguments: dict[str, Any] = Field(
        ...,
        description=(
            "Arguments supplied by the agent. "
            "SECURITY: Untrusted. Validate against JSON Schema before use."
        ),
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Agent-supplied idempotency key for side-effecting tools",
    )
    status: ToolCallStatus = Field(default=ToolCallStatus.PENDING)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = Field(default=None)
    latency_ms: int | None = Field(default=None, ge=0)
    fault_injected: bool = Field(default=False)
    fault_event_id: str | None = Field(default=None)
    metadata: dict[str, str] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """The result returned to the agent from a tool call.

    Security note: content is untrusted environment output. It may contain
    prompt injection (indirect prompt injection). The security grader
    monitors tool results for injection patterns.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID result identifier")
    tool_call_id: str
    trial_id: str
    # SECURITY: treat as untrusted
    content: Any = Field(
        ...,
        description=(
            "Tool result content returned to the agent. "
            "SECURITY: Untrusted — may contain prompt injection. "
            "Schema-validate before accepting."
        ),
    )
    is_error: bool = Field(default=False)
    error_code: str | None = Field(default=None)
    error_message: str | None = Field(
        default=None,
        description="Error message. Must not contain secrets or stack traces.",
    )
    schema_valid: bool | None = Field(
        default=None,
        description="Whether the result passed JSON Schema validation",
    )
    returned_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
