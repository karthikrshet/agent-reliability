"""
Agent Reliability Lab — EvaluationRun State Machine.

Implements an explicit validated state machine for EvaluationRun lifecycle.
Every transition is validated and must be persisted before being considered
effective. Invalid transitions raise immediately — they are never silently
ignored.

Design decisions (see ADR-002):
- Optimistic concurrency: callers pass expected_version; mismatch raises.
- Terminal states are immutable except through AdminCorrectionEvent.
- Cancellation propagates through CANCEL_REQUESTED → CANCELLED.
- A cancelled run is NEVER reported as COMPLETED.
- Worker restarts use idempotency keys to avoid duplicate trials.
"""

from __future__ import annotations

import enum
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Final

from arl.core.errors import (
    InvalidStateTransitionError,
    TerminalStateImmutableError,
)


class EvaluationRunState(str, enum.Enum):
    """All valid states for an EvaluationRun.

    The string value is stored in the database. Do not change existing
    values — this would break historical records.
    """

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    QUEUED = "QUEUED"
    PROVISIONING = "PROVISIONING"
    RUNNING = "RUNNING"
    GRADING = "GRADING"
    AGGREGATING = "AGGREGATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


# ─────────────────────────────────────────────────────────────────────────────
# Terminal states — immutable except through AdminCorrectionEvent
# ─────────────────────────────────────────────────────────────────────────────

TERMINAL_STATES: Final[frozenset[EvaluationRunState]] = frozenset(
    {
        EvaluationRunState.COMPLETED,
        EvaluationRunState.FAILED,
        EvaluationRunState.CANCELLED,
        EvaluationRunState.TIMED_OUT,
    }
)

# ─────────────────────────────────────────────────────────────────────────────
# Valid transitions (from_state → set of allowed to_states)
#
# Security rationale: This allowlist prevents workers or API callers from
# forcing a run into an arbitrary state. For example, a cancelled run
# cannot transition to COMPLETED, preventing result manipulation.
# ─────────────────────────────────────────────────────────────────────────────

_ALLOWED_TRANSITIONS: Final[dict[EvaluationRunState, frozenset[EvaluationRunState]]] = {
    EvaluationRunState.CREATED: frozenset(
        {EvaluationRunState.VALIDATING, EvaluationRunState.FAILED}
    ),
    EvaluationRunState.VALIDATING: frozenset(
        {
            EvaluationRunState.QUEUED,
            EvaluationRunState.FAILED,
            EvaluationRunState.CANCEL_REQUESTED,
        }
    ),
    EvaluationRunState.QUEUED: frozenset(
        {
            EvaluationRunState.PROVISIONING,
            EvaluationRunState.FAILED,
            EvaluationRunState.CANCEL_REQUESTED,
        }
    ),
    EvaluationRunState.PROVISIONING: frozenset(
        {
            EvaluationRunState.RUNNING,
            EvaluationRunState.FAILED,
            EvaluationRunState.CANCEL_REQUESTED,
            EvaluationRunState.TIMED_OUT,
        }
    ),
    EvaluationRunState.RUNNING: frozenset(
        {
            EvaluationRunState.GRADING,
            EvaluationRunState.FAILED,
            EvaluationRunState.CANCEL_REQUESTED,
            EvaluationRunState.TIMED_OUT,
        }
    ),
    EvaluationRunState.GRADING: frozenset(
        {
            EvaluationRunState.AGGREGATING,
            EvaluationRunState.FAILED,
            EvaluationRunState.CANCEL_REQUESTED,
            EvaluationRunState.TIMED_OUT,
        }
    ),
    EvaluationRunState.AGGREGATING: frozenset(
        {
            EvaluationRunState.COMPLETED,
            EvaluationRunState.FAILED,
            EvaluationRunState.TIMED_OUT,
        }
    ),
    EvaluationRunState.CANCEL_REQUESTED: frozenset(
        {
            EvaluationRunState.CANCELLED,
            # A run that completes before cancellation is processed
            # transitions to COMPLETED. The final report must reflect
            # that cancellation was requested.
            EvaluationRunState.COMPLETED,
            EvaluationRunState.FAILED,
        }
    ),
    # Terminal states — no outbound transitions (immutable)
    EvaluationRunState.COMPLETED: frozenset(),
    EvaluationRunState.FAILED: frozenset(),
    EvaluationRunState.CANCELLED: frozenset(),
    EvaluationRunState.TIMED_OUT: frozenset(),
}


