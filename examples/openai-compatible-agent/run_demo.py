"""
Live evaluation runner for OpenAI-compatible model endpoints.

Evaluates an OpenAI-compatible endpoint (OpenAI, Ollama, vLLM, LM Studio, Groq)
using ARL's OpenAIAgentAdapter across stateful evaluation scenarios.
"""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

import httpx

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


async def evaluate_openai_endpoint(base_url: str, api_key: str, model: str) -> None:
    print(f"\nTarget Endpoint: {base_url}")
    print(f"Target Model:    {model}")

    # If targeting local Ollama / vLLM on localhost, ensure environment flags are enabled
    if "localhost" in base_url or "127.0.0.1" in base_url:
        os.environ["ARL_ENVIRONMENT"] = "development"
        os.environ["ARL_ALLOW_LOCALHOST_TARGETS"] = "true"

    adapter = OpenAIAgentAdapter(
        endpoint_url=f"{base_url.rstrip('/')}/chat/completions",
        api_key=api_key,
        model=model,
    )

    scenario_path = Path("scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml")
    if not scenario_path.exists():
        print(f"Error: Scenario file not found at {scenario_path}")
        sys.exit(1)

    scenario, _, _ = load_scenario(scenario_path)
    env = CustomerSupportEnvironment(seed=42)

    trial = Trial(
        id="live-demo-trial-openai",
        run_id="live-demo-run-openai",
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

    print("\nRunning multi-turn evaluation trial against target model endpoint...")
    result = await executor.run()

    print("\n" + "=" * 70)
    print("LIVE TRIAL EXECUTION RESULT")
    print("=" * 70)
    print(f"Termination Reason: {result.termination_reason}")
    print(f"Completed Normally: {result.completed_normally}")
    print(f"Total Turns:        {len(result.turns)}")
    print(f"Tool Calls Made:    {len(result.tool_calls)}")
    for tc in result.tool_calls:
        print(f"  -> Tool: {tc.tool_name}, Arguments: {tc.arguments}")
    print(f"Final Response:     {result.final_response}")
    print("=" * 70)


def check_local_ollama() -> bool:
    """Check if a local Ollama instance is actively running on port 11434."""
    try:
        resp = httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.0)
        return resp.status_code == 200
    except Exception:
        return False


def main() -> None:
    import asyncio

    print("=" * 70)
    print("Agent Reliability Lab — Real Model Evaluation Demo")
    print("=" * 70)

    api_key = os.getenv("ARL_OPENAI_API_KEY")
    base_url = os.getenv("ARL_OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("ARL_OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        # Check if local Ollama is available
        if check_local_ollama():
            print("\n[+] Detected local Ollama service running on http://127.0.0.1:11434")
            base_url = "http://127.0.0.1:11434/v1"
            api_key = "ollama"
            model = os.getenv("ARL_OPENAI_MODEL", "llama3.1")
        else:
            print("\n[!] No live model credentials or local Ollama endpoint detected.")
            print("\nTo evaluate a real model, choose one of the following options:")
            print("\nOption 1: Evaluate using OpenAI API")
            print('  export ARL_OPENAI_API_KEY="sk-..."')
            print('  export ARL_OPENAI_MODEL="gpt-4o-mini"')
            print("  python examples/openai-compatible-agent/run_demo.py")
            print("\nOption 2: Evaluate using local Ollama")
            print("  ollama run llama3.1")
            print("  python examples/openai-compatible-agent/run_demo.py")
            print("\nOption 3: Run the local deterministic reference agent (offline test):")
            print("  python examples/deterministic-http-reference-agent/run_demo.py")
            print("=" * 70)
            sys.exit(1)

    asyncio.run(evaluate_openai_endpoint(base_url, api_key, model))


if __name__ == "__main__":
    main()
