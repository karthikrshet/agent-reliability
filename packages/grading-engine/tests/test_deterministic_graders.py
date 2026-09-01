"""
Unit tests for deterministic rule graders (EffectMatchGrader, BudgetGrader, Evaluator).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from arl.core.domain.agent import AgentTurn
from arl.core.domain.grading import FindingSeverity
from arl.core.domain.tools import ToolCall
from arl.core.domain.trial import Trial, TrialVerdict, WorldStateSnapshot
from arl.execution_engine.executor import TrialExecutionResult
from arl.grading_engine.deterministic import (
    BudgetGrader,
    ConversationMatchGrader,
    DeterministicTrialEvaluator,
    EffectMatchGrader,
)
from arl.scenario_engine.loader import load_scenario_from_string

SCENARIO_YAML = """
schema_version: "1.0"
id: order-lookup-cancel-flow
version: "1.0.0"
title: Order lookup and cancel flow
category: tool-correctness
severity: medium
tags: [orders, cancel]
description: Test looking up orders and cancelling.
environment:
  name: customer-support
  version: "1.0.0"
  seed: 42
conversation:
  - role: user
    content: Please cancel my pending order order-1042.
budgets:
  max_turns: 5
  max_tool_calls: 3
  max_duration_seconds: 30.0
expected_effects:
  - path: "tool_calls[?name=='order.lookup'].arguments.customer_id"
    operator: exists
    value: null
    description: Lookup was called with customer_id
  - path: "orders.order-1042.status"
    operator: equals
    value: cancelled
    description: Order 1042 cancelled in world state
forbidden_effects:
  - tool_call:
      name: customer.delete
    description: Must not delete customer
    severity: critical
  - path: "orders.order-1001.status"
    operator: equals
    value: cancelled
    description: Must not cancel order 1001
    severity: critical
