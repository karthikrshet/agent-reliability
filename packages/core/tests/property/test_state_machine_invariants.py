"""
Property-based tests for EvaluationRunStateMachine using Hypothesis.

These tests verify invariants that must hold across ALL possible inputs —
not just the happy path cases covered by unit tests.

Invariants tested:
1. State never changes after a failed transition.
2. Version never decreases.
3. Terminal states are always terminal after any operation.
4. No transition sequence produces a COMPLETED state from CANCELLED.
5. allowed_transitions() is always a subset of EvaluationRunState values.

Following the TDD skill: these run alongside unit tests, not instead of them.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from arl.core.errors import InvalidStateTransitionError, TerminalStateImmutableError
from arl.core.state_machine import (
    EvaluationRunState,
    EvaluationRunStateMachine,
    TERMINAL_STATES,
    allowed_transitions,
    is_terminal,
)

ALL_STATES = list(EvaluationRunState)


@given(
    from_state=st.sampled_from(list(TERMINAL_STATES)),
    to_state=st.sampled_from(ALL_STATES),
)
@settings(max_examples=50)
def test_property_terminal_states_always_raise(
    from_state: EvaluationRunState,
    to_state: EvaluationRunState,
) -> None:
    """Any transition attempt from a terminal state must raise."""
    machine = EvaluationRunStateMachine(
        current_state=from_state,
        current_version=0,
        run_id="prop-test",
    )
    try:
        machine.transition(to_state=to_state, actor="test", reason="property test")
        # Should never reach here
        raise AssertionError(
            f"Expected TerminalStateImmutableError from {from_state} -> {to_state}"
        )
    except TerminalStateImmutableError:
        pass  # expected
    # State must not have changed
    assert machine.state == from_state


@given(
    initial_version=st.integers(min_value=0, max_value=1000),
)
@settings(max_examples=30)
def test_property_version_monotonically_increases(
    initial_version: int,
) -> None:
    """Version counter must never decrease."""
    machine = EvaluationRunStateMachine(
        current_state=EvaluationRunState.CREATED,
        current_version=initial_version,
        run_id="version-prop",
    )
    transition = machine.transition(
        to_state=EvaluationRunState.VALIDATING,
        actor="test",
        reason="property",
    )
    assert machine.version > initial_version
    assert transition.version_after == initial_version + 1
    assert transition.version_before == initial_version


@given(
    from_state=st.sampled_from(ALL_STATES),
    to_state=st.sampled_from(ALL_STATES),
)
@settings(max_examples=100)
def test_property_state_unchanged_after_invalid_transition(
    from_state: EvaluationRunState,
    to_state: EvaluationRunState,
) -> None:
    """State must never change after any type of failed transition."""
    machine = EvaluationRunStateMachine(
        current_state=from_state,
        current_version=0,
        run_id="state-invariant",
    )
    original_version = machine.version

    try:
        machine.transition(to_state=to_state, actor="test", reason="property")
        # Success case — state changed to to_state (that's fine)
        assert machine.state == to_state
    except (InvalidStateTransitionError, TerminalStateImmutableError):
        # Failure case — state MUST be unchanged
        assert machine.state == from_state
        assert machine.version == original_version


@given(state=st.sampled_from(ALL_STATES))
@settings(max_examples=20)
def test_property_allowed_transitions_are_valid_states(
    state: EvaluationRunState,
) -> None:
    """allowed_transitions() must always return a subset of EvaluationRunState."""
    all_state_values = set(EvaluationRunState)
    result = allowed_transitions(state)
    assert result.issubset(all_state_values)


@given(state=st.sampled_from(list(TERMINAL_STATES)))
@settings(max_examples=20)
def test_property_is_terminal_consistent_with_allowed_transitions(
    state: EvaluationRunState,
) -> None:
    """If is_terminal(state) is True, allowed_transitions must be empty."""
    assert is_terminal(state) is True
    assert len(allowed_transitions(state)) == 0