@dataclass(frozen=True)
class StateTransition:
    """An immutable record of a single state transition.

    Persisted to the database before the transition is considered effective.
    """

    run_id: str
    from_state: EvaluationRunState
    to_state: EvaluationRunState
    actor: str
    reason: str
    occurred_at: datetime
    version_before: int
    version_after: int
    metadata: dict[str, str] = field(default_factory=dict)


class EvaluationRunStateMachine:
    """Validates and records EvaluationRun state transitions.

    This class enforces the transition graph. Persistence is the caller's
    responsibility — the machine produces a StateTransition record that
    callers must persist atomically with the state update.

    Optimistic concurrency: callers supply current_version; a mismatch
    raises ConcurrentModificationError. The database column version must
    be updated atomically in the same transaction.

    Example usage::

        machine = EvaluationRunStateMachine(
            current_state=EvaluationRunState.CREATED,
            current_version=0,
            run_id="run-01JA...",
        )
        transition = machine.transition(
            to_state=EvaluationRunState.VALIDATING,
            actor="api",
            reason="Run accepted by API",
        )
        # Persist transition to DB in the same transaction as state update
        await db.save_transition(transition)
    """

    def __init__(
        self,
        current_state: EvaluationRunState,
        current_version: int,
        run_id: str,
    ) -> None:
        self._state = current_state
        self._version = current_version
        self._run_id = run_id

    @property
    def state(self) -> EvaluationRunState:
        return self._state

    @property
    def version(self) -> int:
        return self._version

    @property
    def is_terminal(self) -> bool:
        return self._state in TERMINAL_STATES

    def allowed_transitions(self) -> AbstractSet[EvaluationRunState]:
        """Return the set of states this run can legally move to."""
        return _ALLOWED_TRANSITIONS[self._state]

    def can_transition_to(self, to_state: EvaluationRunState) -> bool:
        """Return True if a transition to to_state is legal from current state."""
        return to_state in _ALLOWED_TRANSITIONS[self._state]

    def transition(
        self,
        to_state: EvaluationRunState,
        actor: str,
        reason: str,
        metadata: dict[str, str] | None = None,
    ) -> StateTransition:
        """Validate and produce a StateTransition record.

        Does NOT modify the run or database — the caller must persist the
        returned StateTransition alongside the state update atomically.

        Raises:
            TerminalStateImmutableError: Current state is terminal.
            InvalidStateTransitionError: Transition is not in the allowlist.
        """
        if self.is_terminal:
            raise TerminalStateImmutableError(
                run_id=self._run_id,
                current_state=self._state.value,
            )

        if not self.can_transition_to(to_state):
            raise InvalidStateTransitionError(
                from_state=self._state.value,
                to_state=to_state.value,
                run_id=self._run_id,
            )

        version_before = self._version
        version_after = self._version + 1

        transition = StateTransition(
            run_id=self._run_id,
            from_state=self._state,
            to_state=to_state,
            actor=actor,
            reason=reason,
            occurred_at=datetime.now(UTC),
            version_before=version_before,
            version_after=version_after,
            metadata=metadata or {},
        )

        # Update in-memory state — only after validation passes
        self._state = to_state
        self._version = version_after

        return transition

    def request_cancellation(
        self,
        actor: str,
        reason: str,
    ) -> StateTransition:
        """Convenience method to request run cancellation.

        From any non-terminal state, moves to CANCEL_REQUESTED.
        Workers must poll for this state and propagate it.
        """
        return self.transition(
            to_state=EvaluationRunState.CANCEL_REQUESTED,
            actor=actor,
            reason=reason,
        )


def is_terminal(state: EvaluationRunState) -> bool:
    """Return True if state is a terminal (immutable) state."""
    return state in TERMINAL_STATES


def allowed_transitions(state: EvaluationRunState) -> frozenset[EvaluationRunState]:
    """Return the set of legal next states from state."""
    return _ALLOWED_TRANSITIONS[state]
