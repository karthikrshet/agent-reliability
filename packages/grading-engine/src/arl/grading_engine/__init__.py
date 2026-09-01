"""
Agent Reliability Lab — Grading Engine Package.
"""

from __future__ import annotations

from arl.grading_engine.aggregator import (
    CategorySummary,
    EvaluationRunAggregator,
    RunAggregationResult,
)
from arl.grading_engine.base import BaseGrader
from arl.grading_engine.deterministic import (
    BudgetGrader,
    ConversationMatchGrader,
    DeterministicTrialEvaluator,
    EffectMatchGrader,
)
from arl.grading_engine.semantic import JudgeEvaluation, LLMJudge
from arl.grading_engine.stats import (
    compute_mean_and_ci,
    compute_pass_at_k,
    compute_wilson_score_interval,
)

__all__ = [
    "BaseGrader",
    "BudgetGrader",
    "CategorySummary",
    "ConversationMatchGrader",
    "DeterministicTrialEvaluator",
    "EffectMatchGrader",
    "EvaluationRunAggregator",
    "JudgeEvaluation",
    "LLMJudge",
    "RunAggregationResult",
    "compute_mean_and_ci",
    "compute_pass_at_k",
    "compute_wilson_score_interval",
]
