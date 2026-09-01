"""
Agent Reliability Lab — Audit Report Generator.

Generates production-grade evaluation reports in structured JSON and human-readable
GitHub Flavored Markdown format with full statistical confidence intervals, category breakdowns,
critical findings, and cryptographic evidence hashes.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from arl.core.domain.grading import ReadinessVerdict
from arl.evidence.collector import EvidenceCollector
from arl.grading_engine.aggregator import RunAggregationResult


class ReportGenerator:
    """Generates comprehensive JSON and Markdown audit evaluation reports."""

    def __init__(
        self, run_result: RunAggregationResult, evidence_collector: EvidenceCollector | None = None
    ) -> None:
        self.res = run_result
        self.collector = evidence_collector

    def generate_json_report(self) -> dict[str, Any]:
        """Generate structured JSON report payload."""
        ledger_valid = self.collector.verify_ledger_integrity() if self.collector else None
        chain_hash = self.collector.current_hash if self.collector else None

        return {
            "schema_version": "1.0",
            "run_id": self.res.run_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "verdict": self.res.readiness_verdict.value,
            "readiness_score": self.res.readiness_score,
            "verdict_reason": self.res.verdict_reason,
            "statistics": {
                "total_trials": self.res.total_trials,
                "completed_trials": self.res.completed_trials,
                "passed_trials": self.res.passed_trials,
                "failed_trials": self.res.failed_trials,
                "critical_failures": self.res.critical_failures,
                "pass_rate": self.res.pass_rate,
                "pass_rate_ci_95": [self.res.pass_rate_ci_lower, self.res.pass_rate_ci_upper],
                "pass_at_1": self.res.pass_at_1,
                "pass_at_3": self.res.pass_at_3,
                "pass_at_5": self.res.pass_at_5,
            },
            "performance": {
                "mean_duration_seconds": self.res.mean_duration_seconds,
                "mean_tokens": self.res.mean_tokens,
                "total_cost_usd": self.res.total_cost_usd,
            },
            "category_summaries": {
                k: v.model_dump() for k, v in self.res.category_summaries.items()
            },
            "critical_findings": self.res.critical_findings,
            "evidence_audit": {
                "chain_hash": chain_hash,
                "integrity_verified": ledger_valid,
                "total_evidence_blocks": len(self.collector.chain_blocks) if self.collector else 0,
            },
        }

    def generate_markdown_report(self) -> str:
        """Generate formatted GitHub Flavored Markdown audit report."""
        v = self.res.readiness_verdict
        if v == ReadinessVerdict.READY:
            badge = "🟢 **READY FOR PRODUCTION**"
        elif v == ReadinessVerdict.NOT_READY:
            badge = "🔴 **NOT READY FOR PRODUCTION**"
        else:
            badge = "🟡 **INSUFFICIENT EVIDENCE**"

        lines = [
            "# Agent Reliability Lab — Evaluation Audit Report",
            "",
            f"**Evaluation Run ID**: `{self.res.run_id}`  ",
            f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%SZ')}  ",
            f"**Readiness Verdict**: {badge}  ",
            f"**Readiness Score**: `{self.res.readiness_score:.2%}`  ",
            "",
            "> [!IMPORTANT]",
            "> **Verdict Decision Rationale**:  ",
            f"> {self.res.verdict_reason}",
            "",
            "---",
            "",
            "## 1. Statistical Summary & Confidence Intervals",
            "",
            "| Metric | Value | 95% Confidence Interval / Detail |",
            "| :--- | :--- | :--- |",
            f"| **Overall Pass Rate** | **{self.res.pass_rate:.1%}** | `[{self.res.pass_rate_ci_lower:.1%}, {self.res.pass_rate_ci_upper:.1%}]` (Wilson Score) |",
            f"| **Pass@1** | **{self.res.pass_at_1:.3f}** | Unbiased binomial estimator |",
        ]

        if self.res.pass_at_3 is not None:
            lines.append(
                f"| **Pass@3** | **{self.res.pass_at_3:.3f}** | Probability of ≥1 pass in 3 trials |"
            )
        if self.res.pass_at_5 is not None:
            lines.append(
                f"| **Pass@5** | **{self.res.pass_at_5:.3f}** | Probability of ≥1 pass in 5 trials |"
            )

        lines.extend(
            [
                f"| **Completed Trials** | {self.res.completed_trials} / {self.res.total_trials} | {self.res.passed_trials} passed, {self.res.failed_trials} failed |",
                f"| **Critical Failures** | **{self.res.critical_failures}** | Safety / isolation / forbidden effects |",
                f"| **Mean Latency** | {self.res.mean_duration_seconds:.2f}s | Average duration per trial |",
                f"| **Mean Token Usage** | {self.res.mean_tokens:.0f} tokens | Average prompt + completion tokens |",
                f"| **Total Cost** | ${self.res.total_cost_usd:.4f} USD | Evaluated agent execution cost |",
                "",
                "---",
                "",
                "## 2. Evaluation Category Breakdown",
                "",
                "| Category | Trials | Passed | Pass Rate | 95% Wilson CI | Mean Score |",
                "| :--- | :--- | :--- | :--- | :--- | :--- |",
            ]
        )

        for cat, summ in self.res.category_summaries.items():
            lines.append(
                f"| `{cat}` | {summ.trials_total} | {summ.trials_passed} | {summ.pass_rate:.1%} | `[{summ.ci_lower:.1%}, {summ.ci_upper:.1%}]` | {summ.mean_score:.2f} |"
            )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 3. Critical Safety & Integrity Findings",
                "",
            ]
        )

        if not self.res.critical_findings:
            lines.extend(
                [
                    "> [!TIP]",
                    "> Zero critical safety findings, forbidden side effects, or tenant isolation violations detected across all completed trials.",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "> [!CAUTION]",
                    f"> The following {len(self.res.critical_findings)} critical finding(s) were recorded. Critical findings trigger an automatic safety veto.",
                    "",
                    "| Trial ID | Category | Severity | Description |",
                    "| :--- | :--- | :--- | :--- |",
                ]
            )
            lines.extend(
                f"| `{cf.get('trial_id')}` | `{cf.get('category')}` | **{str(cf.get('severity', 'high')).upper()}** | {cf.get('detail')} |"
                for cf in self.res.critical_findings
            )
            lines.append("")

        if self.collector:
            ledger_ok = self.collector.verify_ledger_integrity()
            lines.extend(
                [
                    "---",
                    "",
                    "## 4. Cryptographic Evidence Chain Verification",
                    "",
                    f"- **Ledger Chain Hash**: `{self.collector.current_hash}`",
                    f"- **Total Evidence Blocks**: `{len(self.collector.chain_blocks)}`",
                    f"- **Cryptographic Integrity**: {'✅ **VERIFIED (Tamper-evident chain valid)**' if ledger_ok else '❌ **FAILED INTEGRITY CHECK**'}",
                    "",
                ]
            )

        return "\n".join(lines)
