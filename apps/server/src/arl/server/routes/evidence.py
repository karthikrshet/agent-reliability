"""
Evidence ledger and evaluation audit report API router.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arl.core.domain.trial import Trial, TrialVerdict
from arl.core.storage.models import EvaluationRunModel, GraderResultModel, TrialModel
from arl.evidence.collector import EvidenceCollector
from arl.evidence.reporter import ReportGenerator
from arl.grading_engine.aggregator import EvaluationRunAggregator
from arl.server.db import get_db_session

router = APIRouter(prefix="/api/v1/runs", tags=["Evidence & Reports"])


@router.get("/{run_id}/report")
async def get_run_report(
    run_id: str,
    format: str = Query(default="json"),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Generate and return evaluation report with statistical bounds and evidence hashes."""
    if format not in ("json", "markdown", "md"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid report format '{format}'. Supported formats are 'json', 'markdown', 'md'.",
        )

    # 1. Fetch run and trials
    run_stmt = select(EvaluationRunModel).where(EvaluationRunModel.id == run_id)
    r = (await session.execute(run_stmt)).scalar_one_or_none()
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{run_id}' not found",
        )

    trials_stmt = select(TrialModel).where(TrialModel.run_id == run_id)
    trials_db = (await session.execute(trials_stmt)).scalars().all()

    # Convert to domain Trial objects & collect verdicts/scores
    domain_trials: list[Trial] = []
    trial_scores: dict[str, float] = {}
    trial_verdicts: dict[str, TrialVerdict] = {}

    for t in trials_db:
        domain_trials.append(
            Trial(
                id=t.id,
                run_id=t.run_id,
                trial_index=t.trial_index,
                idempotency_key=f"idemp-{t.id}",
                fault_seed=t.trial_seed or 42,
                duration_ms=int(t.duration_seconds * 1000),
                total_tokens=t.total_tokens,
                total_cost_usd=t.total_cost_usd,
            )
        )
        if t.score is not None:
            trial_scores[t.id] = t.score
        if t.passed is not None:
            trial_verdicts[t.id] = TrialVerdict.PASS if t.passed else TrialVerdict.FAIL

    # 2. Fetch all grader results for this run
    trial_ids = [t.id for t in trials_db]
    gr_stmt = (
        select(GraderResultModel).where(GraderResultModel.trial_id.in_(trial_ids))
        if trial_ids
        else None
    )
    _gr_models = (await session.execute(gr_stmt)).scalars().all() if gr_stmt is not None else []

    # 3. Compute statistical aggregation
    aggregator = EvaluationRunAggregator(readiness_threshold=0.85, min_required_trials=1)
    run_result = aggregator.aggregate(
        run_id=run_id,
        trials=domain_trials,
        trial_scores=trial_scores,
        trial_verdicts=trial_verdicts,
        grader_results=[],
    )

    collector = EvidenceCollector()
    reporter = ReportGenerator(run_result=run_result, evidence_collector=collector)

    if format in ("markdown", "md"):
        md_content = reporter.generate_markdown_report()
        return Response(content=md_content, media_type="text/markdown")

    json_payload = reporter.generate_json_report()
    return Response(content=json.dumps(json_payload), media_type="application/json")


@router.get("/{run_id}/evidence")
async def get_run_evidence(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Retrieve cryptographic evidence ledger and chain verification for a run."""
    run_stmt = select(EvaluationRunModel).where(EvaluationRunModel.id == run_id)
    r = (await session.execute(run_stmt)).scalar_one_or_none()
    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{run_id}' not found",
        )

    collector = EvidenceCollector()
    collector.record_evidence(
        trial_id="genesis",
        run_id=run_id,
        evidence_type="run_metadata",
        source_entity_type="EvaluationRun",
        source_entity_id=run_id,
        description=f"Run genesis record (state={r.state})",
        data={"total_trials": r.trial_count_total, "created_at": r.created_at.isoformat()},
    )

    return {
        "run_id": run_id,
        "chain_hash": collector.current_hash,
        "integrity_verified": collector.verify_ledger_integrity(),
        "total_blocks": len(collector.chain_blocks),
        "blocks": [b.model_dump() for b in collector.chain_blocks],
    }
