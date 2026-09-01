"""
Unit tests for HttpAgentAdapter using httpx mock transport.
"""

from __future__ import annotations

import httpx
import pytest

from arl.adapters.http.adapter import HttpAgentAdapter
from arl.protocol.adapter import (
    AgentInput,
    AgentOutputType,
    InterruptionResolution,
    InterruptionType,
    SessionContext,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_adapter_turn_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/sessions":
            return httpx.Response(200, json={"adapter_state": {"thread_id": "th-123"}})
        if request.url.path == "/turn":
            return httpx.Response(
                200,
                json={
                    "type": "tool_calls",
                    "tool_calls": [
                        {"id": "tc-1", "name": "order.lookup", "arguments": {"customer_id": "c1"}}
                    ],
                    "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost_usd": 0.002},
                    "model": "gpt-4o",
                },
            )
        return httpx.Response(404)

    adapter = HttpAgentAdapter(endpoint_url="http://localhost:8080", allow_localhost=True)
    # Inject mock client
    adapter._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    context = SessionContext(
        session_id="s-http-1",
        trial_id="t-http-1",
        run_id="r-http-1",
        agent_version_id="av-http-1",
        available_tools=[],
        initial_messages=[{"role": "user", "content": "hello"}],
        correlation_id="corr-http",
    )

    session = await adapter.start_session(context)
    assert session.adapter_state["thread_id"] == "th-123"

    output = await adapter.send(session, AgentInput(turn_index=0))
    assert output.output_type == AgentOutputType.TOOL_CALLS
    assert len(output.tool_calls) == 1
    assert output.tool_calls[0].tool_name == "order.lookup"
    assert output.prompt_tokens == 100
    assert output.completion_tokens == 50
    assert output.cost_usd == 0.002
    assert output.model_name == "gpt-4o"

    await adapter.close_session(session)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_adapter_error_handling() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/turn":
            return httpx.Response(500, json={"error": "Model overloaded"})
        return httpx.Response(200, json={})

    adapter = HttpAgentAdapter(endpoint_url="http://localhost:8080", allow_localhost=True)
    adapter._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    context = SessionContext(
        session_id="s-http-2",
        trial_id="t-http-2",
        run_id="r-http-2",
        agent_version_id="av-http-2",
        available_tools=[],
        initial_messages=[{"role": "user", "content": "hi"}],
        correlation_id="corr-err",
    )
    session = await adapter.start_session(context)

    output = await adapter.send(session, AgentInput(turn_index=0))
    assert output.output_type == AgentOutputType.ERROR
    assert output.error_code == "HTTP_500"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_adapter_resume_and_cancel() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/resume":
            return httpx.Response(200, json={"text": "Approved action executed."})
        return httpx.Response(200, json={})

    adapter = HttpAgentAdapter(endpoint_url="http://localhost:8080", allow_localhost=True)
    adapter._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    session = await adapter.start_session(
        SessionContext(
            session_id="s-http-3",
            trial_id="t-http-3",
            run_id="r-http-3",
            agent_version_id="av-http-3",
            available_tools=[],
            initial_messages=[{"role": "user", "content": "hi"}],
            correlation_id="corr-resume",
        )
    )

    out = await adapter.resume(
        session,
        InterruptionResolution(
            interruption_type=InterruptionType.APPROVAL_REQUIRED,
            approved=True,
            resolved_by="admin",
        ),
    )
    assert out.output_type == AgentOutputType.FINISHED
    assert out.raw_text == "Approved action executed."

    await adapter.cancel(session)
    await adapter.close_session(session)
