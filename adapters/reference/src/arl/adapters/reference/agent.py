"""
Agent Reliability Lab — Deterministic Reference Mock Agent Adapter.

Allows scripting exact agent turn outputs, tool calls, and responses
for deterministic unit and integration testing without calling external LLM APIs.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

from arl.protocol.adapter import (
    AgentAdapter,
    AgentInput,
    AgentOutput,
    AgentOutputType,
    AgentSession,
    InterruptionResolution,
    SessionContext,
    ToolCallRecord,
)


class MockAgentAdapter(AgentAdapter):
    """Scriptable mock agent adapter implementing AgentAdapter protocol."""

    def __init__(
        self,
        turn_plan: list[AgentOutput] | None = None,
        custom_handler: Callable[[AgentSession, AgentInput], AgentOutput] | None = None,
    ) -> None:
        self._turn_plan = turn_plan or []
        self._custom_handler = custom_handler
        self._session_turns: dict[str, int] = {}
        self.closed_sessions: list[str] = []

    @property
    def adapter_id(self) -> str:
        return "mock-reference-v1"

    @property
    def framework(self) -> str:
        return "reference-mock"

    @property
    def adapter_version(self) -> str:
        return "1.0.0"

    async def start_session(self, context: SessionContext) -> AgentSession:
        self._session_turns[context.session_id] = 0
        return AgentSession(
            session_id=context.session_id,
            trial_id=context.trial_id,
            agent_version_id=context.agent_version_id,
            framework="reference-mock",
        )

    async def send(self, session: AgentSession, message: AgentInput) -> AgentOutput:
        turn_idx = self._session_turns.get(session.session_id, 0)
        self._session_turns[session.session_id] = turn_idx + 1

        if self._custom_handler is not None:
            return self._custom_handler(session, message)

        if turn_idx < len(self._turn_plan):
            return self._turn_plan[turn_idx]

        # Default fallback response: task finished
        return AgentOutput(
            output_type=AgentOutputType.FINISHED,
            turn_index=message.turn_index,
            raw_text="I have completed your request.",
            prompt_tokens=50,
            completion_tokens=20,
            total_tokens=70,
            cost_usd=0.001,
        )

    async def resume(self, session: AgentSession, interruption: InterruptionResolution) -> AgentOutput:
        return AgentOutput(
            output_type=AgentOutputType.FINISHED,
            turn_index=self._session_turns.get(session.session_id, 0),
            raw_text="Resumed following approval.",
        )

    async def cancel(self, _session: AgentSession) -> None:
        pass

    async def stream(self, session: AgentSession, message: AgentInput) -> AsyncIterator[AgentOutput]:
        output = await self.send(session, message)
        yield output

    async def close_session(self, session: AgentSession) -> None:
        self.closed_sessions.append(session.session_id)

    @classmethod
    def with_single_tool_call(
        cls,
        tool_name: str,
        arguments: dict[str, Any],
        completion_text: str = "Done.",
    ) -> MockAgentAdapter:
        """Helper to create an adapter that calls a tool on turn 0 and completes on turn 1."""
        plan = [
            AgentOutput(
                output_type=AgentOutputType.TOOL_CALLS,
                turn_index=0,
                tool_calls=[ToolCallRecord(tool_call_id="call-001", tool_name=tool_name, arguments=arguments)],
                prompt_tokens=40,
                completion_tokens=25,
            ),
            AgentOutput(
                output_type=AgentOutputType.FINISHED,
                turn_index=1,
                raw_text=completion_text,
                prompt_tokens=80,
                completion_tokens=30,
            ),
        ]
        return cls(turn_plan=plan)
