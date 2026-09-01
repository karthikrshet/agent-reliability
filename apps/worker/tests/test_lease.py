"""
Unit tests for LeaseManager using SQLite in-memory database.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from arl.core.storage.models import (
    AgentDefinitionModel,
    AgentVersionModel,
    Base,
    EvaluationRunModel,
    ProjectModel,
    ScenarioModel,
    ScenarioVersionModel,
    TrialModel,
)
from arl.worker.lease import LeaseManager


@pytest.fixture
async def async_session_factory() -> Any:
    # Use in-memory SQLite with JSON support
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lease_acquisition_and_release(async_session_factory: Any) -> None:
    async with async_session_factory() as session:
        # Seed test project, agent, scenario, run, and trial
        proj = ProjectModel(id="p1", name="Proj 1", slug="proj-1")
        agent_def = AgentDefinitionModel(
            id="ad1", project_id="p1", name="Agent 1", framework="mock"
        )
        agent_ver = AgentVersionModel(id="av1", agent_definition_id="ad1", version_tag="1.0.0")
        scen = ScenarioModel(id="s1", project_id="p1", name="Scen 1", category="tool-correctness")
        scen_ver = ScenarioVersionModel(
            id="sv1",
            scenario_id="s1",
            version_tag="1.0.0",
            schema_version="1.0",
            environment_name="customer-support",
            environment_version="1.0.0",
            seed=42,
            source_yaml="schema_version: '1.0'",
            source_hash="hash",
        )
        run = EvaluationRunModel(id="r1", project_id="p1", run_seed=42, created_by="test")
        trial = TrialModel(
            id="t1",
            run_id="r1",
            agent_version_id="av1",
            scenario_version_id="sv1",
            trial_index=0,
            trial_seed=42,
            state="PENDING",
        )

        session.add_all([proj, agent_def, agent_ver, scen, scen_ver, run, trial])
        await session.commit()

        # Worker claims lease
        manager = LeaseManager(worker_id="worker-01", default_lease_seconds=60)
        claimed = await manager.acquire_trial_lease(session)
        assert claimed is not None
        assert claimed.id == "t1"
        assert claimed.state == "RUNNING"
        assert claimed.worker_id == "worker-01"
        assert claimed.lease_expires_at is not None

        # Another worker tries to claim — should get None
        manager_other = LeaseManager(worker_id="worker-02")
        claimed_other = await manager_other.acquire_trial_lease(session)
        assert claimed_other is None

        # Renew lease
        renewed = await manager.renew_lease(session, trial_id="t1", extension_seconds=120)
        assert renewed is True

        # Release lease upon completion
        await manager.release_lease(
            session=session,
            trial_id="t1",
            new_state="COMPLETED",
            passed=True,
            score=1.0,
            duration_seconds=5.2,
            total_tokens=150,
            total_cost_usd=0.005,
        )

        updated_trial = await session.get(TrialModel, "t1")
        assert updated_trial is not None
        assert updated_trial.state == "COMPLETED"
        assert updated_trial.passed is True
        assert updated_trial.score == 1.0
        assert updated_trial.lease_expires_at is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reclaim_expired_leases(async_session_factory: Any) -> None:
    async with async_session_factory() as session:
        proj = ProjectModel(id="p2", name="P2", slug="p2")
        agent_def = AgentDefinitionModel(id="ad2", project_id="p2", name="A2", framework="mock")
        agent_ver = AgentVersionModel(id="av2", agent_definition_id="ad2", version_tag="1.0.0")
        scen = ScenarioModel(id="s2", project_id="p2", name="S2", category="tool-correctness")
        scen_ver = ScenarioVersionModel(
            id="sv2",
            scenario_id="s2",
            version_tag="1.0.0",
            schema_version="1.0",
            environment_name="customer-support",
            environment_version="1.0.0",
            seed=42,
            source_yaml="schema_version: '1.0'",
            source_hash="hash",
        )
        run = EvaluationRunModel(id="r2", project_id="p2", run_seed=42, created_by="test")

        # Trial with expired lease in the past
        past_time = datetime.now(UTC) - timedelta(minutes=5)
        expired_trial = TrialModel(
            id="t-expired",
            run_id="r2",
            agent_version_id="av2",
            scenario_version_id="sv2",
            trial_index=0,
            trial_seed=42,
            state="RUNNING",
            worker_id="crashed-worker",
            lease_expires_at=past_time,
        )

        session.add_all([proj, agent_def, agent_ver, scen, scen_ver, run, expired_trial])
        await session.commit()

        manager = LeaseManager(worker_id="healthy-worker")
        reclaimed = await manager.reclaim_expired_leases(session)
        assert "t-expired" in reclaimed

        t = await session.get(TrialModel, "t-expired")
        assert t is not None
        assert t.state == "PENDING"
        assert t.worker_id is None
        assert t.lease_expires_at is None
