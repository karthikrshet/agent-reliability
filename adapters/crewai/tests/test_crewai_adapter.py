"""
Tests for CrewAIAgentAdapter.
"""

from __future__ import annotations

from typing import Any

import pytest

from arl.adapters.crewai.adapter import CrewAIAgentAdapter
from arl.core.errors import AgentExecutionError
from arl.protocol.adapter import (
    AgentAdapter,
    AgentInput,
    AgentOutputType,
    InterruptionResolution,
    InterruptionType,
    SessionContext,
)


@pytest.fixture
def mock_session_context() -> SessionContext:
    return SessionContext(
        session_id="01HRM000000000000000000099",
        correlation_id="corr-crew-001",
        trial_id="trial-crew-001",
        run_id="run-crew-001",
        agent_version_id="agent-crew-v1",
        available_tools=[
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": "Search knowledge base",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
                },
            }
        ],
        initial_messages=[{"role": "user", "content": "How do I reset my password?"}],
    )


@pytest.mark.asyncio
async def test_crewai_adapter_protocol_conformance() -> None:
    """Verify CrewAIAgentAdapter implements the AgentAdapter protocol."""
    adapter = CrewAIAgentAdapter(crew=lambda payload: "Done")
    assert isinstance(adapter, AgentAdapter)
    assert adapter.framework == "crewai"
    assert adapter.adapter_id == "crewai-v1"
    assert adapter.adapter_version == "0.1.0"


@pytest.mark.asyncio
async def test_crewai_adapter_message_turn(mock_session_context: SessionContext) -> None:
    """Verify CrewAI adapter executing a text-producing turn."""

    class MockCrew:
        def kickoff(self, inputs: dict[str, Any]) -> str:
            return f"Processed: {inputs.get('input')}"

    adapter = CrewAIAgentAdapter(crew=MockCrew())
    session = await adapter.create_session(mock_session_context)

    input_data = AgentInput(
        turn_index=0,
        user_messages=[{"role": "user", "content": "Analyze system logs"}],
    )
    output = await adapter.send_input(session, input_data)

    assert output.output_type == AgentOutputType.TEXT
    assert output.raw_text is not None and "Processed: Analyze system logs" in output.raw_text
    assert len(session.adapter_state["history"]) == 2


@pytest.mark.asyncio
async def test_crewai_adapter_async_kickoff(mock_session_context: SessionContext) -> None:
    """Verify CrewAI adapter with async kickoff_async method."""

    class AsyncMockCrew:
        async def kickoff_async(self, inputs: dict[str, Any]) -> dict[str, Any]:
            return {"output": f"Async response to: {inputs.get('input')}"}

    adapter = CrewAIAgentAdapter(crew=AsyncMockCrew())
    session = await adapter.create_session(mock_session_context)

    output = await adapter.send_input(
        session,
        AgentInput(turn_index=0, user_messages=[{"role": "user", "content": "Run diagnostics"}]),
    )
    assert output.output_type == AgentOutputType.TEXT
    assert output.raw_text is not None and "Async response to: Run diagnostics" in output.raw_text


@pytest.mark.asyncio
async def test_crewai_adapter_tool_call_turn(mock_session_context: SessionContext) -> None:
    """Verify CrewAI adapter emitting structured tool calls."""

    def mock_crew_with_tools(payload: dict[str, Any]) -> dict[str, Any]:
        # If tool results exist in payload, finalize answer
        if payload.get("tool_results"):
            return {"output": "Found knowledge base article KB-101"}
        # Otherwise request tool call
        return {
            "tool_calls": [
                {
                    "id": "tc_crew_01",
                    "name": "search_knowledge_base",
                    "arguments": {"query": "password reset"},
                }
            ]
        }

    adapter = CrewAIAgentAdapter(crew=mock_crew_with_tools)
    session = await adapter.create_session(mock_session_context)

    # Turn 1: tool call emitted
    out1 = await adapter.send_input(
        session,
        AgentInput(turn_index=0, user_messages=[{"role": "user", "content": "Help with password"}]),
    )
    assert out1.output_type == AgentOutputType.TOOL_CALLS
    assert len(out1.tool_calls) == 1
    assert out1.tool_calls[0].tool_name == "search_knowledge_base"

    # Turn 2: tool result passed back
    tool_result = {
        "tool_call_id": "tc_crew_01",
        "result": {"article": "KB-101", "title": "Reset steps"},
    }
    out2 = await adapter.send_input(
        session,
        AgentInput(turn_index=1, tool_results=[tool_result]),
    )
    assert out2.output_type == AgentOutputType.TEXT
    assert out2.raw_text is not None and "Found knowledge base article" in out2.raw_text


