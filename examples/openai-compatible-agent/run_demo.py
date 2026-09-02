"""
Automated evaluation runner for OpenAI-compatible model endpoints.

Demonstrates evaluating an OpenAI-compatible endpoint with ARL's OpenAIAgentAdapter.
If ARL_OPENAI_API_KEY is not set, starts the local OpenAI-compatible mock server
on port 8089 to execute an offline trial demonstrating the complete protocol flow.
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
import time
from pathlib import Path

import uvicorn

from arl.adapters.openai.adapter import OpenAIAgentAdapter
from arl.core.domain.trial import Trial
from arl.environments.customer_support.environment import (
    CustomerSupportEnvironment,
)
from arl.execution_engine.executor import TrialExecutor
from arl.scenario_engine.loader import load_scenario

if hasattr(sys.stdout, "reconfigure"):
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")


def run_local_openai_mock() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "server",
        Path(__file__).parent / "server.py",
    )
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        uvicorn.run(mod.app, host="127.0.0.1", port=8089, log_level="error")


async def evaluate_openai_endpoint(base_url: str, api_key: str, model: str) -> None:
    print(f"\nTarget Endpoint: {base_url}")
    print(f"Model: {model}")

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
        id="demo-trial-openai",
        run_id="demo-run-openai",
        trial_index=0,
        idempotency_key="demo-idemp-openai",
        fault_seed=42,
    )

    executor = TrialExecutor(
        trial=trial,
        scenario=scenario,
        adapter=adapter,
        environment=env,
    )

    print("Running multi-turn trial evaluation against target model endpoint...")
    result = await executor.run()

    print("\n" + "=" * 70)
    print("TRIAL EXECUTION RESULT")
    print("=" * 70)
    print(f"Termination Reason: {result.termination_reason}")
    print(f"Completed Normally: {result.completed_normally}")
    print(f"Total Turns: {len(result.turns)}")
    print(f"Tool Calls: {len(result.tool_calls)}")
    for tc in result.tool_calls:
        print(f"  -> Tool: {tc.tool_name}, Arguments: {tc.arguments}")
    print(f"Final Response: {result.final_response}")
    print("=" * 70)


def main() -> None:
    import asyncio

    print("=" * 70)
    print("ARL OpenAI-Compatible Model Evaluation Demo")
    print("=" * 70)

    api_key = os.getenv("ARL_OPENAI_API_KEY")
    base_url = os.getenv("ARL_OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("ARL_OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        print("\nNo ARL_OPENAI_API_KEY detected in environment.")
        print(
            "Starting local OpenAI-compatible mock server on port 8089 for offline demonstration..."
        )
        server_thread = threading.Thread(target=run_local_openai_mock, daemon=True)
        server_thread.start()
        time.sleep(1.5)

        base_url = "http://127.0.0.1:8089/v1"
        api_key = "mock-key"
        model = "gpt-4o-mini"

    asyncio.run(evaluate_openai_endpoint(base_url, api_key, model))


if __name__ == "__main__":
    main()
