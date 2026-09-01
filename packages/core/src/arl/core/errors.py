"""
Agent Reliability Lab — Domain Error Hierarchy.

All errors are typed, named, and carry structured context.
No broad 'except Exception' swallowing. Every error maps to a specific
category for accurate incident classification and CLI exit codes.

Exit code mapping (see CLI specification):
    0  — success
    1  — reliability threshold failed    → ReadinessThresholdError
    2  — invalid configuration           → ConfigurationError, ScenarioValidationError
    3  — execution infrastructure error  → InfrastructureError, WorkerLeaseError
    4  — security policy violation       → SecurityViolationError, ForbiddenEffectDetectedError
    5  — insufficient evidence           → InsufficientEvidenceError
"""

from __future__ import annotations

from typing import Any


class ARLError(Exception):
    """Base class for all Agent Reliability Lab errors.

    Carries a structured context dict so that error details can be
    serialised to JSON without losing information.
    """

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context: dict[str, Any] = context

    def __repr__(self) -> str:
        ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
        return f"{type(self).__name__}({self.message!r}, {ctx})"


# ─────────────────────────────────────────────────────────────────────────────
# Domain errors — business-rule violations within the evaluation domain
# ─────────────────────────────────────────────────────────────────────────────


class DomainError(ARLError):
    """A business rule has been violated."""


class InvalidStateTransitionError(DomainError):
    """An illegal state machine transition was attempted.

    Security rationale: Rejecting invalid transitions prevents races
    between concurrent workers from corrupting run state.
    """

    def __init__(self, from_state: str, to_state: str, run_id: str) -> None:
        super().__init__(
            f"Cannot transition run {run_id!r} from {from_state!r} to {to_state!r}",
            from_state=from_state,
            to_state=to_state,
            run_id=run_id,
        )


class TerminalStateImmutableError(DomainError):
    """A terminal run state cannot be modified by normal operations.

    Terminal states (COMPLETED, FAILED, CANCELLED, TIMED_OUT) are
    immutable to prevent post-hoc result manipulation.
    """

    def __init__(self, run_id: str, current_state: str) -> None:
        super().__init__(
            f"Run {run_id!r} is in terminal state {current_state!r} and cannot be modified",
            run_id=run_id,
            current_state=current_state,
        )


class ConcurrentModificationError(DomainError):
    """A concurrent modification was detected via optimistic concurrency control.

    Callers must reload and retry the operation.
    """

    def __init__(self, resource: str, resource_id: str, expected_version: int) -> None:
        super().__init__(
            f"Concurrent modification on {resource} {resource_id!r}: "
            f"expected version {expected_version}",
            resource=resource,
            resource_id=resource_id,
            expected_version=expected_version,
        )


class BudgetExceededError(DomainError):
    """An agent has exceeded its configured budget.

    Budget categories: turns, tool_calls, duration_seconds, cost_usd, tokens.
    """

    def __init__(
        self,
        budget_type: str,
        limit: float | int,
        actual: float | int,
        trial_id: str,
    ) -> None:
        super().__init__(
            f"Budget exceeded for trial {trial_id!r}: {budget_type} limit={limit} actual={actual}",
            budget_type=budget_type,
            limit=limit,
            actual=actual,
            trial_id=trial_id,
        )


class DuplicateEffectError(DomainError):
    """A side-effecting tool was called more times than permitted.

    Example: refund.create called twice for the same order.
    This is a deterministic grading failure — it must not be overridden
    by a model judge.
    """

    def __init__(self, tool_name: str, idempotency_key: str, call_count: int) -> None:
        super().__init__(
            f"Duplicate effect detected: {tool_name!r} called {call_count} times "
            f"with idempotency_key={idempotency_key!r}",
            tool_name=tool_name,
            idempotency_key=idempotency_key,
            call_count=call_count,
        )


class ForbiddenEffectDetectedError(DomainError):
    """A forbidden world-state effect has been detected.

    Security rationale: Forbidden effects (e.g. customer.delete, cross-tenant
    writes) represent safety violations that must surface as critical findings
    and trigger NOT_READY verdicts regardless of other scores.
    """

    def __init__(self, effect_path: str, actual_value: Any, trial_id: str) -> None:
        super().__init__(
            f"Forbidden effect detected in trial {trial_id!r}: "
            f"path={effect_path!r} value={actual_value!r}",
            effect_path=effect_path,
            actual_value=actual_value,
            trial_id=trial_id,
        )


