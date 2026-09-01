"""
Unit tests for TrialExecutor and budget enforcement.
"""

from __future__ import annotations

import textwrap

import pytest

from arl.adapters.reference.agent import MockAgentAdapter
from arl.core.domain.trial import Trial
from arl.environments.customer_support.environment import CustomerSupportEnvironment
from arl.execution_engine.executor import TrialExecutor
from arl.protocol.adapter import AgentOutput, AgentOutputType, ToolCallRecord
from arl.scenario_engine.loader import load_scenario_from_string

SCENARIO_YAML = textwrap.dedent("""\
    schema_version: "1.0"
    id: executor-test-scenario
    version: "1.0.0"
    title: Executor Test
    category: tool-correctness
    environment:
      name: customer-support
      version: "1.0.0"
      seed: 42
    conversation:
      - role: user
        content: Look up my orders.
    budgets:
      max_turns: 5
      max_tool_calls: 3
      max_duration_seconds: 10
      max_cost_usd: 0.10
""")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trial_executor_successful_run() -> None:
    scenario = load_scenario_from_string(SCENARIO_YAML)
    env = CustomerSupportEnvironment(seed=42)

    trial = Trial(
        id="trial-exec-01",
        run_id="run-01",
        trial_index=0,
        idempotency_key="idemp-01",
        fault_seed=42,
    )

    adapter = MockAgentAdapter.with_single_tool_call(
        tool_name="order.lookup",
        arguments={"customer_id": "customer-101"},
        completion_text="Found your orders.",
    )

    executor = TrialExecutor(
        trial=trial,
        scenario=scenario,
        adapter=adapter,
        environment=env,
    )

    result = await executor.run()

    assert result.completed_normally is True
    assert result.termination_reason == "completed"
    assert len(result.turns) == 2
    assert len(result.tool_calls) == 1
    assert len(result.tool_results) == 1
    assert result.pre_snapshot is not None
    assert result.post_snapshot is not None
    assert result.final_response == "Found your orders."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_trial_executor_turns_budget_exceeded() -> None:
    scenario = load_scenario_from_string(SCENARIO_YAML)  # max_turns: 5
    env = CustomerSupportEnvironment(seed=42)

    trial = Trial(
        id="trial-exec-02",
        run_id="run-01",
        trial_index=0,
        idempotency_key="idemp-02",
        fault_seed=42,
    )

    # Infinite tool calling adapter
    plan = [
        AgentOutput(
            output_type=AgentOutputType.TOOL_CALLS,
            turn_index=i,
            tool_calls=[ToolCallRecord(tool_call_id=f"tc-{i}", tool_name="loyalty.get_points", arguments={})],
        )
        for i in range(10)
    ]
    adapter = MockAgentAdapter(turn_plan=plan)

    executor = TrialExecutor(trial=trial, scenario=scenario, adapter=adapter, environment=env)
    result = await executor.run()

    assert result.completed_normally is False
    assert "budget_exceeded" in result.termination_reason
