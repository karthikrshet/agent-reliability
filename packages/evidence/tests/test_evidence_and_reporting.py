"""
Unit tests for EvidenceCollector and ReportGenerator.
"""

from __future__ import annotations

import pytest

from arl.core.domain.grading import (
    ReadinessVerdict,
)
from arl.core.domain.tools import ToolCall, ToolResult
from arl.core.domain.trial import WorldStateSnapshot
from arl.evidence.collector import EvidenceCollector
from arl.evidence.reporter import ReportGenerator
from arl.execution_engine.executor import TrialExecutionResult
from arl.grading_engine.aggregator import CategorySummary, RunAggregationResult


@pytest.mark.unit
def test_evidence_collector_hash_chain_and_tamper_detection() -> None:
    collector = EvidenceCollector()

    # Record 3 pieces of evidence
    ev1 = collector.record_evidence(
        trial_id="t1",
        run_id="r1",
        evidence_type="tool_call",
        source_entity_type="ToolCall",
        source_entity_id="tc-1",
        description="Lookup order",
        data={"order_id": "order-1001", "status": "shipped"},
    )
    assert ev1.id in collector.evidence_records

    ev2 = collector.record_evidence(
        trial_id="t1",
        run_id="r1",
        evidence_type="world_state_snapshot",
        source_entity_type="WorldStateSnapshot",
        source_entity_id="snap-1",
        description="Snapshot",
        data={"orders": {"order-1001": {"status": "shipped"}}},
    )
    assert ev2.id in collector.evidence_records

    # Verify initial ledger integrity
    assert collector.verify_ledger_integrity() is True
    assert len(collector.chain_blocks) == 2

    # Query trial evidence
    trial_evs = collector.get_trial_evidence("t1")
    assert len(trial_evs) == 2

    # Simulate adversarial tampering of evidence data
    collector.evidence_records[ev1.id] = ev1.model_copy(
        update={"data": {"order_id": "order-1001", "status": "TAMPERED"}}
    )

    # Tamper detection must fail integrity check
    assert collector.verify_ledger_integrity() is False


@pytest.mark.unit
def test_evidence_collector_from_trial_result() -> None:
    collector = EvidenceCollector()

    tc = ToolCall(
        id="tc-1",
        trial_id="t1",
        agent_turn_id="turn-1",
        sequence_index=0,
        tool_name="order.lookup",
        call_arguments={"id": "1"},
    )
    tr = ToolResult(id="tr-1", tool_call_id="tc-1", trial_id="t1", content={"status": "found"})
    snap = WorldStateSnapshot(
        id="s1",
        trial_id="t1",
        environment_version_id="1.0",
        snapshot_type="final",
        state={"val": 10},
        schema_version="1.0",
        is_schema_valid=True,
    )

    result = TrialExecutionResult(
        trial_id="t1",
        completed_normally=True,
        termination_reason="completed",
        turns=[],
        tool_calls=[tc],
        tool_results=[tr],
        fault_events=[],
        pre_snapshot=None,
        post_snapshot=snap,
        final_response="Found",
    )

    ev_list = collector.collect_from_trial_result("t1", "r1", result)
    assert len(ev_list) == 2  # post snapshot + tool call
    assert collector.verify_ledger_integrity() is True


@pytest.mark.unit
def test_report_generator_json_and_markdown() -> None:
    collector = EvidenceCollector()
    collector.record_evidence(
        trial_id="t1",
        run_id="r-rep",
        evidence_type="tool_call",
        source_entity_type="ToolCall",
        source_entity_id="tc-1",
        description="Call 1",
        data={"k": "v"},
    )

    run_res = RunAggregationResult(
        run_id="r-rep",
        total_trials=10,
        completed_trials=10,
        passed_trials=9,
        failed_trials=1,
        critical_failures=0,
        readiness_verdict=ReadinessVerdict.READY,
        readiness_score=0.90,
        pass_rate=0.90,
        pass_rate_ci_lower=0.86,
        pass_rate_ci_upper=0.98,
        pass_at_1=0.90,
        pass_at_3=0.99,
        pass_at_5=1.0,
        mean_duration_seconds=3.45,
        mean_tokens=450.0,
        total_cost_usd=0.045,
        category_summaries={
            "tool-correctness": CategorySummary(
                category="tool-correctness",
                trials_total=10,
                trials_passed=9,
                pass_rate=0.90,
                ci_lower=0.86,
                ci_upper=0.98,
                mean_score=0.90,
            )
        },
        critical_findings=[],
        verdict_reason="All confidence bounds satisfied with zero critical safety violations.",
    )

    reporter = ReportGenerator(run_result=run_res, evidence_collector=collector)

    # 1. JSON Report
    json_rep = reporter.generate_json_report()
    assert json_rep["schema_version"] == "1.0"
    assert json_rep["run_id"] == "r-rep"
    assert json_rep["verdict"] == "READY"
    assert json_rep["evidence_audit"]["integrity_verified"] is True
    assert json_rep["statistics"]["pass_rate"] == 0.90

    # 2. Markdown Report
    md_rep = reporter.generate_markdown_report()
    assert "# Agent Reliability Lab — Evaluation Audit Report" in md_rep
    assert "🟢 **READY FOR PRODUCTION**" in md_rep
    assert "tool-correctness" in md_rep
    assert "Cryptographic Evidence Chain Verification" in md_rep
    assert "✅ **VERIFIED (Tamper-evident chain valid)**" in md_rep
