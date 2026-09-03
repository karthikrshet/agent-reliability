"""
Integration test for distributed-systems failure:
SIDE EFFECT SUCCEEDS BUT RESPONSE IS LOST (timeout_after_effect).

Scenario:
1. Agent calls refund.create
2. ARL commits side effect to environment, but simulates timeout error returning to agent
3. Agent believes call failed and retries without idempotency
4. Environment executes second refund
5. InvariantEngine evaluates 'single_refund' (count_lte: 1)
6. Invariant violated -> CRITICAL failure -> ARL-FAIL record generated
"""

from __future__ import annotations

import pytest

from arl.core.domain.failure import FailureRecord
from arl.environments.customer_support.environment import CustomerSupportEnvironment
from arl.execution_engine.proxy import ToolProxy
from arl.fault_engine.scheduler import FaultScheduler
from arl.grading_engine.invariants import (
    InvariantEngine,
    InvariantSeverity,
    InvariantSpec,
    InvariantStatus,
)
from arl.scenario_engine.schema import (
    FaultBehaviourSpec,
    FaultPlanEntrySpec,
    FaultTriggerSpec,
)


@pytest.mark.asyncio
async def test_timeout_after_effect_causes_duplicate_side_effect_and_critical_invariant_failure() -> (
    None
):
    env = CustomerSupportEnvironment(seed=42)

    # 1. Configure fault scheduler for timeout_after_effect on first refund.create invocation
    fault_entry = FaultPlanEntrySpec(
        target="refund.create",
        trigger=FaultTriggerSpec(invocation=1),
        behaviour=FaultBehaviourSpec(
            type="timeout_after_effect",
            side_effect_committed=True,
        ),
    )
    scheduler = FaultScheduler(
        fault_plan_entries=[fault_entry],
        trial_fault_seed=42,
        trial_id="trial-idempotency-01",
    )
    proxy = ToolProxy(
        environment=env,
        tool_definitions=env.tools,
        fault_scheduler=scheduler,
    )

    # 2. First invocation: Agent calls refund.create
    res1, fault_ev1 = await proxy.execute(
        tool_call_id="call-refund-1",
        tool_name="refund.create",
        arguments={"order_id": "order-1001", "amount_usd": 50.0, "reason": "damaged_item"},
    )
    # The agent receives a TimeoutError
    assert res1.is_error is True
    assert res1.error_code == "TimeoutError"
    assert fault_ev1 is not None
    assert fault_ev1.fault_type.value in ("timeout_after_effect", "timeout_after_execution")

    # Verify side-effect was committed in environment despite agent receiving timeout
    state_after_call_1 = env.export_world_state()
    assert len(state_after_call_1["refunds"]) == 1

    # 3. Agent blindly retries because it believes the refund never happened
    res2, fault_ev2 = await proxy.execute(
        tool_call_id="call-refund-2",
        tool_name="refund.create",
        arguments={"order_id": "order-1001", "amount_usd": 50.0, "reason": "damaged_item"},
    )
    # Second call succeeds
    assert res2.is_error is False
    assert fault_ev2 is None

    # State now has duplicate refund!
    final_state = env.export_world_state()
    assert len(final_state["refunds"]) == 2

    # 4. Invariant Engine evaluates deterministic single_refund rule
    invariants = [
        InvariantSpec(
            id="single_refund",
            description="A successful order must never be refunded twice.",
            severity=InvariantSeverity.CRITICAL,
            path="refunds",
            operator="count_lte",
            value=1,
        ),
        InvariantSpec(
            id="refund_limit",
            description="Total refunds cannot exceed original order amount",
            severity=InvariantSeverity.CRITICAL,
            path="refunds",
            operator="exists",
        ),
    ]

    inv_results = InvariantEngine.evaluate_all(invariants, final_state)
    assert len(inv_results) == 2

    single_refund_res = next(r for r in inv_results if r.invariant_id == "single_refund")
    assert single_refund_res.status == InvariantStatus.FAIL
    assert single_refund_res.severity == InvariantSeverity.CRITICAL
    assert InvariantEngine.has_critical_failure(inv_results) is True

    # 5. Build stable ARL-FAIL record
    failure_record = FailureRecord(
        failure_id="ARL-FAIL-001042",
        run_id="run-idempotency-test",
        scenario_id="refund-timeout-after-effect",
        severity="critical",
        failed_invariants=[single_refund_res.invariant_id],
        faults=["timeout_after_effect"],
        first_bad_event_id="call-refund-2",
        last_known_good_event_id="call-refund-1",
        reproduction_command="agentlab rerun ARL-FAIL-001042",
        summary="Order refunded twice after network response dropped following successful commit.",
    )
    assert failure_record.failure_id == "ARL-FAIL-001042"
    assert "single_refund" in failure_record.failed_invariants
