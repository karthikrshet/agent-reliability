"""
Agent Reliability Lab — Base Grader Protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from arl.core.domain.grading import GraderCategory, GraderResult, GraderType
from arl.core.domain.trial import Trial
from arl.execution_engine.executor import TrialExecutionResult
from arl.scenario_engine.schema import ParsedScenario


@runtime_checkable
class BaseGrader(Protocol):
    """Protocol defining a trial grader."""

    @property
    def name(self) -> str:
        """Human-readable grader name."""
        ...

    @property
    def category(self) -> GraderCategory:
        """Category of this grader."""
        ...

    @property
    def grader_type(self) -> GraderType:
        """Whether this grader is deterministic, statistical, or model-based."""
        ...

    @property
    def is_blocking(self) -> bool:
        """If true, failure of this grader blocks the trial and triggers critical failure."""
        ...

    async def grade(
        self,
        trial: Trial,
        scenario: ParsedScenario,
        result: TrialExecutionResult,
    ) -> GraderResult:
        """Grade a completed or terminated trial execution result."""
        ...
