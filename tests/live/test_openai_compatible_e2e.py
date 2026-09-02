"""
Live opt-in End-to-End Evaluation test for OpenAI-compatible model endpoints.

Enable with:
    ARL_LIVE_E2E=1 pytest tests/live/test_openai_compatible_e2e.py -v
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI, Header
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from arl.adapters.openai.adapter import OpenAIAgentAdapter
from arl.core.domain.trial import Trial
from arl.environments.customer_support.environment import CustomerSupportEnvironment
from arl.execution_engine.executor import TrialExecutor
from arl.scenario_engine.loader import load_scenario


class ChatMessage(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[ChatMessage]
    tools: list[dict[str, Any]] = Field(default_factory=list)
    temperature: float = 0.0


mock_app = FastAPI()


@mock_app.post("/v1/chat/completions")
async def create_chat_completion(
    req: ChatCompletionRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    last_msg = req.messages[-1] if req.messages else None
    if last_msg and last_msg.role == "tool":
        return {
            "id": "chatcmpl-test-res",
            "object": "chat.completion",
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Order details retrieved successfully.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
            },
        }

    return {
        "id": "chatcmpl-test-call",
        "object": "chat.completion",
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_12345",
                            "type": "function",
                            "function": {
                                "name": "order.lookup",
                                "arguments": '{"customer_id": "customer-101"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {
            "prompt_tokens": 80,
            "completion_tokens": 25,
            "total_tokens": 105,
        },
    }


@pytest.mark.asyncio
async def test_openai_compatible_evaluation_with_mock_endpoint() -> None:
    """Always runnable contract test verifying OpenAIAgentAdapter against standard ChatCompletions."""
    transport = ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://testopenai") as client:
        adapter = OpenAIAgentAdapter(
            endpoint_url="http://testopenai/v1/chat/completions",
            api_key="test-key",
            model="gpt-4o-mini",
            allow_localhost=True,
            custom_client=client,
        )

        scenario_path = Path(
            "scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml"
        )
        scenario, _, _ = load_scenario(scenario_path)
        env = CustomerSupportEnvironment(seed=42)

        trial = Trial(
            id="trial-openai-e2e-01",
            run_id="run-openai-e2e",
            trial_index=0,
            idempotency_key="idemp-openai-01",
            fault_seed=42,
        )

        executor = TrialExecutor(
            trial=trial,
            scenario=scenario,
            adapter=adapter,
            environment=env,
        )

        result = await executor.run()

        assert result.completed_normally is True
        assert len(result.tool_calls) >= 1
        assert result.tool_calls[0].tool_name == "order.lookup"


@pytest.mark.asyncio
async def test_live_openai_endpoint_opt_in() -> None:
    """Opt-in test running against a real external OpenAI / Ollama / vLLM endpoint."""
    if not os.getenv("ARL_LIVE_E2E"):
        pytest.skip(
            "Opt-in live evaluation skipped (set ARL_LIVE_E2E=1 to enable against live API)"
        )

    api_key = os.getenv("ARL_OPENAI_API_KEY")
    base_url = os.getenv("ARL_OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("ARL_OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        pytest.skip("ARL_OPENAI_API_KEY required for live test")

    adapter = OpenAIAgentAdapter(
        endpoint_url=f"{base_url.rstrip('/')}/chat/completions",
        api_key=api_key,
        model=model,
        allow_localhost=True,
    )

    scenario_path = Path(
        "scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml"
    )
    scenario, _, _ = load_scenario(scenario_path)
    env = CustomerSupportEnvironment(seed=42)

    trial = Trial(
        id="trial-openai-live-real",
        run_id="run-openai-live",
        trial_index=0,
        idempotency_key="idemp-openai-live",
        fault_seed=42,
    )

    executor = TrialExecutor(
        trial=trial,
        scenario=scenario,
        adapter=adapter,
        environment=env,
    )

    result = await executor.run()

    assert result.completed_normally is True
