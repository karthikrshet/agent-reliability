"""
Agent Reliability Lab — Agent Adapter Protocol and Session Schemas.

Defines the stable, framework-independent contract for all agent adapters.
Any framework (HTTP, OpenAI Agents SDK, LangGraph, custom) must implement
AgentAdapter to be testable by Agent Reliability Lab.

Design principles (ADR-003):
- Framework-independent: adapters translate framework-specific calls to this contract.
- Observable behaviour only: no hidden chain-of-thought required.
- Fully typed: every input and output is schema-validated.
- Streaming support: adapters may yield partial outputs through AgentOutput.streaming.
- Interruption support: human-in-the-loop approvals are modelled explicitly.

Security note: All data flowing through this protocol from the agent is untrusted.
Adapters must not execute or eval any content returned by the agent.
"""

from __future__ import annotations

import enum
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# Session and context schemas
# ─────────────────────────────────────────────────────────────────────────────


class SessionContext(BaseModel):
    """Context passed to the adapter when starting a new agent session.

    Contains everything the adapter needs to initialise the agent for a
    specific trial run. Adapters must not store or log sensitive values
    from this context beyond the duration of the session.
    """

    model_config = {"frozen": True}

    session_id: str = Field(..., description="Unique ULID session identifier")
    trial_id: str = Field(..., description="Trial this session belongs to")
    run_id: str = Field(..., description="Evaluation run this trial belongs to")
    agent_version_id: str

    # Environment tool definitions available to the agent
    available_tools: list[dict[str, Any]] = Field(
        ...,
        description=(
            "Tool definitions in the format the adapter/framework expects. "
            "Typically OpenAI function-calling format."
        ),
    )
    # Scenario conversation starter
    initial_messages: list[dict[str, str]] = Field(
        ...,
        description="Initial conversation messages (role + content pairs)",
    )
    # Budget constraints communicated to the adapter
    max_turns: int = Field(default=20, gt=0)
    max_tool_calls: int = Field(default=30, gt=0)
    max_duration_seconds: int = Field(default=300, gt=0)

    # Metadata for adapter-specific configuration
    adapter_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Adapter-specific configuration (e.g. model override for a specific trial)",
    )
    correlation_id: str = Field(...)
    trace_id: str | None = Field(default=None)


class AgentSession(BaseModel):
    """An active session returned by start_session.

    Adapters populate this with framework-specific session state.
    The harness treats it as opaque beyond the typed fields.
    """

    model_config = {"frozen": True}

    session_id: str
    trial_id: str
    agent_version_id: str
    framework: str = Field(..., description="Framework identifier (e.g. 'http', 'langgraph')")
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # Adapter-specific opaque state (e.g. thread ID, session token)
    # SECURITY: must not contain secrets or PII
    adapter_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Framework-specific session state. Must not contain secrets.",
    )


class ToolCallRecord(BaseModel):
    """A tool call observed in an agent turn.

    Populated by the adapter from the agent's output.
    SECURITY: arguments are untrusted agent content.
    """

    model_config = {"frozen": True}

    tool_call_id: str = Field(
        ...,
        description="Framework-native tool call ID (used to return results)",
    )
    tool_name: str
    # SECURITY: untrusted — validate against JSON Schema before use
    arguments: dict[str, Any] = Field(
        ...,
        description=(
            "Tool call arguments as provided by the agent. "
            "SECURITY: Untrusted. Validate against tool's JSON Schema before use."
        ),
    )


class AgentInput(BaseModel):
    """Input sent to the agent for a single turn."""

    model_config = {"frozen": True}

    turn_index: int = Field(..., ge=0)
    # Tool results to deliver (empty on first turn)
    tool_results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Tool results in the format the adapter/framework expects",
    )
    # Additional user messages (empty if no new user message this turn)
    user_messages: list[dict[str, str]] = Field(default_factory=list)


class AgentOutputType(str, enum.Enum):
    """What kind of output the agent produced."""

    TEXT = "text"  # Agent produced a text response (conversation turn)
    TOOL_CALLS = "tool_calls"  # Agent wants to call tools
    INTERRUPTED = "interrupted"  # Agent is waiting for human approval
    ERROR = "error"  # Agent reported an error
    FINISHED = "finished"  # Agent believes it has completed the task


class InterruptionType(str, enum.Enum):
    """Why the agent was interrupted."""

    APPROVAL_REQUIRED = "approval_required"
    CLARIFICATION_NEEDED = "clarification_needed"
    BUDGET_PAUSE = "budget_pause"


