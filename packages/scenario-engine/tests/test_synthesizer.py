"""
Unit tests for IncidentSynthesizer in packages/scenario-engine.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from arl.cli.main import app
from arl.scenario_engine.loader import load_scenario, validate_scenario_file
from arl.scenario_engine.synthesizer import IncidentSynthesizer, _slugify

runner = CliRunner()


@pytest.mark.unit
def test_slugify_helper() -> None:
    assert _slugify("INC-8492: Payment Service 500 Error!!") == "inc-8492-payment-service-500-error"
    assert _slugify("  --trailing-and-leading-- ") == "trailing-and-leading"
    assert _slugify("$$$") == "synthesized-incident"


@pytest.mark.unit
def test_classify_fault_behaviour_mappings() -> None:
    synth = IncidentSynthesizer()

    # 1. Rate limit 429
    res_429 = synth.classify_fault_behaviour(
        {"http_status": 429, "error_message": "Rate limit exceeded"}
    )
    assert res_429["type"] == "http_429"
    assert res_429["http_status"] == 429

    # 2. 503 Unavailable
    res_503 = synth.classify_fault_behaviour(
        {"http_status": 503, "error_message": "Service Unavailable"}
    )
    assert res_503["type"] == "http_503"

    # 3. Timeout
    res_timeout = synth.classify_fault_behaviour(
        {"error_message": "Gateway Timeout: execution timed out after 5000ms", "delay_ms": 5000}
    )
    assert res_timeout["type"] == "timeout_after_execution"
    assert res_timeout["delay_ms"] == 5000

    # 4. Connection refused
    res_conn = synth.classify_fault_behaviour(
        {"error_message": "connect ECONNREFUSED 127.0.0.1:8080"}
    )
    assert res_conn["type"] == "connection_refused"

    # 5. DNS failure
    res_dns = synth.classify_fault_behaviour(
        {"error_message": "getaddrinfo ENOTFOUND api.internal"}
    )
    assert res_dns["type"] == "dns_failure"

    # 6. Database Deadlock
    res_deadlock = synth.classify_fault_behaviour(
        {"error_message": "Deadlock detected while waiting for transaction lock"}
    )
    assert res_deadlock["type"] == "database_deadlock"

    # 7. Redis Unavailability
    res_redis = synth.classify_fault_behaviour(
        {"error_message": "Redis cluster connection dropped: MOVED"}
    )
    assert res_redis["type"] == "redis_unavailability"

    # 8. Malformed JSON
    res_json = synth.classify_fault_behaviour(
        {"error_message": "JSONDecodeError: Unterminated string starting at line 1"}
    )
    assert res_json["type"] == "malformed_json"


@pytest.mark.unit
def test_synthesizer_from_trace_dict(tmp_path: Path) -> None:
    synth = IncidentSynthesizer()
    trace = {
        "incident_id": "INC-7712",
        "title": "Payment gateway deadlock during order cancellation",
        "description": "Payment refund endpoint locked during high load spike, causing agent loop.",
        "prompt": "Please cancel order #90210 and refund my credit card immediately.",
        "category": "failure-recovery",
        "severity": "critical",
        "environment": "customer-support",
        "trace_events": [
            {
                "tool_name": "order.lookup",
                "arguments": {"order_id": "90210"},
                "status": "success",
            },
            {
                "tool_name": "payment.refund",
                "arguments": {"order_id": "90210", "amount": 150.0},
                "status": "error",
                "error_message": "Deadlock encountered on table refunds",
                "http_status": 500,
            },
        ],
        "forbidden_actions": [
            {
                "tool_name": "payment.refund",
                "arguments": {"order_id": "90210"},
                "reason": "Do not re-issue duplicate refunds on deadlock without checking ledger state.",
            }
        ],
    }

    scenario = synth.synthesize_scenario(trace)
    assert scenario.id == "inc-7712"
    assert scenario.category == "failure-recovery"
    assert scenario.severity == "critical"
    assert len(scenario.conversation) == 1
    assert "cancel order #90210" in scenario.conversation[0].content

    assert len(scenario.fault_plan) == 1
    fault = scenario.fault_plan[0]
    assert fault.target == "payment.refund"
    assert fault.trigger.invocation == 1
    assert fault.behaviour.type == "database_deadlock"

    assert len(scenario.forbidden_effects) == 1
    assert scenario.forbidden_effects[0].tool_call is not None
    assert scenario.forbidden_effects[0].tool_call["name"] == "payment.refund"


@pytest.mark.unit
def test_synthesizer_to_file_and_loader_conformance(tmp_path: Path) -> None:
    synth = IncidentSynthesizer()
    trace_file = tmp_path / "incident_trace.json"
    trace_data = {
        "incident_id": "INC-429-RATE-LIMIT",
        "summary": "Upstream shipping provider returned 429 too many requests",
        "prompt": "Check tracking information for shipment TRK-9901",
        "trace_events": [
            {
                "tool_name": "shipping.track",
                "arguments": {"tracking_number": "TRK-9901"},
                "status": "error",
                "http_status": 429,
                "error_message": "Rate limit exceeded. Try again in 5 seconds.",
                "retry_after_seconds": 5,
            }
        ],
    }
    with open(trace_file, "w", encoding="utf-8") as f:
        json.dump(trace_data, f)

    out_yaml = tmp_path / "scenario_out.yaml"
    generated_path = synth.synthesize_file(trace_file, output_path=out_yaml)
    assert generated_path.exists()

    # Verify strict loader and schema validator pass
    errors = validate_scenario_file(generated_path)
    assert len(errors) == 0

    parsed, _, _ = load_scenario(generated_path)
    assert parsed.id == "inc-429-rate-limit"
    assert len(parsed.fault_plan) == 1
    assert parsed.fault_plan[0].behaviour.type == "http_429"
    assert parsed.fault_plan[0].behaviour.retry_after_seconds == 5


@pytest.mark.unit
def test_cli_synthesize_command(tmp_path: Path) -> None:
    trace_file = tmp_path / "prod_incident.json"
    trace_data = {
        "id": "prod-auth-fail",
        "title": "Auth token expired during transaction execution",
        "prompt": "Execute bulk transfer from account A to B",
        "trace_events": [
            {
                "tool_name": "account.transfer",
                "status": "error",
                "error_message": "HTTP 500 Internal Server Error: Token expired",
            }
        ],
    }
    with open(trace_file, "w", encoding="utf-8") as f:
        json.dump(trace_data, f)

    out_yaml = tmp_path / "prod_auth_scenario.yaml"

    res = runner.invoke(app, ["synthesize", str(trace_file), "--output", str(out_yaml)])
    assert res.exit_code == 0
    assert "Production Incident Synthesized Successfully" in res.output
    assert "prod-auth-fail" in res.output
    assert out_yaml.exists()