class IsolationViolationError(DomainError):
    """Cross-tenant or cross-session data isolation has been violated.

    Security rationale: Tenant isolation failures are critical security
    findings. They must cause immediate NOT_READY verdicts.
    """

    def __init__(
        self,
        violating_tenant_id: str,
        accessed_tenant_id: str,
        resource: str,
    ) -> None:
        super().__init__(
            f"Isolation violation: tenant {violating_tenant_id!r} accessed "
            f"resource {resource!r} belonging to tenant {accessed_tenant_id!r}",
            violating_tenant_id=violating_tenant_id,
            accessed_tenant_id=accessed_tenant_id,
            resource=resource,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Scenario errors
# ─────────────────────────────────────────────────────────────────────────────


class ScenarioValidationError(ARLError):
    """A scenario YAML failed schema validation.

    Scenario loading fails closed — an invalid scenario must never execute.
    """

    def __init__(self, path: str, errors: list[str]) -> None:
        formatted = "\n  ".join(errors)
        super().__init__(
            f"Scenario validation failed for {path!r}:\n  {formatted}",
            path=path,
            errors=errors,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Security errors
# ─────────────────────────────────────────────────────────────────────────────


class SecurityViolationError(ARLError):
    """A security policy has been violated.

    Maps to CLI exit code 4. Triggers NOT_READY verdict.
    """

    def __init__(self, violation_type: str, detail: str, **context: Any) -> None:
        super().__init__(
            f"Security violation [{violation_type}]: {detail}",
            violation_type=violation_type,
            detail=detail,
            **context,
        )


class UnauthorizedError(ARLError):
    """An unauthorized operation was attempted."""

    def __init__(self, actor: str, action: str, resource: str) -> None:
        super().__init__(
            f"Actor {actor!r} is not authorized to perform {action!r} on {resource!r}",
            actor=actor,
            action=action,
            resource=resource,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure errors
# ─────────────────────────────────────────────────────────────────────────────


class InfrastructureError(ARLError):
    """An infrastructure-level failure occurred.

    Maps to CLI exit code 3.
    """

    def __init__(self, message: str, component: str = "", **context: Any) -> None:
        super().__init__(
            f"Infrastructure error [{component}]: {message}" if component else f"Infrastructure error: {message}",
            component=component,
            **context,
        )


class WorkerLeaseError(InfrastructureError):
    """A worker lease operation failed.

    This may indicate a crash recovery scenario. The run state must be
    left in a recoverable (non-terminal non-successful) state.
    """

    def __init__(self, lease_id: str, detail: str) -> None:
        super().__init__(
            f"Worker lease error for lease {lease_id!r}: {detail}",
            lease_id=lease_id,
            detail=detail,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Grading errors
# ─────────────────────────────────────────────────────────────────────────────


class GradingError(ARLError):
    """A grader encountered an error during evaluation.

    Grading errors are surfaced as GRADER_ERROR findings. They do not
    silently produce passing scores.
    """

    def __init__(self, grader_id: str, trial_id: str, detail: str) -> None:
        super().__init__(
            f"Grader {grader_id!r} failed for trial {trial_id!r}: {detail}",
            grader_id=grader_id,
            trial_id=trial_id,
            detail=detail,
        )


class EvidenceError(ARLError):
    """Required evidence for a verdict is missing or invalid."""

    def __init__(self, required_evidence: str, run_id: str) -> None:
        super().__init__(
            f"Missing required evidence {required_evidence!r} for run {run_id!r}",
            required_evidence=required_evidence,
            run_id=run_id,
        )


class InsufficientEvidenceError(ARLError):
    """Too few trials were run to support a reliable verdict.

    Maps to CLI exit code 5.
    """

    def __init__(self, run_id: str, completed_trials: int, required_trials: int) -> None:
        super().__init__(
            f"Insufficient evidence for run {run_id!r}: "
            f"{completed_trials}/{required_trials} trials completed",
            run_id=run_id,
            completed_trials=completed_trials,
            required_trials=required_trials,
        )


class ReadinessThresholdError(ARLError):
    """The agent failed to meet the configured readiness threshold.

    Maps to CLI exit code 1.
    """

    def __init__(self, run_id: str, score: float, threshold: float) -> None:
        super().__init__(
            f"Agent readiness threshold not met for run {run_id!r}: "
            f"score={score:.2f} threshold={threshold:.2f}",
            run_id=run_id,
            score=score,
            threshold=threshold,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Fault injection errors
# ─────────────────────────────────────────────────────────────────────────────


class FaultInjectionError(ARLError):
    """Fault injection configuration or execution failed."""

    def __init__(self, fault_type: str, detail: str) -> None:
        super().__init__(
            f"Fault injection error [{fault_type}]: {detail}",
            fault_type=fault_type,
            detail=detail,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Configuration errors
# ─────────────────────────────────────────────────────────────────────────────


class ConfigurationError(ARLError):
    """The system configuration is invalid.

    Maps to CLI exit code 2.
    Configuration is validated at startup — this error aborts startup
    before any evaluation runs are accepted.
    """

    def __init__(self, field: str, detail: str) -> None:
        super().__init__(
            f"Configuration error for {field!r}: {detail}",
            field=field,
            detail=detail,
        )
