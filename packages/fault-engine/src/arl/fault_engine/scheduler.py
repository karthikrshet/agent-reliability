"""
Agent Reliability Lab — Deterministic Fault Scheduler.

The FaultScheduler is the core of the fault injection engine. Given a
FaultPlan and a seed, it deterministically schedules faults for a trial.

DETERMINISM GUARANTEE:
The same scenario version + same seed ALWAYS produces the same fault schedule.
This enables reproducible test runs and regression detection.

IMPLEMENTATION NOTES:
- Do NOT use random.random() or any non-seeded random source.
- Use Python's random.Random(seed) for all random decisions (not the global instance).
- Fault injection occurs through adapters/proxies — never by patching global functions.
- Every injected fault creates a FaultEvent record (persisted before the fault fires).

Security note: fault injection is an internal testing mechanism. The scheduler
itself does not execute code in the agent's environment. Faults are applied
through the tool proxy layer.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from arl.core.domain.faults import FaultEvent, FaultType
from arl.core.errors import FaultInjectionError

if TYPE_CHECKING:
    from arl.scenario_engine.schema import (
        FaultPlanEntrySpec,
        FaultTriggerSpec,
    )

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScheduledFault:
    """A fault that has been scheduled for a specific tool invocation.

    This is the output of the scheduler — the proxy layer uses it to
    decide whether to inject a fault when a tool is called.
    """

    entry: FaultPlanEntrySpec
    trial_fault_seed: int


@dataclass
class FaultScheduler:
    """Determines which faults to inject during a trial.

    Usage::

        scheduler = FaultScheduler(
            fault_plan_entries=[...],
            trial_fault_seed=42,
            trial_id="trial-01JA...",
        )

        # Called by the tool proxy before executing a tool
        result = scheduler.check(tool_name="refund.create", invocation_index=1)
        if result is not None:
            # inject the fault, create FaultEvent
            ...

    The scheduler is stateful — it tracks invocation counts per tool.
    Each trial must use a fresh FaultScheduler instance.
    """

    fault_plan_entries: list[FaultPlanEntrySpec]
    trial_fault_seed: int
    trial_id: str
    # Internal state — invocation count per tool name (1-based)
    _invocation_counts: dict[str, int] = field(default_factory=dict, init=False)
    # Seeded RNG — isolated from the global random state
    _rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.trial_fault_seed)  # noqa: S311 (seeded deterministic use)
        self._invocation_counts = {}

    def check(
        self,
        tool_name: str,
        call_arguments: dict[str, Any] | None = None,
        elapsed_seconds: float = 0.0,
    ) -> ScheduledFault | None:
        """Check whether a fault should be injected for this tool call.

        Called by the tool proxy BEFORE executing the real tool.

        Args:
            tool_name: The name of the tool being called.
            call_arguments: The tool call arguments (for argument_contains matching).
            elapsed_seconds: Seconds elapsed since trial start.

        Returns:
            A ScheduledFault if a fault should be injected, else None.
        """
        # Track invocation count (1-based)
        self._invocation_counts[tool_name] = self._invocation_counts.get(tool_name, 0) + 1
        invocation_index = self._invocation_counts[tool_name]

        for entry in self.fault_plan_entries:
            if entry.target != tool_name:
                continue
            if self._trigger_matches(
                entry.trigger, invocation_index, call_arguments, elapsed_seconds
            ):
                logger.debug(
                    "Fault scheduled: tool=%s invocation=%d type=%s seed=%d",
                    tool_name,
                    invocation_index,
                    entry.behaviour.type,
                    self.trial_fault_seed,
                )
                return ScheduledFault(
                    entry=entry,
                    trial_fault_seed=self.trial_fault_seed,
                )

        return None

    def _trigger_matches(
        self,
        trigger: FaultTriggerSpec,
        invocation_index: int,
        call_arguments: dict[str, Any] | None,
        elapsed_seconds: float,
    ) -> bool:
        """Return True if this trigger fires for the current invocation."""
        # Check invocation-based trigger
        if trigger.invocation is not None and invocation_index != trigger.invocation:
            return False

        # Check time-based trigger
        if trigger.after_seconds is not None and elapsed_seconds < trigger.after_seconds:
            return False

        # Check argument-contains trigger
        if trigger.argument_contains is not None:
            if call_arguments is None:
                return False
            if not _dict_contains(call_arguments, trigger.argument_contains):
                return False

        return True

    def make_fault_event(
        self,
        scheduled: ScheduledFault,
        tool_name: str,
        tool_call_id: str | None = None,
        ulid_factory: Any = None,
    ) -> FaultEvent:
        """Create a FaultEvent record for a scheduled fault.

        The FaultEvent must be PERSISTED before the fault is applied.
        Persistence before injection ensures that even if the worker crashes
        during injection, there is evidence of the planned fault.

        Args:
            scheduled: The scheduled fault from check().
            tool_name: The tool being faulted.
            tool_call_id: The ToolCall ID if already created.
            ulid_factory: Optional ULID factory (defaults to str(random ULID)).

        Returns:
            FaultEvent — caller must persist this before firing the fault.
        """
        from arl.core.domain.faults import FaultBehaviour as DomainFaultBehaviour

        invocation = scheduled.entry.trigger.invocation
        behaviour_spec = scheduled.entry.behaviour

        try:
            fault_type = FaultType(behaviour_spec.type)
        except ValueError as exc:
            raise FaultInjectionError(
                fault_type=behaviour_spec.type,
                detail=f"Unknown fault type: {behaviour_spec.type!r}",
            ) from exc

        if ulid_factory is not None:
            event_id = ulid_factory()
        else:
            import uuid

            event_id = str(uuid.uuid4())

        domain_behaviour = DomainFaultBehaviour(
            fault_type=fault_type,
            delay_ms=behaviour_spec.delay_ms,
            http_status=behaviour_spec.http_status,
            retry_after_seconds=behaviour_spec.retry_after_seconds,
            side_effect_committed=behaviour_spec.side_effect_committed,
            response_body=behaviour_spec.response_body,
        )

        return FaultEvent(
            id=event_id,
            trial_id=self.trial_id,
            tool_call_id=tool_call_id,
            fault_type=fault_type,
            target_tool=tool_name,
            trigger_invocation=invocation,
            behaviour=domain_behaviour,
            fault_seed=self.trial_fault_seed,
            injected_at=datetime.now(UTC),
            agent_observed_error=None,  # set after the fault fires
        )


def _dict_contains(source: dict[str, Any], subset: dict[str, Any]) -> bool:
    """Return True if all key-value pairs in subset exist in source.

    Supports one level of nesting. Used for argument_contains matching.
    """
    for key, expected_value in subset.items():
        if key not in source:
            return False
        actual = source[key]
        if isinstance(expected_value, dict) and isinstance(actual, dict):
            if not _dict_contains(actual, expected_value):
                return False
        elif actual != expected_value:
            return False
    return True


def derive_trial_fault_seed(run_seed: int, trial_index: int) -> int:
    """Derive a deterministic trial-specific fault seed from the run seed.

    The same run_seed + trial_index always produces the same trial seed.
    This ensures per-trial determinism while keeping trials independent.

    Formula: mix run_seed and trial_index using a simple hash.
    """
    # XOR-based mixing — simple, fast, deterministic, no external deps
    return (run_seed * 6364136223846793005 + trial_index) & 0xFFFF_FFFF_FFFF_FFFF
