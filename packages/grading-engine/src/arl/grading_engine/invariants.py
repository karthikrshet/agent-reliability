"""
Agent Reliability Lab — Deterministic Invariant Engine.

Evaluates deterministic rules and invariants against world state, execution
transcripts, and tool calls using structured operators and safe path access.

Security Invariants:
- Zero use of eval() or dynamic code execution.
- Safe JMESPath and fallback dot-notation path traversal only.
- Strict PASS / FAIL / ERROR / NOT_EVALUATED statuses.
- Deterministic failures cannot be overridden by LLM judges.
"""

from __future__ import annotations

import enum
import logging
import re
from typing import Any

import jmespath
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class InvariantSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InvariantStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    NOT_EVALUATED = "NOT_EVALUATED"


class InvariantSpec(BaseModel):
    """Specification of a deterministic invariant."""

    model_config = {"frozen": True}

    id: str = Field(..., description="Unique invariant identifier (e.g. 'refund_once')")
    description: str = Field(default="", description="Human readable description")
    severity: InvariantSeverity = Field(
        default=InvariantSeverity.CRITICAL,
        description="Severity level; CRITICAL failures veto production readiness",
    )
    path: str = Field(..., description="JMESPath or dot-notation path to extract target value")
    operator: str = Field(
        ...,
        description=(
            "Supported operators: eq, neq, lt, lte, gt, gte, exists, not_exists, "
            "count_eq, count_lte, count_gte, contains, not_contains"
        ),
    )
    value: Any = Field(default=None, description="Expected value or parameter")


class InvariantResult(BaseModel):
    """Result of evaluating a single deterministic invariant."""

    model_config = {"frozen": True}

    invariant_id: str
    status: InvariantStatus
    severity: InvariantSeverity
    expected: Any
    observed: Any
    evidence_refs: list[str] = Field(default_factory=list)
    error_detail: str | None = None


def safe_path_search(path: str, context: dict[str, Any]) -> Any:
    """Safely search context using JMESPath with dictionary dot-path fallback."""
    # Strip leading $. if present
    clean_path = path.strip()
    if clean_path.startswith("$."):
        clean_path = clean_path[2:]
    elif clean_path == "$":
        return context

    try:
        res = jmespath.search(clean_path, context)
        if res is not None:
            return res
    except Exception:
        pass

    # Fallback dot-separated dictionary traversal
    parts = clean_path.split(".")
    curr: Any = context
    for p in parts:
        clean_p = p.strip("\"'")
        if isinstance(curr, dict) and clean_p in curr:
            curr = curr[clean_p]
        elif isinstance(curr, list) and clean_p.isdigit():
            idx = int(clean_p)
            if 0 <= idx < len(curr):
                curr = curr[idx]
            else:
                return None
        else:
            return None
    return curr


def _values_equal(expected: Any, actual: Any) -> bool:
    """Robust equality comparison supporting numeric tolerance and regex strings."""
    if expected is None and actual is None:
        return True
    if expected == actual:
        return True
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(float(expected) - float(actual)) < 1e-6
    if isinstance(expected, dict) and isinstance(actual, dict):
        return all(k in actual and _values_equal(v, actual[k]) for k, v in expected.items())
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return False
        return all(_values_equal(e, a) for e, a in zip(expected, actual, strict=False))
    if isinstance(expected, str) and isinstance(actual, str):
        if expected.startswith("/") and expected.endswith("/") and len(expected) > 2:
            return bool(re.search(expected[1:-1], actual))
        return expected.strip() == actual.strip()
    return False