class AgentOutput(BaseModel):
    """Output from a single agent turn.

    Adapters populate this from the framework's raw response.
    All agent content fields are untrusted — the harness validates and
    escapes before any further processing.

    SECURITY: raw_text, tool_calls[*].arguments are untrusted agent content.
    """

    model_config = {"frozen": True}

    output_type: AgentOutputType
    turn_index: int = Field(..., ge=0)

    # Text content — SECURITY: untrusted; HTML-escape before rendering
    raw_text: str | None = Field(
        default=None,
        description=("Agent's text response. SECURITY: Untrusted. HTML-escape before rendering."),
    )
    # Tool calls — SECURITY: arguments are untrusted
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)

    # Interruption metadata
    interruption_type: InterruptionType | None = Field(default=None)
    interruption_payload: dict[str, Any] = Field(default_factory=dict)

    # Usage metrics (populated by adapter when available)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0.0)
    latency_ms: int | None = Field(default=None, ge=0)

    # Model metadata (populated by adapter when available from provider)
    model_name: str | None = Field(default=None)
    model_version: str | None = Field(default=None)
    finish_reason: str | None = Field(default=None)

    # Error info (when output_type == ERROR)
    error_code: str | None = Field(default=None)
    error_message: str | None = Field(
        default=None,
        description="Error message. Must not contain secrets or stack traces.",
    )

    produced_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InterruptionResolution(BaseModel):
    """Resolution of an agent interruption (e.g. approval granted/denied)."""

    model_config = {"frozen": True}

    interruption_type: InterruptionType
    approved: bool
    resolution_payload: dict[str, Any] = Field(default_factory=dict)
    resolved_by: str = Field(..., description="Actor that resolved the interruption")
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ─────────────────────────────────────────────────────────────────────────────
# Agent Adapter Protocol
# ─────────────────────────────────────────────────────────────────────────────


@runtime_checkable
class AgentAdapter(Protocol):
    """Stable, framework-independent agent adapter protocol.

    All agent frameworks (HTTP, OpenAI Agents SDK, LangGraph, etc.) must
    implement this protocol to be tested by Agent Reliability Lab.

    Adapter identity properties must be populated — they are recorded
    in every trial for reproducibility and debugging.

    SECURITY:
    - Adapters must not execute or eval agent outputs.
    - Adapters must not store session state beyond session lifetime.
    - Adapters must not expose harness credentials to the agent.
    - Adapters must redact secrets from error messages.

    Follows the agent-design skill (karthikrshet/aiskills):
    - Tool permissions are declared in SessionContext.available_tools
    - Side effects require idempotency keys (enforced by graders)
    - Human escalation is modelled through InterruptionType
    """

    # ── Identity (populated at adapter construction) ──────────────────────

    @property
    def adapter_id(self) -> str:
        """Stable identifier for this adapter type (e.g. 'http-v1')."""
        ...

    @property
    def framework(self) -> str:
        """Framework name (e.g. 'http', 'openai-agents', 'langgraph')."""
        ...

    @property
    def adapter_version(self) -> str:
        """Adapter version string."""
        ...

    # ── Session lifecycle ─────────────────────────────────────────────────

    async def start_session(
        self,
        context: SessionContext,
    ) -> AgentSession:
        """Initialise a new agent session for a trial.

        Must not begin any execution — only initialise state.
        Raises InfrastructureError if the agent endpoint is unreachable.
        """
        ...

    async def send(
        self,
        session: AgentSession,
        message: AgentInput,
    ) -> AgentOutput:
        """Send a turn to the agent and receive its output.

        Blocks until the agent produces an output (text, tool_calls, or error).
        Must respect the session's budget limits — raise BudgetExceededError if
        the agent has exceeded its configured limits.

        SECURITY: Content returned by the agent must not be executed.
        """
        ...

    async def resume(
        self,
        session: AgentSession,
        interruption: InterruptionResolution,
    ) -> AgentOutput:
        """Resume an interrupted session with the interruption resolution.

        Called after a human approves or denies an agent action.
        """
        ...

    async def cancel(
        self,
        session: AgentSession,
    ) -> None:
        """Request cancellation of an in-progress session.

        Must not raise if the session is already complete.
        """
        ...

    async def close_session(
        self,
        session: AgentSession,
    ) -> None:
        """Release resources associated with the session.

        Called after every session — even after errors.
        Must be idempotent.
        """
        ...

    def stream(
        self,
        session: AgentSession,
        message: AgentInput,
    ) -> AsyncIterator[AgentOutput]:
        """Optional: stream partial agent outputs.

        Not all adapters support streaming. Adapters that do not support
        streaming should raise NotImplementedError.
        """
        ...
