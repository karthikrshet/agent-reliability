"""
Unit tests for ToolProxy with fault injection.
"""

from __future__ import annotations

import pytest

from arl.environments.customer_support.environment import CustomerSupportEnvironment
from arl.execution_engine.proxy import ToolProxy
from arl.fault_engine.scheduler import FaultScheduler
from arl.scenario_engine.schema import (
    FaultBehaviourSpec,
    FaultPlanEntrySpec,
    FaultTriggerSpec,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_proxy_executes_tool_normally() -> None:
    env = CustomerSupportEnvironment(seed=42)
    proxy = ToolProxy(environment=env, tool_definitions=env.tools)

    result, fault_event = await proxy.execute(
        tool_call_id="call-01",
        tool_name="order.lookup",
        arguments={"customer_id": "customer-101"},
    )
    assert fault_event is None
    assert not result.is_error
    assert result.content["count"] >= 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_proxy_injects_http_500_fault() -> None:
    env = CustomerSupportEnvironment(seed=42)
    fault_entry = FaultPlanEntrySpec(
        target="order.lookup",
        trigger=FaultTriggerSpec(invocation=1),
        behaviour=FaultBehaviourSpec(type="http_500"),
    )
    scheduler = FaultScheduler(
        fault_plan_entries=[fault_entry],
        trial_fault_seed=42,
        trial_id="trial-test",
    )
    proxy = ToolProxy(environment=env, tool_definitions=env.tools, fault_scheduler=scheduler)

    result, fault_event = await proxy.execute(
        tool_call_id="call-02",
        tool_name="order.lookup",
        arguments={"customer_id": "customer-101"},
    )
    assert fault_event is not None
    assert fault_event.fault_type.value == "http_500"
    assert result.is_error
    assert result.error_code == "HTTP500"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_proxy_timeout_after_execution_commits_side_effect() -> None:
    env = CustomerSupportEnvironment(seed=42)
    fault_entry = FaultPlanEntrySpec(
        target="refund.create",
        trigger=FaultTriggerSpec(invocation=1),
        behaviour=FaultBehaviourSpec(type="timeout_after_execution", side_effect_committed=True),
    )
    scheduler = FaultScheduler(
        fault_plan_entries=[fault_entry],
        trial_fault_seed=42,
        trial_id="trial-test",
    )
    proxy = ToolProxy(environment=env, tool_definitions=env.tools, fault_scheduler=scheduler)

    result, fault_event = await proxy.execute(
        tool_call_id="call-03",
        tool_name="refund.create",
        arguments={"order_id": "order-1042", "amount_usd": 49.99},
    )
    assert fault_event is not None
    assert result.is_error
    assert result.error_code == "TimeoutError"
    assert result.content.get("side_effect_uncertain") is True

    # Critical check: the side effect was indeed committed in the world state!
    assert len(env.export_world_state()["refunds"]) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_proxy_all_fault_behaviours() -> None:
    env = CustomerSupportEnvironment(seed=42)

    # 1. http_503 with custom response body
    p_503 = ToolProxy(
        environment=env,
        tool_definitions=env.tools,
        fault_scheduler=FaultScheduler(
            fault_plan_entries=[
                FaultPlanEntrySpec(
                    target="order.lookup",
                    trigger=FaultTriggerSpec(invocation=1),
                    behaviour=FaultBehaviourSpec(type="http_503", response_body="Maintenance"),
                )
            ],
            trial_fault_seed=1,
            trial_id="t",
        ),
    )
    res_503, _ = await p_503.execute(
        tool_call_id="c1", tool_name="order.lookup", arguments={"customer_id": "c1"}
    )
    assert res_503.error_code == "HTTP503"

    # 2. http_429 rate limit
    p_429 = ToolProxy(
        environment=env,
        tool_definitions=env.tools,
        fault_scheduler=FaultScheduler(
            fault_plan_entries=[
                FaultPlanEntrySpec(
                    target="order.lookup",
                    trigger=FaultTriggerSpec(invocation=1),
                    behaviour=FaultBehaviourSpec(type="http_429", retry_after_seconds=3),
                )
            ],
            trial_fault_seed=2,
            trial_id="t",
        ),
    )
    res_429, _ = await p_429.execute(
        tool_call_id="c2", tool_name="order.lookup", arguments={"customer_id": "c1"}
    )
    assert res_429.error_code == "HTTP429"

    # 3. dns_failure & connection_refused & dropped_response
    for ftype, err_code in [
        ("dns_failure", "DNSLookupFailure"),
        ("connection_refused", "ConnectionRefused"),
        ("dropped_response", "ConnectionReset"),
        ("timeout_before_execution", "TimeoutError"),
    ]:
        p = ToolProxy(
            environment=env,
            tool_definitions=env.tools,
            fault_scheduler=FaultScheduler(
                fault_plan_entries=[
                    FaultPlanEntrySpec(
                        target="order.lookup",
                        trigger=FaultTriggerSpec(invocation=1),
                        behaviour=FaultBehaviourSpec(type=ftype),
                    )
                ],
                trial_fault_seed=3,
                trial_id="t",
            ),
        )
        res, _ = await p.execute(
            tool_call_id="c3", tool_name="order.lookup", arguments={"customer_id": "c1"}
        )
        assert res.error_code == err_code

    # 4. malformed_json & schema_invalid_result & stale_result & partial_success
    for ftype, is_err in [
        ("malformed_json", True),
        ("schema_invalid_result", False),
        ("stale_result", False),
        ("partial_success", False),
    ]:
        p = ToolProxy(
            environment=env,
            tool_definitions=env.tools,
            fault_scheduler=FaultScheduler(
                fault_plan_entries=[
                    FaultPlanEntrySpec(
                        target="order.lookup",
                        trigger=FaultTriggerSpec(invocation=1),
                        behaviour=FaultBehaviourSpec(type=ftype, response_body='{"test": 1}'),
                    )
                ],
                trial_fault_seed=4,
                trial_id="t",
            ),
        )
        res, _ = await p.execute(
            tool_call_id="c4", tool_name="order.lookup", arguments={"customer_id": "c1"}
        )
        assert res.is_error == is_err


@pytest.mark.asyncio
async def test_proxy_new_fault_types_and_sanitization() -> None:
    env = CustomerSupportEnvironment(seed=42)

    # 1. empty_response
    p_empty = ToolProxy(
        environment=env,
        tool_definitions=env.tools,
        fault_scheduler=FaultScheduler(
            fault_plan_entries=[
                FaultPlanEntrySpec(
                    target="order.lookup",
                    trigger=FaultTriggerSpec(invocation=1),
                    behaviour=FaultBehaviourSpec(type="empty_response"),
                )
            ],
            trial_fault_seed=5,
            trial_id="t5",
        ),
    )
    res_empty, _ = await p_empty.execute(
        tool_call_id="c_empty", tool_name="order.lookup", arguments={"customer_id": "customer-101"}
    )
    assert res_empty.content == {}
    assert len(p_empty.recorded_fault_results) == 1
    assert p_empty.recorded_fault_results[0].target == "order.lookup"

    # 2. duplicate_response
    p_dup = ToolProxy(
        environment=env,
        tool_definitions=env.tools,
        fault_scheduler=FaultScheduler(
            fault_plan_entries=[
                FaultPlanEntrySpec(
                    target="order.lookup",
                    trigger=FaultTriggerSpec(invocation=1),
                    behaviour=FaultBehaviourSpec(type="duplicate_response"),
                )
            ],
            trial_fault_seed=6,
            trial_id="t6",
        ),
    )
    res_dup, _ = await p_dup.execute(
        tool_call_id="c_dup", tool_name="order.lookup", arguments={"customer_id": "customer-101"}
    )
    assert res_dup.content.get("is_duplicate") is True
    assert "duplicate_payload" in res_dup.content

    # 3. secret redaction in sanitize_payload
    from arl.execution_engine.proxy import sanitize_payload

    raw_args = {
        "customer_id": "customer-101",
        "api_key": "sk-secret-12345",
        "authorization": "Bearer token-abc",
        "nested": {"cookie": "session=xyz", "token": "tok-999"},
    }
    sanitized = sanitize_payload(raw_args)
    assert sanitized["customer_id"] == "customer-101"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["authorization"] == "[REDACTED]"
    assert sanitized["nested"]["cookie"] == "[REDACTED]"
    assert sanitized["nested"]["token"] == "[REDACTED]"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_proxy_unknown_tool_and_schema_validation() -> None:
    env = CustomerSupportEnvironment(seed=42)
    proxy = ToolProxy(environment=env, tool_definitions=env.tools)

    # 1. Unknown tool
    res_unknown, _ = await proxy.execute(
        tool_call_id="c_unk",
        tool_name="nonexistent.tool",
        arguments={},
    )
    assert res_unknown.is_error is True
    assert res_unknown.error_code == "UnknownToolError"

    # 2. Invalid argument types
    res_bad_args, _ = await proxy.execute(
        tool_call_id="c_bad",
        tool_name="order.lookup",
        arguments="not-a-dict",  # type: ignore[arg-type]
    )
    assert res_bad_args.is_error is True
    assert res_bad_args.error_code == "ValidationError"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_proxy_empty_and_corrupted_response_faults() -> None:
    env = CustomerSupportEnvironment(seed=42)

    # 1. empty_response
    p_empty = ToolProxy(
        environment=env,
        tool_definitions=env.tools,
        fault_scheduler=FaultScheduler(
            fault_plan_entries=[
                FaultPlanEntrySpec(
                    target="order.lookup",
                    trigger=FaultTriggerSpec(invocation=1),
                    behaviour=FaultBehaviourSpec(type="empty_response"),
                )
            ],
            trial_fault_seed=7,
            trial_id="t7",
        ),
    )
    res_empty, _ = await p_empty.execute(
        tool_call_id="c_empty", tool_name="order.lookup", arguments={"customer_id": "customer-101"}
    )
    assert res_empty.content == {}

    # 2. malformed_response
    p_corrupt = ToolProxy(
        environment=env,
        tool_definitions=env.tools,
        fault_scheduler=FaultScheduler(
            fault_plan_entries=[
                FaultPlanEntrySpec(
                    target="order.lookup",
                    trigger=FaultTriggerSpec(invocation=1),
                    behaviour=FaultBehaviourSpec(type="malformed_response"),
                )
            ],
            trial_fault_seed=8,
            trial_id="t8",
        ),
    )
    res_corrupt, _ = await p_corrupt.execute(
        tool_call_id="c_corrupt",
        tool_name="order.lookup",
        arguments={"customer_id": "customer-101"},
    )
    assert "raw_output" in res_corrupt.content
    assert res_corrupt.error_code == "MalformedJSON"
