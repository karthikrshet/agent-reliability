"""Shared pytest configuration for Agent Reliability Lab test suites."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure all workspace packages, adapters, environments, and apps are on sys.path
_REPO_ROOT = Path(__file__).resolve().parent
for _pattern in ("packages/*/src", "adapters/*/src", "apps/*/src", "environments/*/src"):
    for _src_dir in sorted(_REPO_ROOT.glob(_pattern)):
        if "dashboard" in _src_dir.parts:
            continue
        _str_path = str(_src_dir)
        if _str_path not in sys.path:
            sys.path.insert(0, _str_path)

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def pytest_configure(config: pytest.Config) -> None:
    """Register custom marks to suppress PytestUnknownMarkWarning."""
    config.addinivalue_line("markers", "unit: fast unit tests (no I/O, no network)")
    config.addinivalue_line("markers", "integration: tests requiring external services")
    config.addinivalue_line("markers", "e2e: full end-to-end scenario execution tests")
    config.addinivalue_line("markers", "slow: tests that take more than 1 second")


@pytest.fixture(scope="session", autouse=True)
def ensure_sample_disk_runs() -> None:
    """Ensure deterministic sample runs exist on disk for CLI comparison and SSE streaming tests."""
    from arl.evidence.disk_store import persist_run_to_disk

    runs_dir = _REPO_ROOT / ".arl" / "runs"

    # Create run-2a432c75 if not present
    if not (runs_dir / "run-2a432c75" / "manifest.json").exists():
        persist_run_to_disk(
            run_id="run-2a432c75",
            manifest={
                "run_id": "run-2a432c75",
                "scenario_count": 1,
                "total_trials": 1,
                "reference_only": True,
                "seed": 42,
                "threshold": 0.8,
                "verdict": "INSUFFICIENT_EVIDENCE",
                "evidence_root_hash": "ad11b501abd217fd024f13dbf6eaa547d635a014a36ba0d4a1a51e2bf72b5f47",
            },
            events=[
                {"event_id": "ev-1", "type": "run_started", "run_id": "run-2a432c75"},
                {"event_id": "ev-2", "type": "run_completed", "run_id": "run-2a432c75"},
            ],
            faults=[],
            invariants=[],
            summary={
                "run_id": "run-2a432c75",
                "completed_trials": 1,
                "passed_trials": 1,
                "failed_trials": 0,
                "pass_rate": 1.0,
                "pass_rate_ci_lower": 0.95,
                "pass_rate_ci_upper": 1.0,
                "pass_at_1": 1.0,
                "pass_at_3": None,
                "critical_failures": 0,
                "verdict": "INSUFFICIENT_EVIDENCE",
            },
            failures=[],
            trials=[
                {
                    "trial_id": "trial-2a43-01",
                    "scenario_id": "tool-correctness-01",
                    "verdict": "PASS",
                    "duration_seconds": 0.42,
                }
            ],
            base_dir=_REPO_ROOT / ".arl",
        )

    # Create run-5c30c699 if not present
    if not (runs_dir / "run-5c30c699" / "manifest.json").exists():
        persist_run_to_disk(
            run_id="run-5c30c699",
            manifest={
                "run_id": "run-5c30c699",
                "scenario_count": 1,
                "total_trials": 1,
                "reference_only": True,
                "seed": 43,
                "threshold": 0.8,
                "verdict": "INSUFFICIENT_EVIDENCE",
                "evidence_root_hash": "bc22c612bce328fe135f24ecf7fbb658e746b125b47cb1e5b2b62f3cf83c6f58",
            },
            events=[
                {"event_id": "ev-5c-1", "type": "run_started", "run_id": "run-5c30c699"},
                {"event_id": "ev-5c-2", "type": "run_completed", "run_id": "run-5c30c699"},
            ],
            faults=[],
            invariants=[],
            summary={
                "run_id": "run-5c30c699",
                "completed_trials": 1,
                "passed_trials": 0,
                "failed_trials": 1,
                "pass_rate": 0.0,
                "pass_rate_ci_lower": 0.0,
                "pass_rate_ci_upper": 0.7935,
                "pass_at_1": 0.0,
                "pass_at_3": None,
                "critical_failures": 0,
                "verdict": "INSUFFICIENT_EVIDENCE",
            },
            failures=[],
            trials=[
                {
                    "trial_id": "trial-5c30-01",
                    "scenario_id": "tool-correctness-01",
                    "verdict": "FAIL",
                    "duration_seconds": 0.38,
                }
            ],
            base_dir=_REPO_ROOT / ".arl",
        )
