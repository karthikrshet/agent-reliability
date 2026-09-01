"""
Unit tests for LLMJudge semantic evaluation.
"""

from __future__ import annotations

import pytest

from arl.core.domain.trial import Trial
from arl.execution_engine.executor import TrialExecutionResult
from arl.grading_engine.semantic import JudgeEvaluation, LLMJudge
from arl.scenario_engine.loader import load_scenario_from_string

SCENARIO_YAML = """
schema_version: "1.0"
id: support-flow
version: "1.0.0"
title: Support flow
category: tool-correctness
severity: low
environment:
  name: customer-support
  version: "1.0.0"
  seed: 42
conversation:
  - role: user
    content: Help me
budgets:
  max_turns: 5
  max_tool_calls: 3
  max_duration_seconds: 30.0
"""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_llm_judge_default_heuristic() -> None:
    scenario = load_scenario_from_string(SCENARIO_YAML)
    trial = Trial(id="t1", run_id="r1", trial_index=0, idempotency_key="k1", fault_seed=42)

    judge = LLMJudge()

    # Good response
    res_good = TrialExecutionResult(
        trial_id="t1",
        completed_normally=True,
        termination_reason="completed",
        turns=[],
        tool_calls=[],
        tool_results=[],
        fault_events=[],
        pre_snapshot=None,
        post_snapshot=None,
        final_response="Thank you for reaching out! I am very glad to help you today.",
    )
    g_good = await judge.grade(trial, scenario, res_good)
    assert g_good.passed is True
    assert g_good.score is not None and g_good.score >= 0.8
    assert g_good.judge_reason is not None

    # Empty response
    res_empty = TrialExecutionResult(
        trial_id="t1",
        completed_normally=True,
        termination_reason="completed",
        turns=[],
        tool_calls=[],
        tool_results=[],
        fault_events=[],
        pre_snapshot=None,
        post_snapshot=None,
        final_response="",
    )
    g_empty = await judge.grade(trial, scenario, res_empty)
    assert g_empty.passed is False
    assert g_empty.score == 0.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_llm_judge_custom_evaluator() -> None:
    scenario = load_scenario_from_string(SCENARIO_YAML)
    trial = Trial(id="t2", run_id="r1", trial_index=1, idempotency_key="k2", fault_seed=42)

    def custom_eval(response: str, criteria: str) -> JudgeEvaluation:
        return JudgeEvaluation(
            passed=True,
            score=0.95,
            confidence=0.99,
            reasoning="Passed custom compliance rubric.",
            rubric_scores={"clarity": 1.0, "tone": 0.9},
        )

    judge = LLMJudge(custom_evaluator=custom_eval)
    res = TrialExecutionResult(
        trial_id="t2",
        completed_normally=True,
        termination_reason="completed",
        turns=[],
        tool_calls=[],
        tool_results=[],
        fault_events=[],
        pre_snapshot=None,
        post_snapshot=None,
        final_response="Any response",
    )
    g_res = await judge.grade(trial, scenario, res)
    assert g_res.passed is True
    assert g_res.score == 0.95
    assert "Passed custom compliance rubric." in (g_res.judge_reason or "")
