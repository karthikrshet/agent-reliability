"""
Unit tests for the FaultScheduler.

TDD approach: tests define the observable contract of the scheduler:
- Same seed always produces same fault decisions (determinism).
- Invocation index is tracked correctly per tool.
- Trigger conditions match correctly.
- FaultEvent records contain correct data.
- derive_trial_fault_seed() is deterministic and stable.
"""

from __future__ import annotations

import pytest

from arl.fault_engine.scheduler import (
    FaultScheduler,
    ScheduledFault,
    derive_trial_fault_seed,
)
from arl.scenario_engine.schema import (
    FaultBehaviourSpec,
    FaultPlanEntrySpec,
    FaultTriggerSpec,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def make_entry(
    target: str = "refund.create",
    invocation: int | None = 1,
    fault_type: str = "http_500",
    side_effect_committed: bool = False,
) -> FaultPlanEntrySpec:
    return FaultPlanEntrySpec(
        target=target,
        trigger=FaultTriggerSpec(invocation=invocation),
        behaviour=FaultBehaviourSpec(
            type=fault_type,
            side_effect_committed=side_effect_committed,
        ),
    )


def make_scheduler(
    entries: list[FaultPlanEntrySpec] | None = None,
    seed: int = 42,
    trial_id: str = "trial-001",
) -> FaultScheduler:
    return FaultScheduler(
        fault_plan_entries=entries or [],
        trial_fault_seed=seed,
        trial_id=trial_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Basic trigger matching
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_no_fault_plan_never_injects() -> None:
    scheduler = make_scheduler(entries=[])
    for _ in range(10):
        result = scheduler.check("any.tool")
        assert result is None


@pytest.mark.unit
def test_fault_injected_on_matching_invocation() -> None:
    entry = make_entry(target="refund.create", invocation=1)
    scheduler = make_scheduler(entries=[entry])

    result = scheduler.check("refund.create")
    assert result is not None
    assert isinstance(result, ScheduledFault)
    assert result.entry.target == "refund.create"


@pytest.mark.unit
def test_fault_not_injected_on_non_matching_invocation() -> None:
    """Fault is set for invocation 3 — first two calls must return None."""
    entry = make_entry(target="refund.create", invocation=3)
    scheduler = make_scheduler(entries=[entry])

    assert scheduler.check("refund.create") is None  # invocation 1
    assert scheduler.check("refund.create") is None  # invocation 2
    result = scheduler.check("refund.create")        # invocation 3
    assert result is not None


@pytest.mark.unit
def test_wrong_tool_name_not_injected() -> None:
    entry = make_entry(target="refund.create", invocation=1)
    scheduler = make_scheduler(entries=[entry])

    result = scheduler.check("order.lookup")
    assert result is None


@pytest.mark.unit
def test_each_tool_has_independent_invocation_count() -> None:
    """Invocation tracking must be per-tool, not global."""
    entry = make_entry(target="tool.b", invocation=1)
    scheduler = make_scheduler(entries=[entry])

    # tool.a calls should not affect tool.b's counter
    scheduler.check("tool.a")
    scheduler.check("tool.a")
    scheduler.check("tool.a")

    # First call to tool.b should trigger fault (invocation=1)
    result = scheduler.check("tool.b")
    assert result is not None


# ─────────────────────────────────────────────────────────────────────────────
# Argument_contains trigger
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_argument_contains_trigger_matches() -> None:
    entry = FaultPlanEntrySpec(
        target="refund.create",
        trigger=FaultTriggerSpec(argument_contains={"order_id": "order-999"}),
        behaviour=FaultBehaviourSpec(type="http_500"),
    )
    scheduler = make_scheduler(entries=[entry])

    # Matching arguments
    result = scheduler.check("refund.create", call_arguments={"order_id": "order-999", "amount": 10.0})
    assert result is not None


@pytest.mark.unit
def test_argument_contains_trigger_does_not_match() -> None:
    entry = FaultPlanEntrySpec(
        target="refund.create",
        trigger=FaultTriggerSpec(argument_contains={"order_id": "order-999"}),
        behaviour=FaultBehaviourSpec(type="http_500"),
    )
    scheduler = make_scheduler(entries=[entry])

    # Different order ID — must not inject
    result = scheduler.check("refund.create", call_arguments={"order_id": "order-001"})
    assert result is None


@pytest.mark.unit
def test_argument_contains_no_args_does_not_match() -> None:
    entry = FaultPlanEntrySpec(
        target="refund.create",
        trigger=FaultTriggerSpec(argument_contains={"order_id": "order-999"}),
        behaviour=FaultBehaviourSpec(type="http_500"),
    )
    scheduler = make_scheduler(entries=[entry])
    result = scheduler.check("refund.create", call_arguments=None)
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Time-based trigger
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_after_seconds_trigger_fires_when_elapsed_exceeds() -> None:
    entry = FaultPlanEntrySpec(
        target="some.tool",
        trigger=FaultTriggerSpec(after_seconds=30.0),
        behaviour=FaultBehaviourSpec(type="timeout_before_execution"),
    )
    scheduler = make_scheduler(entries=[entry])

    assert scheduler.check("some.tool", elapsed_seconds=10.0) is None
    assert scheduler.check("some.tool", elapsed_seconds=29.9) is None
    result = scheduler.check("some.tool", elapsed_seconds=30.0)
    assert result is not None


# ─────────────────────────────────────────────────────────────────────────────
# Determinism guarantee
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_same_seed_produces_identical_results() -> None:
    """DETERMINISM: same seed + same plan = same schedule, always."""
    entry = make_entry(target="refund.create", invocation=1)

    tools = ["refund.create", "order.lookup", "refund.create"]
    sched_a = make_scheduler(entries=[entry], seed=12345)
    results_a = [sched_a.check(t) is not None for t in tools]

    sched_b = make_scheduler(entries=[entry], seed=12345)
    results_b = [sched_b.check(t) is not None for t in tools]

    assert results_a == results_b


@pytest.mark.unit
def test_different_seeds_may_differ() -> None:
    """Sanity: different seeds with different plans should behave differently."""
    entry_a = make_entry(target="tool.x", invocation=1, fault_type="http_500")
    entry_b = make_entry(target="tool.x", invocation=2, fault_type="http_429")

    sched_a = make_scheduler(entries=[entry_a], seed=1)
    sched_b = make_scheduler(entries=[entry_b], seed=2)

    # First call — entry_a fires, entry_b does not
    result_a = sched_a.check("tool.x")
    result_b = sched_b.check("tool.x")
    assert result_a is not None  # invocation 1 triggers entry_a
    assert result_b is None      # invocation 1 does NOT trigger entry_b (needs 2)


# ─────────────────────────────────────────────────────────────────────────────
# FaultEvent creation
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_make_fault_event_returns_correct_fault_type() -> None:
    entry = make_entry(
        target="refund.create",
        invocation=1,
        fault_type="timeout_after_execution",
        side_effect_committed=True,
    )
    scheduler = make_scheduler(entries=[entry], trial_id="trial-evt-001")
    scheduled = scheduler.check("refund.create")
    assert scheduled is not None

    event = scheduler.make_fault_event(
        scheduled=scheduled,
        tool_name="refund.create",
        tool_call_id="tc-001",
    )
    from arl.core.domain.faults import FaultType
    assert event.fault_type == FaultType.TIMEOUT_AFTER_EXECUTION
    assert event.behaviour.side_effect_committed is True
    assert event.trial_id == "trial-evt-001"
    assert event.target_tool == "refund.create"
    assert event.tool_call_id == "tc-001"
    assert event.injected_at is not None


@pytest.mark.unit
def test_make_fault_event_is_immutable() -> None:
    """FaultEvent must be a frozen Pydantic model."""
    entry = make_entry(fault_type="http_500")
    scheduler = make_scheduler(entries=[entry])
    scheduled = scheduler.check("refund.create")
    assert scheduled is not None

    event = scheduler.make_fault_event(scheduled=scheduled, tool_name="refund.create")
    from pydantic import ValidationError
    with pytest.raises((AttributeError, TypeError, ValidationError)):
        event.fault_type = None  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# derive_trial_fault_seed()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_derive_trial_fault_seed_is_deterministic() -> None:
    s1 = derive_trial_fault_seed(run_seed=999, trial_index=0)
    s2 = derive_trial_fault_seed(run_seed=999, trial_index=0)
    assert s1 == s2


@pytest.mark.unit
def test_derive_trial_fault_seed_differs_by_trial_index() -> None:
    seeds = [derive_trial_fault_seed(run_seed=1, trial_index=i) for i in range(20)]
    # All seeds must be unique
    assert len(set(seeds)) == len(seeds)


@pytest.mark.unit
def test_derive_trial_fault_seed_differs_by_run_seed() -> None:
    for trial_idx in range(5):
        s_a = derive_trial_fault_seed(run_seed=1000, trial_index=trial_idx)
        s_b = derive_trial_fault_seed(run_seed=2000, trial_index=trial_idx)
        assert s_a != s_b


@pytest.mark.unit
def test_derive_trial_fault_seed_returns_non_negative_int() -> None:
    for run_seed in [0, 1, 42, 99999, 2**32 - 1]:
        seed = derive_trial_fault_seed(run_seed=run_seed, trial_index=0)
        assert isinstance(seed, int)
        assert seed >= 0
