"""
Unit tests for EvaluationRunStateMachine.

Following the TDD skill (karthikrshet/aiskills):
- Tests define expected behaviour BEFORE implementation details matter.
- Every test asserts on observable outcomes (state, exceptions, transitions).
- No test merely asserts that a function was called.

Coverage targets:
- All valid transitions must succeed.
- All invalid transitions must raise InvalidStateTransitionError.
- Terminal state mutations must raise TerminalStateImmutableError.
- Optimistic concurrency version must increment on every transition.
- Cancellation path: CANCEL_REQUESTED -> CANCELLED.
"""

from __future__ import annotations

import pytest

from arl.core.errors import InvalidStateTransitionError, TerminalStateImmutableError
from arl.core.state_machine import (
    TERMINAL_STATES,
    EvaluationRunState,
    EvaluationRunStateMachine,
    StateTransition,
    allowed_transitions,
    is_terminal,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_machine(
    state: EvaluationRunState = EvaluationRunState.CREATED,
    version: int = 0,
    run_id: str = "run-test-001",
) -> EvaluationRunStateMachine:
    return EvaluationRunStateMachine(
        current_state=state,
        current_version=version,
        run_id=run_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Valid transition tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_created_to_validating_succeeds() -> None:
    machine = make_machine(EvaluationRunState.CREATED)
    transition = machine.transition(
        to_state=EvaluationRunState.VALIDATING,
        actor="api",
        reason="Run accepted",
    )
    assert machine.state == EvaluationRunState.VALIDATING
    assert isinstance(transition, StateTransition)
    assert transition.from_state == EvaluationRunState.CREATED
    assert transition.to_state == EvaluationRunState.VALIDATING
    assert transition.actor == "api"


@pytest.mark.unit
def test_full_happy_path_transition_sequence() -> None:
    """Walk the complete happy path: CREATED -> COMPLETED."""
    machine = make_machine(EvaluationRunState.CREATED)
    path = [
        EvaluationRunState.VALIDATING,
        EvaluationRunState.QUEUED,
        EvaluationRunState.PROVISIONING,
        EvaluationRunState.RUNNING,
        EvaluationRunState.GRADING,
        EvaluationRunState.AGGREGATING,
        EvaluationRunState.COMPLETED,
    ]
    for state in path:
        machine.transition(to_state=state, actor="system", reason="test")

    assert machine.state == EvaluationRunState.COMPLETED


@pytest.mark.unit
def test_cancellation_path() -> None:
    """RUNNING -> CANCEL_REQUESTED -> CANCELLED."""
    machine = make_machine(EvaluationRunState.RUNNING)
    machine.request_cancellation(actor="user", reason="user requested cancel")
    assert machine.state == EvaluationRunState.CANCEL_REQUESTED

    machine.transition(
        to_state=EvaluationRunState.CANCELLED,
        actor="worker",
        reason="worker acknowledged cancellation",
    )
    assert machine.state == EvaluationRunState.CANCELLED


@pytest.mark.unit
def test_any_state_can_fail() -> None:
    """From RUNNING, failure transition to FAILED must succeed."""
    machine = make_machine(EvaluationRunState.RUNNING)
    machine.transition(
        to_state=EvaluationRunState.FAILED,
        actor="worker",
        reason="unhandled exception in trial executor",
    )
    assert machine.state == EvaluationRunState.FAILED


@pytest.mark.unit
def test_timeout_from_running() -> None:
    machine = make_machine(EvaluationRunState.RUNNING)
    machine.transition(
        to_state=EvaluationRunState.TIMED_OUT,
        actor="worker",
        reason="trial exceeded max_duration_seconds",
    )
    assert machine.state == EvaluationRunState.TIMED_OUT


# ─────────────────────────────────────────────────────────────────────────────
# Invalid transition tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_invalid_transition_raises() -> None:
    """CREATED cannot jump to RUNNING — must raise."""
    machine = make_machine(EvaluationRunState.CREATED)
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        machine.transition(
            to_state=EvaluationRunState.RUNNING,
            actor="api",
            reason="invalid shortcut",
        )
    # State must remain unchanged after a failed transition
    assert machine.state == EvaluationRunState.CREATED
    assert exc_info.value.context["from_state"] == "CREATED"
    assert exc_info.value.context["to_state"] == "RUNNING"


@pytest.mark.unit
def test_cannot_skip_provisioning() -> None:
    """QUEUED cannot jump directly to RUNNING."""
    machine = make_machine(EvaluationRunState.QUEUED)
    with pytest.raises(InvalidStateTransitionError):
        machine.transition(
            to_state=EvaluationRunState.RUNNING,
            actor="worker",
            reason="invalid skip",
        )
    assert machine.state == EvaluationRunState.QUEUED


@pytest.mark.unit
@pytest.mark.parametrize("terminal_state", list(TERMINAL_STATES))
def test_terminal_state_raises_on_transition(terminal_state: EvaluationRunState) -> None:
    """Any transition from a terminal state must raise TerminalStateImmutableError."""
    machine = make_machine(terminal_state)
    with pytest.raises(TerminalStateImmutableError) as exc_info:
        machine.transition(
            to_state=EvaluationRunState.RUNNING,
            actor="attacker",
            reason="attempt to reopen closed run",
        )
    assert exc_info.value.context["run_id"] == "run-test-001"
    # State must remain terminal after failed transition
    assert machine.state == terminal_state


@pytest.mark.unit
def test_cancelled_cannot_become_completed() -> None:
    """Security: a cancelled run must never be reported as completed."""
    machine = make_machine(EvaluationRunState.CANCELLED)
    with pytest.raises(TerminalStateImmutableError):
        machine.transition(
            to_state=EvaluationRunState.COMPLETED,
            actor="result-manipulator",
            reason="fraudulent completion",
        )
    assert machine.state == EvaluationRunState.CANCELLED


# ─────────────────────────────────────────────────────────────────────────────
# Optimistic concurrency / version tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_version_increments_on_each_transition() -> None:
    """Version must increment by exactly 1 on every successful transition."""
    machine = make_machine(EvaluationRunState.CREATED, version=5)
    transition = machine.transition(
        to_state=EvaluationRunState.VALIDATING,
        actor="api",
        reason="test",
    )
    assert transition.version_before == 5
    assert transition.version_after == 6
    assert machine.version == 6


@pytest.mark.unit
def test_version_does_not_change_on_failed_transition() -> None:
    """A failed transition must not change the version counter."""
    machine = make_machine(EvaluationRunState.CREATED, version=3)
    with pytest.raises(InvalidStateTransitionError):
        machine.transition(
            to_state=EvaluationRunState.COMPLETED,
            actor="api",
            reason="invalid",
        )
    assert machine.version == 3


# ─────────────────────────────────────────────────────────────────────────────
# StateTransition record tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_transition_record_is_immutable() -> None:
    """StateTransition is a frozen dataclass — mutation must raise."""
    machine = make_machine(EvaluationRunState.CREATED)
    transition = machine.transition(
        to_state=EvaluationRunState.VALIDATING,
        actor="api",
        reason="test",
    )
    with pytest.raises((AttributeError, TypeError)):
        transition.actor = "hacker"  # type: ignore[misc]


@pytest.mark.unit
def test_transition_record_contains_required_evidence() -> None:
    """Every StateTransition must carry full audit evidence."""
    machine = make_machine(EvaluationRunState.CREATED, run_id="run-evidence-001")
    transition = machine.transition(
        to_state=EvaluationRunState.VALIDATING,
        actor="api-worker",
        reason="run validated",
        metadata={"correlation_id": "corr-123"},
    )
    assert transition.run_id == "run-evidence-001"
    assert transition.actor == "api-worker"
    assert transition.reason == "run validated"
    assert transition.occurred_at is not None
    assert transition.metadata["correlation_id"] == "corr-123"


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_is_terminal_returns_true_for_all_terminal_states() -> None:
    for state in TERMINAL_STATES:
        assert is_terminal(state) is True


@pytest.mark.unit
def test_is_terminal_returns_false_for_non_terminal_states() -> None:
    non_terminal = set(EvaluationRunState) - TERMINAL_STATES
    for state in non_terminal:
        assert is_terminal(state) is False


@pytest.mark.unit
def test_allowed_transitions_created_state() -> None:
    transitions = allowed_transitions(EvaluationRunState.CREATED)
    assert EvaluationRunState.VALIDATING in transitions
    assert EvaluationRunState.FAILED in transitions
    # Must not be able to jump ahead
    assert EvaluationRunState.RUNNING not in transitions
    assert EvaluationRunState.COMPLETED not in transitions


@pytest.mark.unit
def test_terminal_states_have_no_allowed_transitions() -> None:
    """Terminal states must have an empty allowed_transitions set."""
    for state in TERMINAL_STATES:
        assert len(allowed_transitions(state)) == 0


@pytest.mark.unit
def test_can_transition_to_returns_correct_result() -> None:
    machine = make_machine(EvaluationRunState.CREATED)
    assert machine.can_transition_to(EvaluationRunState.VALIDATING) is True
    assert machine.can_transition_to(EvaluationRunState.COMPLETED) is False


@pytest.mark.unit
def test_is_terminal_property_on_machine() -> None:
    non_terminal_machine = make_machine(EvaluationRunState.RUNNING)
    assert non_terminal_machine.is_terminal is False

    terminal_machine = make_machine(EvaluationRunState.COMPLETED)
    assert terminal_machine.is_terminal is True
