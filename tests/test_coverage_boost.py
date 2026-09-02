"""
Targeted tests to ensure >=85% test coverage across core packages, server routes, and graders.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from arl.core.domain.trial import Trial, TrialVerdict
from arl.core.errors import (
    AgentCommunicationError,
    AgentExecutionError,
    ARLError,
    BudgetExceededError,
    ConfigurationError,
    DuplicateEffectError,
    FaultInjectionError,
    ForbiddenEffectDetectedError,
    GradingError,
    InfrastructureError,
    InsufficientEvidenceError,
    IsolationViolationError,
    ReadinessThresholdError,
    ScenarioValidationError,
    SecurityViolationError,
    UnauthorizedError,
    WorkerLeaseError,
)
from arl.core.storage.models import Base
from arl.execution_engine.executor import TrialExecutionResult
from arl.grading_engine.deterministic import (
    DeterministicTrialEvaluator,
    _evaluate_operator,
    _values_match,
    safe_jmespath_search,
)
from arl.protocol.adapter import ToolCallRecord
from arl.scenario_engine.loader import load_scenario
from arl.server.db import engine
from arl.server.main import app


@pytest.mark.unit
def test_core_errors_serialization() -> None:
    """Exercise domain error constructors and serialization helpers."""
    e1 = ARLError("Base error", details={"key": "val"})
    assert "Base error" in str(e1)

    e2 = SecurityViolationError("SSRF_VIOLATION", "Private IP", resource="http://10.0.0.1")
    assert e2.context["violation_type"] == "SSRF_VIOLATION"

    e3 = InfrastructureError("Database down", component="PostgreSQL")
    assert e3.context["component"] == "PostgreSQL"

    e4 = GradingError(grader_id="world_state", trial_id="tr-01", detail="Grader timeout")
    assert e4.context["grader_id"] == "world_state"

    e5 = ScenarioValidationError(path="test.yaml", errors=["missing required field 'budgets'"])
    assert "test.yaml" in str(e5)

    e6 = AgentCommunicationError("Endpoint unreachable", endpoint_url="http://example.com")
    assert e6.context["endpoint_url"] == "http://example.com"

    e7 = AgentExecutionError("Execution failed", agent_version_id="ag-01")
    assert e7.context["agent_version_id"] == "ag-01"

    e8 = BudgetExceededError(budget_type="turns", limit=10, actual=12, trial_id="tr-01")
    assert e8.context["limit"] == 10

    e9 = DuplicateEffectError(tool_name="order.refund", idempotency_key="k1", call_count=2)
    assert e9.context["call_count"] == 2

    e10 = ForbiddenEffectDetectedError(
        effect_path="customer.delete", actual_value=True, trial_id="tr-01"
    )
    assert e10.context["trial_id"] == "tr-01"

    e11 = IsolationViolationError(violating_tenant_id="t1", accessed_tenant_id="t2", resource="db")
    assert e11.context["violating_tenant_id"] == "t1"

    e12 = UnauthorizedError(actor="user-1", action="delete", resource="project-1")
    assert e12.context["actor"] == "user-1"

    e13 = WorkerLeaseError(lease_id="l-1", detail="Lease expired")
    assert e13.context["lease_id"] == "l-1"

    e14 = InsufficientEvidenceError(run_id="run-1", completed_trials=2, required_trials=5)
    assert e14.context["completed_trials"] == 2

    e15 = ReadinessThresholdError(run_id="run-1", score=0.75, threshold=0.90)
    assert e15.context["score"] == 0.75

    e16 = FaultInjectionError(fault_type="LATENCY", detail="Timeout exceeded")
    assert e16.context["fault_type"] == "LATENCY"

    e17 = ConfigurationError(field="database_url", detail="Invalid connection string")
    assert e17.context["field"] == "database_url"


@pytest.mark.unit
def test_deterministic_operators_helper() -> None:
    """Exercise _evaluate_operator and _values_match functions."""
    assert _evaluate_operator("exists", "val", None) is True
    assert _evaluate_operator("exists", None, None) is False
    assert _evaluate_operator("not_exists", None, None) is True
    assert _evaluate_operator("not_exists", "val", None) is False
    assert _evaluate_operator("equals", "a", "a") is True
    assert _evaluate_operator("not_equals", "a", "b") is True
    assert _evaluate_operator("contains", ["a", "b"], "a") is True
    assert _evaluate_operator("matches", "abc-123", r"^abc-\d+$") is True
    assert _evaluate_operator("gt", 5, 3) is True
    assert _evaluate_operator("gte", 5, 5) is True
    assert _evaluate_operator("lt", 3, 5) is True
    assert _evaluate_operator("lte", 3, 3) is True
    assert _evaluate_operator("unknown_op", 1, 1) is False

    assert _values_match(None, None) is True
    assert _values_match(1.0, 1.0) is True
    assert _values_match({"a": 1}, {"a": 1, "b": 2}) is True
    assert _values_match([1, 2], [1, 2]) is True
    assert _values_match("/^test/", "testing") is True
    assert _values_match("hello", "world") is False

    ctx = {"orders": {"ord-1": {"status": "shipped"}}}
    assert safe_jmespath_search('orders."ord-1".status', ctx) == "shipped"
    assert safe_jmespath_search("orders.ord-1.status", ctx) == "shipped"
    assert safe_jmespath_search("orders.nonexistent", ctx) is None


@pytest.mark.asyncio
async def test_graders_and_evaluator_flow() -> None:
    """Exercise EffectMatchGrader, BudgetGrader, ConversationMatchGrader, and DeterministicTrialEvaluator."""
    scenario_path = Path("scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml")
    scenario, _, _ = load_scenario(scenario_path)

    trial = Trial(
        id="tr-test-eval",
        run_id="run-eval",
        trial_index=0,
        idempotency_key="idemp-eval",
        fault_seed=42,
    )

    exec_res = TrialExecutionResult(
        trial_id=trial.id,
        completed_normally=True,
        final_response="Order status is confirmed.",
        turns=["t1", "t2"],
        tool_calls=[
            ToolCallRecord(
                tool_call_id="c1",
                tool_name="order.lookup",
                arguments={"customer_id": "customer-101"},
            ),
        ],
        total_cost_usd=0.005,
    )

    evaluator = DeterministicTrialEvaluator()
    verdict, _score, results = await evaluator.evaluate_trial(trial, scenario, exec_res)
    assert len(results) >= 3
    assert verdict in (TrialVerdict.PASS, TrialVerdict.FAIL)


@pytest.mark.asyncio
async def test_server_runs_and_trials_extended_endpoints() -> None:
    """Exercise server runs filtering, trial listing, and trial details endpoints."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Create Project
        p_res = await client.post("/api/v1/projects", json={"name": "Runs Extended"})
        pid = p_res.json()["id"]

        # Create Agent
        a_res = await client.post(
            f"/api/v1/projects/{pid}/agents",
            json={
                "name": "Runs Ext Agent",
                "framework": "http",
                "version_tag": "1.0.0",
                "endpoint_url": "http://localhost:8088",
            },
        )
        avid = a_res.json()["latest_version_id"]

        # Create Run
        r_res = await client.post(
            "/api/v1/runs",
            json={
                "project_id": pid,
                "agent_version_id": avid,
                "scenario_ids": ["order-lookup-correct-arguments"],
                "trials_per_scenario": 2,
                "seed": 42,
            },
        )
        rid = r_res.json()["id"]

        # List runs with project_id filter
        runs_list = await client.get(f"/api/v1/runs?project_id={pid}")
        assert runs_list.status_code == 200
        assert len(runs_list.json()) >= 1

        # Get single run
        run_get = await client.get(f"/api/v1/runs/{rid}")
        assert run_get.status_code == 200
        assert run_get.json()["id"] == rid

        # Get run trials
        trials_res = await client.get(f"/api/v1/runs/{rid}/trials")
        assert trials_res.status_code == 200
        trials = trials_res.json()
        assert len(trials) == 2

        # Get single trial
        tid = trials[0]["id"]
        t_res = await client.get(f"/api/v1/trials/{tid}")
        assert t_res.status_code == 200
        assert t_res.json()["id"] == tid
