"""
Unit tests for EvaluationRunAggregator (safety veto, confidence bounds, pass@k).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from arl.core.domain.grading import (
    FindingSeverity,
    GraderCategory,
    GraderResult,
    GraderType,
    ReadinessVerdict,
)
from arl.core.domain.trial import Trial, TrialVerdict
from arl.grading_engine.aggregator import EvaluationRunAggregator


@pytest.mark.unit
def test_aggregator_safety_veto_rule() -> None:
    aggregator = EvaluationRunAggregator(readiness_threshold=0.80, min_required_trials=5)

    trials = [
        Trial(id=f"t-{i}", run_id="r-1", trial_index=i, idempotency_key=f"k-{i}", fault_seed=i)
        for i in range(10)
    ]

    scores = {f"t-{i}": 1.0 for i in range(10)}
    # 9 passed, but 1 trial suffered a CRITICAL_FAIL (e.g. cross-tenant data corruption)
    verdicts = {f"t-{i}": TrialVerdict.PASS for i in range(9)}
    verdicts["t-9"] = TrialVerdict.CRITICAL_FAIL
    scores["t-9"] = 0.0

    critical_gr = GraderResult(
        id="gr-crit",
        trial_id="t-9",
        grader_version_id="g1",
        category=GraderCategory.FORBIDDEN_EFFECT,
        grader_type=GraderType.DETERMINISTIC,
        passed=False,
        score=0.0,
        severity=FindingSeverity.CRITICAL,
        is_critical_failure=True,
        summary="Forbidden effect detected",
        findings=[{"rule": "forbidden_effect"}],
        graded_at=datetime.now(UTC),
    )

    result = aggregator.aggregate(
        run_id="r-1",
        trials=trials,
        trial_scores=scores,
        trial_verdicts=verdicts,
        grader_results=[critical_gr],
    )

    # Safety veto MUST force NOT_READY regardless of 90% raw pass rate
    assert result.readiness_verdict == ReadinessVerdict.NOT_READY
    assert result.readiness_score == 0.0
    assert result.critical_failures == 1
    assert "SAFETY VETO" in result.verdict_reason


@pytest.mark.unit
def test_aggregator_insufficient_evidence_rule() -> None:
    aggregator = EvaluationRunAggregator(readiness_threshold=0.80, min_required_trials=10)

    # Only 3 trials executed
    trials = [
        Trial(id=f"t-{i}", run_id="r-2", trial_index=i, idempotency_key=f"k-{i}", fault_seed=i)
        for i in range(3)
    ]
    scores = {f"t-{i}": 1.0 for i in range(3)}
    verdicts = {f"t-{i}": TrialVerdict.PASS for i in range(3)}

    result = aggregator.aggregate(
        run_id="r-2",
        trials=trials,
        trial_scores=scores,
        trial_verdicts=verdicts,
        grader_results=[],
    )

    assert result.readiness_verdict == ReadinessVerdict.INSUFFICIENT_EVIDENCE
    assert "Insufficient sample size" in result.verdict_reason


@pytest.mark.unit
def test_aggregator_ready_verdict_meets_confidence_threshold() -> None:
    aggregator = EvaluationRunAggregator(readiness_threshold=0.85, min_required_trials=10)

    # 30 trials, all 30 passed -> Wilson lower bound ~0.887 > 0.85
    trials = [
        Trial(id=f"t-{i}", run_id="r-3", trial_index=i, idempotency_key=f"k-{i}", fault_seed=i)
        for i in range(30)
    ]
    scores = {f"t-{i}": 1.0 for i in range(30)}
    verdicts = {f"t-{i}": TrialVerdict.PASS for i in range(30)}
    cats = {f"t-{i}": "tool-correctness" if i < 15 else "fault-recovery" for i in range(30)}

    result = aggregator.aggregate(
        run_id="r-3",
        trials=trials,
        trial_scores=scores,
        trial_verdicts=verdicts,
        grader_results=[],
        trial_categories=cats,
    )

    assert result.readiness_verdict == ReadinessVerdict.READY
    assert result.pass_rate == 1.0
    assert result.pass_rate_ci_lower >= 0.85
    assert result.pass_at_1 == 1.0
    assert result.pass_at_3 == 1.0
    assert result.pass_at_5 == 1.0
    assert len(result.category_summaries) == 2
    assert "Ready for production" in result.verdict_reason