@pytest.mark.asyncio
async def test_crewai_adapter_interruption_and_resume(mock_session_context: SessionContext) -> None:
    """Verify human-in-the-loop interruption request and resume flow."""

    def mock_interrupting_crew(payload: dict[str, Any]) -> dict[str, Any]:
        if "Resumed after review" in payload.get("input", ""):
            return {"output": "Transfer executed successfully"}
        return {
            "interrupted": True,
            "task_id": "transfer_funds",
            "prompt": "Approve $5,000 transfer?",
        }

    adapter = CrewAIAgentAdapter(crew=mock_interrupting_crew)
    session = await adapter.create_session(mock_session_context)

    out_interrupt = await adapter.send_input(
        session,
        AgentInput(turn_index=0, user_messages=[{"role": "user", "content": "Transfer $5,000"}]),
    )
    assert out_interrupt.output_type == AgentOutputType.INTERRUPTED
    assert (
        out_interrupt.raw_text is not None and "Approve $5,000 transfer" in out_interrupt.raw_text
    )

    # Resume turn
    resolution = InterruptionResolution(
        interruption_type=InterruptionType.APPROVAL_REQUIRED,
        approved=True,
        resolved_by="user_manager_01",
        resolution_payload={"notes": "Manager approved transfer"},
    )
    out_resumed = await adapter.resume_interrupted(session, resolution)
    assert out_resumed.output_type == AgentOutputType.TEXT
    assert (
        out_resumed.raw_text is not None
        and "Transfer executed successfully" in out_resumed.raw_text
    )


@pytest.mark.asyncio
async def test_crewai_adapter_streaming(mock_session_context: SessionContext) -> None:
    """Verify streaming outputs from CrewAIAgentAdapter."""
    adapter = CrewAIAgentAdapter(crew=lambda payload: "Streamed result")
    session = await adapter.create_session(mock_session_context)

    chunks = [
        chunk
        async for chunk in adapter.stream_output(
            session,
            AgentInput(turn_index=0, user_messages=[{"role": "user", "content": "Stream me"}]),
        )
    ]

    assert len(chunks) == 1
    assert chunks[0].raw_text == "Streamed result"


@pytest.mark.asyncio
async def test_crewai_adapter_invalid_import_and_lifecycle(
    mock_session_context: SessionContext,
) -> None:
    """Verify error handling on malformed import strings and session termination."""
    with pytest.raises(ValueError, match="Invalid CrewAI import string"):
        CrewAIAgentAdapter(crew="no_colon_import_path")

    with pytest.raises(ImportError, match="Failed to import CrewAI target"):
        CrewAIAgentAdapter(crew="nonexistent_pkg_xyz:crew_target")

    adapter = CrewAIAgentAdapter(crew=lambda p: "ok")
    session = await adapter.create_session(mock_session_context)
    await adapter.cancel_session(session)
    assert session.adapter_state.get("cancelled") is True

    await adapter.end_session(session)
    assert len(session.adapter_state) == 0


@pytest.mark.asyncio
async def test_crewai_adapter_unsupported_crew_object(mock_session_context: SessionContext) -> None:
    """Verify clear error when object has no execution method."""
    adapter = CrewAIAgentAdapter(crew=object())
    session = await adapter.create_session(mock_session_context)

    with pytest.raises(AgentExecutionError, match="no recognized execution method"):
        await adapter.send_input(
            session,
            AgentInput(turn_index=0, user_messages=[{"role": "user", "content": "Hi"}]),
        )
