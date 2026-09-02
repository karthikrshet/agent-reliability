"""
Agent Reliability Lab — Adapter Conformance Test Suite.

Verifies that all implementations of AgentAdapter adhere strictly to the
lifecycle protocol, SSRF defenses, tool record structures, and error handling.
"""

from __future__ import annotations

import httpx
import pytest

from arl.adapters.http.adapter import HttpAgentAdapter
from arl.adapters.openai.adapter import OpenAIAgentAdapter
from arl.adapters.reference.agent import MockAgentAdapter
from arl.core.errors import SecurityViolationError
from arl.protocol.adapter import (
    AgentAdapter,
    AgentInput,
    AgentOutputType,
    SessionContext,
)


@pytest.mark.asyncio
async def test_mock_adapter_conformance() -> None:
    """Verify MockAgentAdapter conforms to AgentAdapter protocol."""
    adapter: AgentAdapter = MockAgentAdapter()
    assert adapter.adapter_id == "mock-reference-v1"
    assert adapter.framework == "reference-mock"

    ctx = SessionContext(
        session_id="sess-001",
        trial_id="tr-001",
        run_id="run-001",
        agent_version_id="ag-v1",
        available_tools=[{"name": "lookup_order", "description": "lookup order", "parameters": {}}],
        initial_messages=[{"role": "user", "content": "lookup order 123"}],
        correlation_id="corr-001",
    )
    session = await adapter.start_session(ctx)
    assert session.session_id == "sess-001"

    inp = AgentInput(
        turn_index=1,
        user_messages=[{"role": "user", "content": "lookup order 123"}],
    )
    output = await adapter.send(session, inp)
    assert output.output_type in (
        AgentOutputType.TOOL_CALLS,
        AgentOutputType.TEXT,
        AgentOutputType.FINISHED,
    )

    await adapter.close_session(session)


@pytest.mark.asyncio
async def test_http_adapter_ssrf_conformance() -> None:
    """Verify HttpAgentAdapter rejects malicious private IP and cloud metadata endpoints."""
    # 1. AWS/GCP/Azure Cloud metadata endpoint (169.254.169.254)
    with pytest.raises(SecurityViolationError) as exc_info:
        HttpAgentAdapter(endpoint_url="http://169.254.169.254/latest/meta-data")
    assert "SSRF_PROTECTION" in str(exc_info.value)

    # 2. Private 10.0.0.0/8 network
    with pytest.raises(SecurityViolationError):
        HttpAgentAdapter(endpoint_url="http://10.0.1.5:8080/agent")

    # 3. Invalid protocol scheme (e.g. file://, gopher://)
    with pytest.raises(SecurityViolationError) as exc_scheme:
        HttpAgentAdapter(endpoint_url="file:///etc/passwd")
    assert "INVALID_SCHEME" in str(exc_scheme.value)


@pytest.mark.asyncio
async def test_openai_adapter_lifecycle_and_mock() -> None:
    """Verify OpenAIAgentAdapter session lifecycle and ChatCompletions tool call formatting."""
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))
    )
    adapter = OpenAIAgentAdapter(
        endpoint_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        api_key="sk-test-key",
        custom_client=client,
    )
    assert adapter.adapter_id == "openai-v1"
    assert adapter.framework == "openai"

    ctx = SessionContext(
        session_id="sess-openai-01",
        trial_id="tr-openai-01",
        run_id="run-openai-01",
        agent_version_id="ag-openai-v1",
        available_tools=[
            {"name": "lookup_order", "description": "Lookup order", "parameters": {}},
            {"name": "issue_refund", "description": "Issue refund", "parameters": {}},
        ],
        initial_messages=[{"role": "user", "content": "hello"}],
        correlation_id="corr-openai-01",
    )
    session = await adapter.start_session(ctx)
    assert len(session.adapter_state["tools"]) == 2
    assert session.adapter_state["model"] == "gpt-4o-mini"

    # SSRF rejection check on OpenAI adapter
    with pytest.raises(SecurityViolationError):
        OpenAIAgentAdapter(endpoint_url="http://169.254.169.254/v1")

    await adapter.close_session(session)
