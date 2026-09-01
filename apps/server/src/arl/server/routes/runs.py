"""
Evaluation runs and trials execution management router.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arl.core.domain.trial import TrialStatus
from arl.core.state_machine import EvaluationRunState
from arl.core.storage.models import (
    AgentVersionModel,
    EvaluationRunModel,
    GraderResultModel,
    ProjectModel,
    ScenarioModel,
    ScenarioVersionModel,
    ToolCallModel,
    TrialModel,
)
from arl.server.db import get_db_session

router = APIRouter(tags=["Runs & Trials"])


class CreateRunRequest(BaseModel):
    project_id: str
    agent_version_id: str
    scenario_ids: list[str] = Field(default_factory=list)
    trials_per_scenario: int = Field(default=3, ge=1, le=50)
    seed: int = Field(default=42)
    name: str | None = None


class RunSummaryResponse(BaseModel):
    id: str
    project_id: str
    state: str
    total_trials: int
    completed_trials: int
    passed_trials: int
    failed_trials: int
    readiness_score: float | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TrialSummaryResponse(BaseModel):
    id: str
    run_id: str
    scenario_version_id: str
    trial_index: int
    state: str
    verdict: str | None = None
    score: float | None = None
    turns_count: int
    tool_calls_count: int
    duration_seconds: float
    created_at: datetime
    completed_at: datetime | None = None


class TrialDetailResponse(BaseModel):
    id: str
    run_id: str
    scenario_version_id: str
    trial_index: int
    state: str
    verdict: str | None = None
    score: float | None = None
    turns_count: int
    tool_calls_count: int
    duration_seconds: float
    total_cost_usd: float
    tool_calls: list[dict[str, Any]]
    grader_results: list[dict[str, Any]]
    created_at: datetime
    completed_at: datetime | None = None


@router.post("/api/v1/runs", response_model=RunSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_evaluation_run(
    req: CreateRunRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RunSummaryResponse:
    """Trigger a new evaluation run across specified scenarios."""
    # 1. Verify project and agent version exist
    proj_stmt = select(ProjectModel).where(ProjectModel.id == req.project_id)
    if (await session.execute(proj_stmt)).scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{req.project_id}' not found",
        )

    agent_stmt = select(AgentVersionModel).where(AgentVersionModel.id == req.agent_version_id)
    if (await session.execute(agent_stmt)).scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent version '{req.agent_version_id}' not found",
        )

    # 2. Collect scenario versions
    scenario_versions: list[str] = []
    if req.scenario_ids:
        for sc_id in req.scenario_ids:
            sc_ver = await session.execute(
                select(ScenarioVersionModel.id).where(ScenarioVersionModel.scenario_id == sc_id)
            )
            sc_ver_id = sc_ver.scalar_one_or_none()
            if sc_ver_id:
                scenario_versions.append(sc_ver_id)
            else:
                # If scenario not yet persisted in DB, auto-create stub
                stub_sc = ScenarioModel(
                    id=sc_id,
                    project_id=req.project_id,
                    name=sc_id,
                    category="general",
                    created_at=datetime.now(UTC),
                )
                stub_ver_id = f"sv-{uuid.uuid4().hex[:12]}"
                stub_ver = ScenarioVersionModel(
                    id=stub_ver_id,
                    scenario_id=sc_id,
                    version_tag="1.0.0",
                    schema_version="1.0",
                    environment_name="customer-support",
                    environment_version="1.0.0",
                    seed=42,
                    source_yaml="",
                    source_hash="sha256-stub",
                    created_at=datetime.now(UTC),
                )
                session.add(stub_sc)
                session.add(stub_ver)
                scenario_versions.append(stub_ver_id)
    else:
        # Default scenario if none provided
        def_sc_id = "tc-001-order-lookup"
        stub_ver_id = f"sv-{uuid.uuid4().hex[:12]}"
        session.add(
            ScenarioModel(
                id=def_sc_id, project_id=req.project_id, name=def_sc_id, category="tool-correctness"
            )
        )
        session.add(
            ScenarioVersionModel(
                id=stub_ver_id,
                scenario_id=def_sc_id,
                schema_version="1.0",
                environment_name="customer-support",
                environment_version="1.0.0",
                seed=42,
                source_yaml="",
                source_hash="sha256-stub",
            )
        )
        scenario_versions.append(stub_ver_id)

    run_id = f"run-{uuid.uuid4().hex[:12]}"
    total_trials = len(scenario_versions) * req.trials_per_scenario

    eval_run = EvaluationRunModel(
        id=run_id,
        project_id=req.project_id,
        state=EvaluationRunState.CREATED.value,
        state_version=0,
        run_seed=req.seed,
        trial_count_total=total_trials,
        trial_count_completed=0,
        trial_count_passed=0,
        trial_count_failed=0,
        created_by="api-user",
        created_at=datetime.now(UTC),
    )
    session.add(eval_run)

    # 3. Create individual Trial rows for worker claiming
    trial_idx = 0
    for sc_ver_id in scenario_versions:
        for _ in range(req.trials_per_scenario):
            t_id = f"tr-{uuid.uuid4().hex[:12]}"
            trial = TrialModel(
                id=t_id,
                run_id=run_id,
                agent_version_id=req.agent_version_id,
                scenario_version_id=sc_ver_id,
                trial_index=trial_idx,
                trial_seed=req.seed + trial_idx,
                state=TrialStatus.PENDING.value,
                created_at=datetime.now(UTC),
            )
            session.add(trial)
            trial_idx += 1

    await session.commit()
    await session.refresh(eval_run)

    return RunSummaryResponse(
        id=eval_run.id,
        project_id=eval_run.project_id,
        state=eval_run.state,
        total_trials=eval_run.trial_count_total,
        completed_trials=eval_run.trial_count_completed,
        passed_trials=eval_run.trial_count_passed,
        failed_trials=eval_run.trial_count_failed,
        created_at=eval_run.created_at,
    )


@router.get("/api/v1/runs", response_model=list[RunSummaryResponse])
async def list_runs(
    project_id: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[RunSummaryResponse]:
    """List evaluation runs."""
    stmt = select(EvaluationRunModel)
    if project_id:
        stmt = stmt.where(EvaluationRunModel.project_id == project_id)
    stmt = stmt.order_by(EvaluationRunModel.created_at.desc())

    res = await session.execute(stmt)
    runs = res.scalars().all()

    return [
        RunSummaryResponse(
            id=r.id,
            project_id=r.project_id,
            state=r.state,
            total_trials=r.trial_count_total,
            completed_trials=r.trial_count_completed,
            passed_trials=r.trial_count_passed,
            failed_trials=r.trial_count_failed,
            readiness_score=r.readiness_score,
            created_at=r.created_at,
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in runs
    ]


@router.get("/api/v1/runs/{run_id}", response_model=RunSummaryResponse)
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> RunSummaryResponse:
    """Get evaluation run status by ID."""
    stmt = select(EvaluationRunModel).where(EvaluationRunModel.id == run_id)
    res = await session.execute(stmt)
    r = res.scalar_one_or_none()

    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{run_id}' not found",
        )

    return RunSummaryResponse(
        id=r.id,
        project_id=r.project_id,
        state=r.state,
        total_trials=r.trial_count_total,
        completed_trials=r.trial_count_completed,
        passed_trials=r.trial_count_passed,
        failed_trials=r.trial_count_failed,
        readiness_score=r.readiness_score,
        created_at=r.created_at,
        started_at=r.started_at,
        completed_at=r.completed_at,
    )


@router.post("/api/v1/runs/{run_id}/cancel", response_model=RunSummaryResponse)
async def cancel_run(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> RunSummaryResponse:
    """Cancel an active or pending evaluation run."""
    stmt = select(EvaluationRunModel).where(EvaluationRunModel.id == run_id)
    res = await session.execute(stmt)
    r = res.scalar_one_or_none()

    if r is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{run_id}' not found",
        )

    r.state = EvaluationRunState.CANCELLED.value
    r.completed_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(r)

    return RunSummaryResponse(
        id=r.id,
        project_id=r.project_id,
        state=r.state,
        total_trials=r.trial_count_total,
        completed_trials=r.trial_count_completed,
        passed_trials=r.trial_count_passed,
        failed_trials=r.trial_count_failed,
        readiness_score=r.readiness_score,
        created_at=r.created_at,
        started_at=r.started_at,
        completed_at=r.completed_at,
    )


@router.get("/api/v1/runs/{run_id}/trials", response_model=list[TrialSummaryResponse])
async def list_run_trials(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> list[TrialSummaryResponse]:
    """List all trials belonging to an evaluation run."""
    stmt = (
        select(TrialModel).where(TrialModel.run_id == run_id).order_by(TrialModel.trial_index.asc())
    )
    res = await session.execute(stmt)
    trials = res.scalars().all()

    return [
        TrialSummaryResponse(
            id=t.id,
            run_id=t.run_id,
            scenario_version_id=t.scenario_version_id,
            trial_index=t.trial_index,
            state=t.state,
            verdict="PASS" if t.passed else ("FAIL" if t.passed is False else None),
            score=t.score,
            turns_count=t.turns_count,
            tool_calls_count=t.tool_calls_count,
            duration_seconds=t.duration_seconds,
            created_at=t.created_at,
            completed_at=t.completed_at,
        )
        for t in trials
    ]


@router.get("/api/v1/trials/{trial_id}", response_model=TrialDetailResponse)
async def get_trial_detail(
    trial_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> TrialDetailResponse:
    """Get full trial execution detail including tool calls and grader results."""
    stmt = select(TrialModel).where(TrialModel.id == trial_id)
    res = await session.execute(stmt)
    t = res.scalar_one_or_none()

    if t is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trial '{trial_id}' not found",
        )

    # Fetch tool calls
    tc_stmt = (
        select(ToolCallModel)
        .where(ToolCallModel.trial_id == trial_id)
        .order_by(ToolCallModel.turn_index.asc(), ToolCallModel.call_index_in_turn.asc())
    )
    tc_res = await session.execute(tc_stmt)
    tcs = tc_res.scalars().all()

    # Fetch grader results
    gr_stmt = select(GraderResultModel).where(GraderResultModel.trial_id == trial_id)
    gr_res = await session.execute(gr_stmt)
    grs = gr_res.scalars().all()

    return TrialDetailResponse(
        id=t.id,
        run_id=t.run_id,
        scenario_version_id=t.scenario_version_id,
        trial_index=t.trial_index,
        state=t.state,
        verdict="PASS" if t.passed else ("FAIL" if t.passed is False else None),
        score=t.score,
        turns_count=t.turns_count,
        tool_calls_count=t.tool_calls_count,
        duration_seconds=t.duration_seconds,
        total_cost_usd=t.total_cost_usd,
        tool_calls=[
            {
                "id": c.id,
                "tool_name": c.tool_name,
                "turn_index": c.turn_index,
                "call_index_in_turn": c.call_index_in_turn,
                "arguments": c.arguments,
                "duration_ms": c.duration_ms,
                "is_fault_injected": c.is_fault_injected,
            }
            for c in tcs
        ],
        grader_results=[
            {
                "id": g.id,
                "category": g.category,
                "grader_type": g.grader_type,
                "passed": g.passed,
                "score": g.score,
                "severity": g.severity,
                "is_critical_failure": g.is_critical_failure,
                "summary": g.summary,
                "findings": g.findings,
            }
            for g in grs
        ],
        created_at=t.created_at,
        completed_at=t.completed_at,
    )