def evaluate_invariant(
    spec: InvariantSpec,
    context: dict[str, Any],
    evidence_refs: list[str] | None = None,
) -> InvariantResult:
    """Evaluate a single invariant against an execution context."""
    refs = list(evidence_refs or [])
    observed: Any = None
    op = spec.operator.strip().lower()

    try:
        observed = safe_path_search(spec.path, context)
    except Exception as exc:
        return InvariantResult(
            invariant_id=spec.id,
            status=InvariantStatus.ERROR,
            severity=spec.severity,
            expected=spec.value,
            observed=None,
            evidence_refs=refs,
            error_detail=f"Failed to query path {spec.path!r}: {exc}",
        )

    try:
        # 1. Existence operators
        if op == "exists":
            passed = observed is not None and not (
                isinstance(observed, (list, dict, str)) and len(observed) == 0
            )
        elif op in ("not_exists", "not_exist"):
            passed = observed is None or (
                isinstance(observed, (list, dict, str)) and len(observed) == 0
            )

        # 2. Equality operators
        elif op in ("eq", "equals", "=="):
            passed = _values_equal(spec.value, observed)
        elif op in ("neq", "not_equals", "!="):
            passed = not _values_equal(spec.value, observed)

        # 3. Numeric ordering
        elif op == "lt":
            passed = float(observed) < float(spec.value)
        elif op == "lte":
            passed = float(observed) <= float(spec.value)
        elif op == "gt":
            passed = float(observed) > float(spec.value)
        elif op == "gte":
            passed = float(observed) >= float(spec.value)

        # 4. Count operators
        elif op == "count_eq":
            count = (
                len(observed)
                if isinstance(observed, (list, dict, str))
                else (1 if observed is not None else 0)
            )
            passed = count == int(spec.value)
        elif op == "count_lte":
            count = (
                len(observed)
                if isinstance(observed, (list, dict, str))
                else (1 if observed is not None else 0)
            )
            passed = count <= int(spec.value)
        elif op == "count_gte":
            count = (
                len(observed)
                if isinstance(observed, (list, dict, str))
                else (1 if observed is not None else 0)
            )
            passed = count >= int(spec.value)

        # 5. Containment operators
        elif op == "contains":
            if isinstance(observed, (list, dict, str)) and spec.value is not None:
                passed = spec.value in observed
            else:
                passed = False
        elif op == "not_contains":
            if isinstance(observed, (list, dict, str)) and spec.value is not None:
                passed = spec.value not in observed
            else:
                passed = True

        else:
            return InvariantResult(
                invariant_id=spec.id,
                status=InvariantStatus.ERROR,
                severity=spec.severity,
                expected=spec.value,
                observed=observed,
                evidence_refs=refs,
                error_detail=f"Unsupported invariant operator: {spec.operator!r}",
            )

        return InvariantResult(
            invariant_id=spec.id,
            status=InvariantStatus.PASS if passed else InvariantStatus.FAIL,
            severity=spec.severity,
            expected=spec.value,
            observed=observed,
            evidence_refs=refs,
        )

    except Exception as exc:
        logger.exception("Error evaluating invariant %s", spec.id)
        return InvariantResult(
            invariant_id=spec.id,
            status=InvariantStatus.ERROR,
            severity=spec.severity,
            expected=spec.value,
            observed=observed,
            evidence_refs=refs,
            error_detail=f"Evaluation exception: {exc}",
        )


class InvariantEngine:
    """Evaluates suites of invariants and assesses critical failure boundaries."""

    @staticmethod
    def evaluate_all(
        invariants: list[InvariantSpec],
        context: dict[str, Any],
        evidence_refs: list[str] | None = None,
    ) -> list[InvariantResult]:
        """Evaluate a list of invariants in order."""
        return [evaluate_invariant(inv, context, evidence_refs) for inv in invariants]

    @staticmethod
    def has_critical_failure(results: list[InvariantResult]) -> bool:
        """Return True if any CRITICAL invariant failed or encountered an error."""
        return any(
            r.severity == InvariantSeverity.CRITICAL
            and r.status in (InvariantStatus.FAIL, InvariantStatus.ERROR)
            for r in results
        )

    @staticmethod
    def summary(results: list[InvariantResult]) -> dict[str, int]:
        """Aggregate invariant evaluation results into counts."""
        return {
            "total": len(results),
            "passed": sum(1 for r in results if r.status == InvariantStatus.PASS),
            "failed": sum(1 for r in results if r.status == InvariantStatus.FAIL),
            "errors": sum(1 for r in results if r.status == InvariantStatus.ERROR),
            "critical_failures": sum(
                1
                for r in results
                if r.severity == InvariantSeverity.CRITICAL
                and r.status in (InvariantStatus.FAIL, InvariantStatus.ERROR)
            ),
        }
