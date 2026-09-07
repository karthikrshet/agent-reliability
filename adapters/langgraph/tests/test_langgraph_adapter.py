"""
Tests for LangGraphAgentAdapter.
"""

from __future__ import annotations

from typing import Any

import pytest

from arl.adapters.langgraph.adapter import LangGraphAgentAdapter
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
        session_id="01HRM000000000000000000001",
        correlation_id="corr-001",
        trial_id="trial-001",
        run_id="run-001",
        agent_version_id="agent-v1",
        available_tools=[
            {
                "type": "function",
                "function": {
                    "name": "lookup_order",
                    "description": "Lookup order by id",
                    "parameters": {
                        "type": "object",
                        "properties": {"order_id": {"type": "string"}},
                    },
                },
            }
        ],
        initial_messages=[{"role": "user", "content": "Where is my order #1234?"}],
    )


@pytest.mark.asyncio
async def test_langgraph_adapter_protocol_conformance() -> None:
    """Verify LangGraphAgentAdapter implements the AgentAdapter protocol."""
    adapter = LangGraphAgentAdapter(graph=lambda state, config: state)
    assert isinstance(adapter, AgentAdapter)
    assert adapter.framework == "langgraph"
    assert adapter.adapter_id == "langgraph-v1"
    assert adapter.adapter_version == "0.1.0"


@pytest.mark.asyncio
async def test_langgraph_adapter_message_turn(mock_session_context: SessionContext) -> None:
    """Verify graph producing a text message."""

    def simple_chat_graph(state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        messages = list(state.get("messages", []))
        messages.append({"role": "assistant", "content": "Your order #1234 is on the way."})
        return {"messages": messages}

    adapter = LangGraphAgentAdapter(graph=simple_chat_graph)
    session = await adapter.start_session(mock_session_context)

    # Execute user turn
    turn_input = AgentInput(
        turn_index=0,
        user_messages=[{"role": "user", "content": "Any updates on my order?"}],
    )
    output = await adapter.send(session, turn_input)

    assert output.output_type == AgentOutputType.TEXT
    assert output.raw_text == "Your order #1234 is on the way."

    await adapter.close_session(session)
    assert len(session.adapter_state) == 0


@pytest.mark.asyncio
async def test_langgraph_adapter_tool_call_turn(mock_session_context: SessionContext) -> None:
    """Verify graph producing tool calls."""

    class FakeAIMessage:
        def __init__(self, content: str, tool_calls: list[dict[str, Any]]) -> None:
            self.content = content
            self.tool_calls = tool_calls

    async def tool_calling_graph(state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        messages = list(state.get("messages", []))
        messages.append(
            FakeAIMessage(
                content="Looking up order...",
                tool_calls=[
                    {
                        "id": "call_ord_99",
                        "name": "lookup_order",
                        "args": {"order_id": "1234"},
                    }
                ],
            )
        )
        return {"messages": messages}

    adapter = LangGraphAgentAdapter(graph=tool_calling_graph)
    session = await adapter.start_session(mock_session_context)

    turn_input = AgentInput(
        turn_index=0,
        user_messages=[{"role": "user", "content": "Please check status of order 1234"}],
    )
    output = await adapter.send(session, turn_input)

    assert output.output_type == AgentOutputType.TOOL_CALLS
    assert len(output.tool_calls) == 1
    assert output.tool_calls[0].tool_name == "lookup_order"
    assert output.tool_calls[0].tool_call_id == "call_ord_99"
    assert output.tool_calls[0].arguments == {"order_id": "1234"}

    # Simulate tool result feedback into graph
    result_input = AgentInput(
        turn_index=1,
        tool_results=[
            {
                "tool_call_id": "call_ord_99",
                "content": '{"status": "delivered", "date": "2026-09-01"}',
            }
        ],
    )
    res_output = await adapter.send(session, result_input)
    assert res_output.output_type == AgentOutputType.TOOL_CALLS

    await adapter.close_session(session)


@pytest.mark.asyncio
async def test_langgraph_adapter_invalid_import_path() -> None:
    """Verify error raised on invalid import string."""
    with pytest.raises(ValueError, match="Invalid LangGraph import path"):
        LangGraphAgentAdapter(graph="invalid_path_without_colon")


@pytest.mark.asyncio
async def test_langgraph_adapter_resume_interrupted(mock_session_context: SessionContext) -> None:
    """Verify resuming an interrupted execution."""

    def echo_graph(state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        messages = list(state.get("messages", []))
        messages.append({"role": "assistant", "content": "Action resumed successfully"})
        return {"messages": messages}

    adapter = LangGraphAgentAdapter(graph=echo_graph)
    session = await adapter.start_session(mock_session_context)

    res = await adapter.resume(
        session,
        InterruptionResolution(
            interruption_type=InterruptionType.APPROVAL_REQUIRED,
            approved=True,
            resolved_by="admin",
            resolution_payload={"action": "approve"},
        ),
    )
    assert res.output_type == AgentOutputType.TEXT
    assert res.raw_text == "Action resumed successfully"
    await adapter.close_session(session)
