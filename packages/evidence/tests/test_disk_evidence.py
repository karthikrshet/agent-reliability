"""
Unit tests for .arl/runs/ disk evidence storage.

Verifies:
- Creation of manifest.json, events.jsonl, faults.json, invariants.json, summary.json, failures.json
- Loading and listing runs from disk
"""

from __future__ import annotations

import tempfile

from arl.core.domain.failure import FailureRecord
from arl.core.domain.faults import FaultResult
from arl.evidence.disk_store import list_runs_on_disk, load_run_from_disk, persist_run_to_disk
from arl.grading_engine.invariants import InvariantResult, InvariantSeverity, InvariantStatus


def test_persist_and_load_run_disk_artifacts() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "run-test-1042"
        manifest = {
            "run_id": run_id,
            "scenario_id": "refund-timeout",
            "seed": 42,
            "verdict": "FAIL",
        }
        events = [
            {"event_id": "ev-1", "type": "tool_call", "tool": "refund.create"},
            {"event_id": "ev-2", "type": "fault_injected", "fault": "timeout_after_effect"},
        ]
        faults = [
            FaultResult(
                fault_id="flt-01",
                injected=True,
                target="refund.create",
                observed_effect="TimeoutError after side effect committed",
                side_effect_committed=True,
                duration_ms=500,
            )
        ]
        invariants = [
            InvariantResult(
                invariant_id="single_refund",
                status=InvariantStatus.FAIL,
                severity=InvariantSeverity.CRITICAL,
                expected=1,
                observed=2,
            )
        ]
        summary = {
            "total_trials": 1,
            "passed_trials": 0,
            "pass_rate": 0.0,
            "critical_invariant_failures": 1,
        }
        failures = [
            FailureRecord(
                failure_id="ARL-FAIL-1042",
                run_id=run_id,
                scenario_id="refund-timeout",
                severity="critical",
                failed_invariants=["single_refund"],
                faults=["timeout_after_effect"],
                summary="Order refunded twice after network response dropped",
            )
        ]

        run_path = persist_run_to_disk(
            run_id=run_id,
            manifest=manifest,
            events=events,
            faults=faults,
            invariants=invariants,
            summary=summary,
            failures=failures,
            base_dir=tmpdir,
        )

        assert (run_path / "manifest.json").exists()
        assert (run_path / "events.jsonl").exists()
        assert (run_path / "faults.json").exists()
        assert (run_path / "invariants.json").exists()
        assert (run_path / "summary.json").exists()
        assert (run_path / "failures.json").exists()

        loaded = load_run_from_disk(run_id, base_dir=tmpdir)
        assert loaded["run_id"] == run_id
        assert loaded["manifest"]["scenario_id"] == "refund-timeout"
        assert len(loaded["events"]) == 2
        assert len(loaded["faults"]) == 1
        assert len(loaded["invariants"]) == 1
        assert loaded["invariants"][0]["invariant_id"] == "single_refund"
        assert len(loaded["failures"]) == 1
        assert loaded["failures"][0]["failure_id"] == "ARL-FAIL-1042"

        runs_list = list_runs_on_disk(base_dir=tmpdir)
        assert runs_list == [run_id]