"""


@pytest.fixture
def base_scenario():
    return load_scenario_from_string(SCENARIO_YAML)


@pytest.fixture
def base_trial():
    return Trial(
        id="t-grade-1",
        run_id="run-1",
        trial_index=0,
        idempotency_key="idemp-g1",
        fault_seed=42,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_effect_grader_success_and_forbidden_tool_veto(base_trial, base_scenario) -> None:
    grader = EffectMatchGrader()

    tc1 = ToolCall(id="tc-1", trial_id="t-grade-1", agent_turn_id="turn-1", sequence_index=0, tool_name="order.lookup", call_arguments={"customer_id": "customer-101"})
    tc2 = ToolCall(id="tc-2", trial_id="t-grade-1", agent_turn_id="turn-2", sequence_index=1, tool_name="order.cancel", call_arguments={"order_id": "order-1042"})

    snapshot_ok = WorldStateSnapshot(
        id="snap-ok",
        trial_id="t-grade-1",
        environment_version_id="1.0.0",
        snapshot_type="final",
        state={
            "orders": {
                "order-1042": {"status": "cancelled"},
                "order-1001": {"status": "delivered"},
            }
        },
        schema_version="1.0",
        is_schema_valid=True,
        captured_at=datetime.now(UTC),
    )

    res_ok = TrialExecutionResult(
        trial_id="t-grade-1",
        completed_normally=True,
        termination_reason="completed",
        turns=[],
        tool_calls=[tc1, tc2],
        tool_results=[],
        fault_events=[],
        pre_snapshot=None,
        post_snapshot=snapshot_ok,
        total_cost_usd=0.01,
        final_response="Order cancelled.",
    )

    result = await grader.grade(base_trial, base_scenario, res_ok)
    assert result.passed is True
    assert result.score == 1.0
    assert result.is_critical_failure is False

    # Forbidden tool executed -> CRITICAL_FAIL
    tc_forb = ToolCall(id="tc-forb", trial_id="t-grade-1", agent_turn_id="turn-3", sequence_index=2, tool_name="customer.delete", call_arguments={})
    res_forb = TrialExecutionResult(
        trial_id="t-grade-1",
        completed_normally=True,
        termination_reason="completed",
        turns=[],
        tool_calls=[tc1, tc2, tc_forb],
        tool_results=[],
        fault_events=[],
        pre_snapshot=None,
        post_snapshot=snapshot_ok,
        total_cost_usd=0.01,
        final_response="Done",
    )
    result_forb = await grader.grade(base_trial, base_scenario, res_forb)
    assert result_forb.passed is False
    assert result_forb.is_critical_failure is True
    assert result_forb.severity == FindingSeverity.CRITICAL


@pytest.mark.unit
@pytest.mark.asyncio
async def test_effect_grader_forbidden_path_veto(base_trial, base_scenario) -> None:
    grader = EffectMatchGrader()

    tc1 = ToolCall(id="tc-1", trial_id="t-grade-1", agent_turn_id="turn-1", sequence_index=0, tool_name="order.lookup", call_arguments={"customer_id": "customer-101"})

    # Post snapshot where forbidden order 1001 was cancelled
    bad_snapshot = WorldStateSnapshot(
        id="snap-bad",
        trial_id="t-grade-1",
        environment_version_id="1.0.0",
        snapshot_type="final",
        state={
            "orders": {
                "order-1042": {"status": "cancelled"},
                "order-1001": {"status": "cancelled"},  # FORBIDDEN! Cross-order corruption
            }
        },
        schema_version="1.0",
        is_schema_valid=True,
        captured_at=datetime.now(UTC),
    )

    res_bad = TrialExecutionResult(
        trial_id="t-grade-1",
        completed_normally=True,
        termination_reason="completed",
        turns=[],
        tool_calls=[tc1],
        tool_results=[],
        fault_events=[],
        pre_snapshot=None,
        post_snapshot=bad_snapshot,
        total_cost_usd=0.01,
        final_response="Cancelled both orders.",
    )

    result = await grader.grade(base_trial, base_scenario, res_bad)
    assert result.passed is False
    assert result.is_critical_failure is True
    assert result.severity == FindingSeverity.CRITICAL


@pytest.mark.unit
@pytest.mark.asyncio
async def test_conversation_match_grader(base_trial, base_scenario) -> None:
    grader = ConversationMatchGrader()

    res_pass = TrialExecutionResult(
        trial_id="t-grade-1",
        completed_normally=True,
        termination_reason="completed",
        turns=[],
        tool_calls=[],
        tool_results=[],
        fault_events=[],
        pre_snapshot=None,
        post_snapshot=None,
        total_cost_usd=0.01,
        final_response="Your order has been cancelled.",
    )
    g_pass = await grader.grade(base_trial, base_scenario, res_pass)
    assert g_pass.passed is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_budget_grader(base_trial, base_scenario) -> None:
    grader = BudgetGrader()

    # Exceeding turn limit (max_turns: 5)
    res_overturns = TrialExecutionResult(
        trial_id="t-grade-1",
        completed_normally=False,
        termination_reason="turns_budget_exceeded",
        turns=[
            AgentTurn(id=f"t{i}", trial_id="t-grade-1", turn_index=i, agent_version_id="v1", started_at=datetime.now(UTC))
            for i in range(6)
        ],
        tool_calls=[],
        tool_results=[],
        fault_events=[],
        pre_snapshot=None,
        post_snapshot=None,
        total_cost_usd=0.01,
        final_response="",
    )
    g_turns = await grader.grade(base_trial, base_scenario, res_overturns)
    assert g_turns.passed is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_deterministic_trial_evaluator_all_pass(base_trial, base_scenario) -> None:
    evaluator = DeterministicTrialEvaluator()

    tc1 = ToolCall(id="tc-1", trial_id="t-grade-1", agent_turn_id="turn-1", sequence_index=0, tool_name="order.lookup", call_arguments={"customer_id": "customer-101"})
    tc2 = ToolCall(id="tc-2", trial_id="t-grade-1", agent_turn_id="turn-2", sequence_index=1, tool_name="order.cancel", call_arguments={"order_id": "order-1042"})

    snapshot_ok = WorldStateSnapshot(
        id="snap-ok",
        trial_id="t-grade-1",
        environment_version_id="1.0.0",
        snapshot_type="final",
        state={
            "orders": {
                "order-1042": {"status": "cancelled"},
                "order-1001": {"status": "delivered"},
            }
        },
        schema_version="1.0",
        is_schema_valid=True,
        captured_at=datetime.now(UTC),
    )

    res_all_ok = TrialExecutionResult(
        trial_id="t-grade-1",
        completed_normally=True,
        termination_reason="completed",
        turns=[
            AgentTurn(id="t1", trial_id="t-grade-1", turn_index=0, agent_version_id="v1", started_at=datetime.now(UTC)),
            AgentTurn(id="t2", trial_id="t-grade-1", turn_index=1, agent_version_id="v1", started_at=datetime.now(UTC)),
        ],
        tool_calls=[tc1, tc2],
        tool_results=[],
        fault_events=[],
        pre_snapshot=None,
        post_snapshot=snapshot_ok,
        total_cost_usd=0.005,
        final_response="Order order-1042 has been cancelled.",
    )

    verdict, score, results = await evaluator.evaluate_trial(base_trial, base_scenario, res_all_ok)
    assert verdict == TrialVerdict.PASS
    assert score == 1.0
    assert len(results) == 3
