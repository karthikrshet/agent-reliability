"""
Unit tests for OpenAIAgentAdapter.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from arl.adapters.openai.adapter import OpenAIAgentAdapter
from arl.protocol.adapter import (
    AgentInput,
    AgentOutputType,
    InterruptionResolution,
    InterruptionType,
    SessionContext,
)


class MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, response_data: dict[str, Any], status_code: int = 200) -> None:
        self.response_data = response_data
        self.status_code = status_code

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=self.status_code,
            json=self.response_data,
            request=request,
        )


@pytest.mark.asyncio
async def test_openai_adapter_send_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "lookup_order",
                                "arguments": '{"order_id": "ord-001"}',
                            },
                        }
                    ],
                }
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
    }

    adapter = OpenAIAgentAdapter(endpoint_url="https://api.openai.com/v1", api_key="sk-test")
    client = httpx.AsyncClient(transport=MockTransport(mock_resp))
    adapter._client = client

    ctx = SessionContext(
        session_id="sess-01",
        trial_id="tr-01",
        run_id="run-01",
        agent_version_id="ag-01",
        available_tools=[{"name": "lookup_order", "description": "Lookup order", "parameters": {}}],
        initial_messages=[{"role": "user", "content": "lookup order ord-001"}],
        correlation_id="corr-01",
    )
    session = await adapter.start_session(ctx)

    inp = AgentInput(
        turn_index=1,
        user_messages=[{"role": "user", "content": "lookup order ord-001"}],
    )
    out = await adapter.send(session, inp)
    assert out.output_type == AgentOutputType.TOOL_CALLS
    assert len(out.tool_calls) == 1
    assert out.tool_calls[0].tool_name == "lookup_order"
    assert out.tool_calls[0].arguments == {"order_id": "ord-001"}
    assert out.total_tokens == 25


@pytest.mark.asyncio
async def test_openai_adapter_send_text_and_streaming() -> None:
    mock_resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "Your order has been located successfully.",
                }
            }
        ],
        "usage": {"prompt_tokens": 15, "completion_tokens": 20, "total_tokens": 35},
    }

    adapter = OpenAIAgentAdapter(endpoint_url="https://api.openai.com/v1", api_key="sk-test")
    client = httpx.AsyncClient(transport=MockTransport(mock_resp))
    adapter._client = client

    ctx = SessionContext(
        session_id="sess-02",
        trial_id="tr-02",
        run_id="run-02",
        agent_version_id="ag-02",
        available_tools=[],
        initial_messages=[],
        correlation_id="corr-02",
    )
    session = await adapter.start_session(ctx)

    # Tool results feedback turn
    inp = AgentInput(
        turn_index=2,
        tool_results=[{"tool_call_id": "call_123", "result": {"status": "shipped"}}],
    )
    out = await adapter.send(session, inp)
    assert out.output_type == AgentOutputType.TEXT
    assert "located" in (out.raw_text or "")

    # Test stream
    stream_chunks = [chunk async for chunk in adapter.stream(session, inp)]
    assert len(stream_chunks) == 1

    # Test interrupt
    intr = await adapter.interrupt(
        session,
        InterruptionResolution(
            interruption_type=InterruptionType.APPROVAL_REQUIRED,
            approved=True,
            resolved_by="user-01",
        ),
    )
    assert intr.raw_text == "Interrupted"

    await adapter.end_session(session)
