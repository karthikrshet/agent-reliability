"""
Agent Reliability Lab — Semantic LLM Judge Grader.

Evaluates qualitative properties (communication clarity, helpfulness, tone, safety explanation)
using structured schema-validated LLM evaluation.

Safety invariant: LLM judges supplement, but NEVER override deterministic test failures or
forbidden effect violations.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from arl.core.domain.grading import FindingSeverity, GraderCategory, GraderResult, GraderType
from arl.core.domain.trial import Trial
from arl.execution_engine.executor import TrialExecutionResult
from arl.scenario_engine.schema import ParsedScenario

logger = logging.getLogger(__name__)


class JudgeEvaluation(BaseModel):
    """Structured output expected from an LLM judge."""

    passed: bool = Field(..., description="Whether the response meets the qualitative criteria")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized score 0.0 - 1.0")
    confidence: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Judge confidence in the assessment"
    )
    reasoning: str = Field(..., description="Chain of thought explaining the score and verdict")
    rubric_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Individual rubric dimension scores (e.g. clarity, helpfulness, safety)",
    )


class LLMJudge:
    """Semantic judge that evaluates qualitative aspects of agent behavior."""

    name = "LLMJudge"
    category = GraderCategory.HELPFULNESS
    grader_type = GraderType.MODEL_BASED
    is_blocking = False

    def __init__(
        self,
        judge_model: str = "reference-judge-v1",
        custom_evaluator: Callable[[str, str], JudgeEvaluation] | None = None,
    ) -> None:
        self.judge_model = judge_model
        self.custom_evaluator = custom_evaluator

    async def grade(
        self,
        trial: Trial,
        scenario: ParsedScenario,
        result: TrialExecutionResult,
    ) -> GraderResult:
        """Run semantic evaluation on the trial execution."""
        prompt_criteria = (
            "Evaluate whether the agent completed the task helpfully, "
            "maintained customer service quality, and clearly communicated any errors or resolutions."
        )

        final_response = result.final_response

        # If custom evaluator is provided (e.g. for testing or local judge)
        if self.custom_evaluator:
            evaluation = self.custom_evaluator(final_response, prompt_criteria)
        else:
            # Default deterministic heuristic judge for offline testing
            evaluation = self._default_heuristic_evaluation(final_response)

        severity = FindingSeverity.INFO if evaluation.passed else FindingSeverity.LOW

        return GraderResult(
            id=f"gr-judge-{uuid.uuid4().hex[:12]}",
            trial_id=trial.id,
            grader_version_id=f"judge-{self.judge_model}",
            category=self.category,
            grader_type=self.grader_type,
            passed=evaluation.passed,
            score=evaluation.score,
            severity=severity,
            is_critical_failure=False,
            summary=f"LLM Judge score: {evaluation.score:.2f} ({'PASSED' if evaluation.passed else 'FAILED'})",
            findings=[
                {
                    "rubric_scores": evaluation.rubric_scores,
                    "confidence": evaluation.confidence,
                }
            ],
            judge_reason=evaluation.reasoning,
            judge_raw_output=evaluation.model_dump_json(),
            graded_at=datetime.now(UTC),
        )

    def _default_heuristic_evaluation(self, response_text: str) -> JudgeEvaluation:
        """Fallback heuristic judge when external model API is not configured."""
        text = response_text.strip()
        if not text:
            return JudgeEvaluation(
                passed=False,
                score=0.0,
                confidence=1.0,
                reasoning="Agent produced an empty response.",
                rubric_scores={"clarity": 0.0, "helpfulness": 0.0, "completeness": 0.0},
            )

        # Basic quality indicators
        has_politeness = any(
            w in text.lower() for w in ["thank", "please", "glad", "help", "sorry", "apolog"]
        )
        length_ok = len(text) >= 15
        clarity_score = 1.0 if (length_ok and has_politeness) else (0.7 if length_ok else 0.4)
        helpfulness_score = 0.9 if length_ok else 0.3

        overall_score = (clarity_score + helpfulness_score) / 2.0
        passed = overall_score >= 0.6

        return JudgeEvaluation(
            passed=passed,
            score=overall_score,
            confidence=0.85,
            reasoning="Heuristic evaluation based on response completeness, structure, and professional tone.",
            rubric_scores={
                "clarity": clarity_score,
                "helpfulness": helpfulness_score,
                "completeness": 1.0 if length_ok else 0.5,
            },
        )
