"""
Unit tests for MockAgentAdapter.
"""

from __future__ import annotations

from typing import Any

import pytest

from arl.adapters.reference.agent import MockAgentAdapter
from arl.protocol.adapter import (
    AgentInput,
    AgentOutput,
    AgentOutputType,
    InterruptionResolution,
    InterruptionType,
    SessionContext,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_adapter_lifecycle() -> None:
    adapter = MockAgentAdapter()
    assert adapter.adapter_id == "mock-reference-v1"
    assert adapter.framework == "reference-mock"
    assert adapter.adapter_version == "1.0.0"

    context = SessionContext(
        session_id="s1",
        trial_id="t1",
        run_id="r1",
        agent_version_id="av1",
        available_tools=[],
        initial_messages=[{"role": "user", "content": "Hi"}],
        correlation_id="corr-1",
    )

    session = await adapter.start_session(context)
    assert session.session_id == "s1"
    assert session.framework == "reference-mock"

    output = await adapter.send(session, AgentInput(turn_index=0))
    assert output.output_type == AgentOutputType.FINISHED
    assert output.raw_text is not None

    res_output = await adapter.resume(
        session,
        InterruptionResolution(
            interruption_type=InterruptionType.APPROVAL_REQUIRED,
            approved=True,
            resolved_by="user",
        ),
    )
    assert res_output.output_type == AgentOutputType.FINISHED

    await adapter.cancel(session)
    await adapter.close_session(session)
    assert "s1" in adapter.closed_sessions


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_adapter_with_single_tool_call() -> None:
    adapter = MockAgentAdapter.with_single_tool_call(
        tool_name="order.lookup",
        arguments={"customer_id": "cust-1"},
        completion_text="Here is your order.",
    )

    context = SessionContext(
        session_id="s2",
        trial_id="t2",
        run_id="r2",
        agent_version_id="av2",
        available_tools=[],
        initial_messages=[{"role": "user", "content": "Lookup"}],
        correlation_id="corr-2",
    )
    session = await adapter.start_session(context)

    # Turn 0: tool call
    out1 = await adapter.send(session, AgentInput(turn_index=0))
    assert out1.output_type == AgentOutputType.TOOL_CALLS
    assert len(out1.tool_calls) == 1
    assert out1.tool_calls[0].tool_name == "order.lookup"

    # Turn 1: completion
    out2 = await adapter.send(session, AgentInput(turn_index=1, tool_results=[{"status": "ok"}]))
    assert out2.output_type == AgentOutputType.FINISHED
    assert out2.raw_text == "Here is your order."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_adapter_custom_handler() -> None:
    def handler(_sess: Any, inp: AgentInput) -> AgentOutput:
        return AgentOutput(
            output_type=AgentOutputType.TEXT,
            turn_index=inp.turn_index,
            raw_text=f"Turn {inp.turn_index} echo",
        )

    adapter = MockAgentAdapter(custom_handler=handler)
    context = SessionContext(
        session_id="s3",
        trial_id="t3",
        run_id="r3",
        agent_version_id="av3",
        available_tools=[],
        initial_messages=[{"role": "user", "content": "Test"}],
        correlation_id="corr-3",
    )
    session = await adapter.start_session(context)

    out = await adapter.send(session, AgentInput(turn_index=4))
    assert out.raw_text == "Turn 4 echo"
