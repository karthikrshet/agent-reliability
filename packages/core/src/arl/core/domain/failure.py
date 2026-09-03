"""
Agent Reliability Lab — Failure Classification Domain Entity.

Provides stable ARL-FAIL-<id> identifiers, violated invariants linkage,
reproduction parameters, and evidence references.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FailureRecord(BaseModel):
    """Stable failure classification record for autonomous agent failures."""

    model_config = {"frozen": True}

    failure_id: str = Field(
        ...,
        description="Stable failure identifier (e.g. 'ARL-FAIL-1042')",
    )
    run_id: str = Field(..., description="Evaluation run ID")
    scenario_id: str = Field(..., description="Scenario identifier")
    severity: str = Field(default="critical", description="Severity (critical, high, medium, low)")
    failed_invariants: list[str] = Field(
        default_factory=list,
        description="List of invariant IDs that were violated",
    )
    faults: list[str] = Field(
        default_factory=list,
        description="List of injected fault types or fault IDs",
    )
    first_bad_event_id: str | None = Field(
        default=None,
        description="ID of the first event where divergence/violation occurred",
    )
    last_known_good_event_id: str | None = Field(
        default=None,
        description="ID of the last healthy state event prior to fault or failure",
    )
    reproduction_command: str = Field(
        default="",
        description="CLI command to deterministically reproduce this failure",
    )
    reproduction_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Seed, scenario version, and parameters needed for deterministic rerun",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="Cryptographic evidence IDs documenting this failure",
    )
    summary: str = Field(default="", description="Detailed human-readable failure diagnosis")
