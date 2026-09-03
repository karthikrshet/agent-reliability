"""
Agent Reliability Lab — Machine-Readable Disk Evidence Store.

Persists trial and run execution evidence to deterministic disk structures:
.arl/
  runs/
    <run-id>/
      manifest.json
      events.jsonl
      faults.json
      invariants.json
      summary.json
      failures.json (optional, written if invariant violations or failures exist)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from arl.core.domain.failure import FailureRecord
from arl.core.domain.faults import FaultResult
from arl.grading_engine.invariants import InvariantResult


def persist_run_to_disk(
    run_id: str,
    manifest: dict[str, Any],
    events: list[dict[str, Any]],
    faults: list[FaultResult],
    invariants: list[InvariantResult],
    summary: dict[str, Any],
    failures: list[FailureRecord] | None = None,
    base_dir: Path | str = ".arl",
) -> Path:
    """Persist structured run artifacts to .arl/runs/<run-id>/."""
    root = Path(base_dir) / "runs" / run_id
    root.mkdir(parents=True, exist_ok=True)

    # 1. manifest.json
    with (root / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)

    # 2. events.jsonl
    with (root / "events.jsonl").open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, default=str) + "\n")

    # 3. faults.json
    with (root / "faults.json").open("w", encoding="utf-8") as f:
        json.dump([flt.model_dump() for flt in faults], f, indent=2, default=str)

    # 4. invariants.json
    with (root / "invariants.json").open("w", encoding="utf-8") as f:
        json.dump([inv.model_dump() for inv in invariants], f, indent=2, default=str)

    # 5. summary.json
    with (root / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    # 6. failures.json (if any)
    if failures:
        with (root / "failures.json").open("w", encoding="utf-8") as f:
            json.dump([fail.model_dump() for fail in failures], f, indent=2, default=str)

    return root


def load_run_from_disk(
    run_id: str,
    base_dir: Path | str = ".arl",
) -> dict[str, Any]:
    """Load all persisted artifacts for a run from disk."""
    root = Path(base_dir) / "runs" / run_id
    if not root.exists():
        raise FileNotFoundError(f"Run directory not found: {root}")

    # Load manifest
    manifest: dict[str, Any] = {}
    if (root / "manifest.json").exists():
        with (root / "manifest.json").open("r", encoding="utf-8") as f:
            manifest = json.load(f)

    # Load events
    events: list[dict[str, Any]] = []
    if (root / "events.jsonl").exists():
        with (root / "events.jsonl").open("r", encoding="utf-8") as f:
            events.extend([json.loads(line) for line in f if line.strip()])

    # Load faults
    faults: list[dict[str, Any]] = []
    if (root / "faults.json").exists():
        with (root / "faults.json").open("r", encoding="utf-8") as f:
            faults = json.load(f)

    # Load invariants
    invariants: list[dict[str, Any]] = []
    if (root / "invariants.json").exists():
        with (root / "invariants.json").open("r", encoding="utf-8") as f:
            invariants = json.load(f)

    # Load summary
    summary: dict[str, Any] = {}
    if (root / "summary.json").exists():
        with (root / "summary.json").open("r", encoding="utf-8") as f:
            summary = json.load(f)

    # Load failures
    failures: list[dict[str, Any]] = []
    if (root / "failures.json").exists():
        with (root / "failures.json").open("r", encoding="utf-8") as f:
            failures = json.load(f)

    return {
        "run_id": run_id,
        "manifest": manifest,
        "events": events,
        "faults": faults,
        "invariants": invariants,
        "summary": summary,
        "failures": failures,
        "directory": str(root),
    }


def list_runs_on_disk(base_dir: Path | str = ".arl") -> list[str]:
    """List all available run IDs on disk sorted by modification time (latest first)."""
    runs_dir = Path(base_dir) / "runs"
    if not runs_dir.exists():
        return []
    run_paths = [p for p in runs_dir.iterdir() if p.is_dir()]
    run_paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [p.name for p in run_paths]
