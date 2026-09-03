"""
CLI tests for replay, rerun, report, and CI regression gating (--gate).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from arl.cli.main import app
from arl.evidence.disk_store import persist_run_to_disk

runner = CliRunner()


@pytest.fixture
def populated_arl_run(tmp_path: Path) -> str:
    """Populate a test run directory under tmp_path/.arl/runs/."""
    run_id = "run-sample-gate-01"
    manifest = {
        "run_id": run_id,
        "scenario_count": 1,
        "total_trials": 1,
        "reference_only": True,
        "seed": 42,
        "threshold": 0.80,
        "verdict": "NON_PRODUCTION_REFERENCE",
        "evidence_root_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }
    events = [
        {
            "event_id": "ev-1",
            "event_type": "tool_call",
            "component": "tool_proxy",
            "tool_name": "order.lookup",
        },
    ]
    summary = {
        "run_id": run_id,
        "completed_trials": 1,
        "passed_trials": 1,
        "failed_trials": 0,
        "pass_rate": 1.0,
        "pass_rate_ci_lower": 0.95,
        "pass_rate_ci_upper": 1.0,
        "critical_failures": 0,
        "verdict": "NON_PRODUCTION_REFERENCE",
    }
    persist_run_to_disk(
        run_id=run_id,
        manifest=manifest,
        events=events,
        faults=[],
        invariants=[],
        summary=summary,
        failures=[],
        base_dir=tmp_path / ".arl",
    )
    return run_id


def test_cli_test_command_executes_scenarios() -> None:
    yaml_path = Path("scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml")
    if yaml_path.exists():
        res = runner.invoke(
            app, ["test", str(yaml_path), "--reference-agent", "--trials", "1", "--seed", "42"]
        )
        assert res.exit_code == 0
        assert "Execution Progress" in res.output
        assert "Artifacts Persisted:" in res.output


def test_cli_test_gate_passes_on_zero_critical_failures() -> None:
    yaml_path = Path("scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml")
    if yaml_path.exists():
        res = runner.invoke(
            app,
            [
                "test",
                str(yaml_path),
                "--gate",
                "--reference-agent",
                "--trials",
                "1",
                "--seed",
                "42",
            ],
        )
        assert res.exit_code == 0
        assert "CI RELIABILITY GATE PASSED" in res.output


def test_cli_report_command_formats() -> None:
    yaml_path = Path("scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml")
    if yaml_path.exists():
        # First execute a test run to create artifacts on disk
        runner.invoke(
            app, ["test", str(yaml_path), "--reference-agent", "--trials", "1", "--seed", "42"]
        )

        # Test report latest in text format
        res_text = runner.invoke(app, ["report", "latest"])
        assert res_text.exit_code == 0
        assert "ARL Report:" in res_text.output

        # Test report in markdown format
        res_md = runner.invoke(app, ["report", "latest", "--format", "markdown"])
        assert res_md.exit_code == 0
        assert "# ARL Evaluation Report" in res_md.output

        # Test report in json format
        res_json = runner.invoke(app, ["report", "latest", "--format", "json"])
        assert res_json.exit_code == 0
        assert '"run_id":' in res_json.output


def test_cli_replay_and_rerun_commands() -> None:
    yaml_path = Path("scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml")
    if yaml_path.exists():
        # Execute test run to populate .arl/runs/
        runner.invoke(
            app, ["test", str(yaml_path), "--reference-agent", "--trials", "1", "--seed", "42"]
        )

        from arl.evidence.disk_store import list_runs_on_disk

        runs = list_runs_on_disk()
        assert len(runs) > 0
        latest_run_id = runs[0]

        # Replay the run
        replay_res = runner.invoke(app, ["replay", latest_run_id])
        assert replay_res.exit_code == 0
        assert "ARL Evidence Replay" in replay_res.output

        # Rerun the run
        rerun_res = runner.invoke(app, ["rerun", latest_run_id])
        assert rerun_res.exit_code == 0
        assert "Deterministic Scenario Rerun" in rerun_res.output


def test_cli_verify_command() -> None:
    res = runner.invoke(app, ["verify"])
    assert res.exit_code == 0
    assert "CRYPTOGRAPHIC INTEGRITY VERIFIED" in res.output


def test_cli_replay_failure_by_identifier() -> None:
    from arl.core.domain.failure import FailureRecord
    from arl.evidence.disk_store import persist_run_to_disk

    fail_id = "ARL-FAIL-9999"
    run_id = "run-sample-with-failure"
    fail_record = FailureRecord(
        failure_id=fail_id,
        run_id=run_id,
        scenario_id="sc-fail-01",
        severity="critical",
        failed_invariants=["inv-duplicate-refund"],
        faults=["timeout_after_effect"],
        first_bad_event_id="ev-101",
        reproduction_command=f"agentlab rerun {fail_id}",
        reproduction_metadata={"seed": 42},
        summary="Trial failed with duplicate refund",
    )
    persist_run_to_disk(
        run_id=run_id,
        manifest={"run_id": run_id, "scenario_count": 1},
        events=[
            {
                "event_id": "ev-101",
                "event_type": "fault_injected",
                "component": "tool_proxy",
                "fault_type": "timeout",
            }
        ],
        faults=[],
        invariants=[],
        summary={"run_id": run_id, "pass_rate": 0.0},
        failures=[fail_record],
    )

    # Replay by failure ID
    res = runner.invoke(app, ["replay", fail_id])
    assert res.exit_code == 0
    assert "CRITICAL FAILURE RECORD: ARL-FAIL-9999" in res.output
    assert "inv-duplicate-refund" in res.output
