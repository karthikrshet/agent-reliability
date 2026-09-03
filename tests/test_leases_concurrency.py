"""
Agent Reliability Lab — Multi-Worker Distributed Lease Concurrency Tests.

Verifies:
1. PostgreSQL query compilation compiles `FOR UPDATE SKIP LOCKED`.
2. Atomic trial acquisition by concurrent asynchronous worker tasks (no duplicate execution).
3. Expired lease fencing and automatic reclamation after worker crash/timeout.
4. Worker lease renewal with ownership checks.
5. Clean trial completion and lease release.
6. Optional PostgreSQL live service / testcontainer execution.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

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


def test_postgresql_skip_locked_query_compilation() -> None:
    """Verify that PostgreSQL dialect builds SELECT ... FOR UPDATE SKIP LOCKED statements."""
    stmt = (
        select(TrialModel)
        .where(TrialModel.state == "PENDING")
        .order_by(TrialModel.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    compiled = str(stmt.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE SKIP LOCKED" in compiled, (
        f"Query must contain FOR UPDATE SKIP LOCKED, got: {compiled}"
    )


@pytest.fixture
async def in_memory_session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    yield session_factory
    await engine.dispose()


@pytest.fixture
async def seeded_run_and_trials(in_memory_session_factory):
    async with in_memory_session_factory() as session:
        # Create Project
        proj = ProjectModel(id="proj-test", name="Test Project", slug="test-project")
        session.add(proj)

        # Create Agent Definition & Version
        agent = AgentDefinitionModel(
            id="agent-def-test",
            project_id=proj.id,
            name="Test Agent",
            framework="http",
        )
        session.add(agent)
        agent_ver = AgentVersionModel(
            id="agent-ver-test",
            agent_definition_id=agent.id,
            version_tag="1.0.0",
            endpoint_url="http://127.0.0.1:8088",
        )
        session.add(agent_ver)

        # Create Scenario & Version
        sc = ScenarioModel(
            id="sc-test",
            project_id=proj.id,
            name="Test Scenario",
            category="tool-correctness",
        )
        session.add(sc)
        sc_ver = ScenarioVersionModel(
            id="sc-ver-test",
            scenario_id=sc.id,
            version_tag="1.0.0",
            schema_version="2020-12",
            environment_name="customer-support",
            environment_version="1.0.0",
            seed=42,
            source_yaml="id: sc-test\ntitle: Test\ncategory: tool-correctness\nseverity: medium\nbudgets:\n  max_turns: 5\n  max_tool_calls: 3\nconversation: []\ninitial_state: {}\nenvironment:\n  name: customer-support\n  version: 1.0.0\n  seed: 42\nfault_plan: []\nexpected_effects: []\nforbidden_effects: []",
            source_hash="sc-hash-123",
        )
        session.add(sc_ver)

        # Create Evaluation Run
        run = EvaluationRunModel(
            id="run-lease-test",
            project_id=proj.id,
            state="RUNNING",
            run_seed=42,
            created_by="test-suite",
            trial_count_total=6,
        )
        session.add(run)

        # Create 6 pending trials
        for i in range(6):
            t = TrialModel(
                id=f"tr-lease-{i}",
                run_id=run.id,
                scenario_version_id=sc_ver.id,
                agent_version_id=agent_ver.id,
                trial_index=i,
                trial_seed=100 + i,
                state="PENDING",
            )
            session.add(t)

        await session.commit()
    return "run-lease-test"


@pytest.mark.asyncio
async def test_concurrent_worker_tasks_claim_disjoint_trials(
    in_memory_session_factory, seeded_run_and_trials
) -> None:
    """Ensure concurrent asynchronous workers claiming trials via separate sessions never collide."""
    workers = [
        LeaseManager(worker_id=f"worker-node-{i}", default_lease_seconds=30) for i in range(6)
    ]

    lock = asyncio.Lock()

    async def worker_claim(worker: LeaseManager) -> str | None:
        async with (
            lock,
            in_memory_session_factory() as session,
        ):  # Protect SQLite single-writer in memory
            trial = await worker.acquire_trial_lease(session)
            return trial.id if trial else None

    results = await asyncio.gather(*[worker_claim(w) for w in workers])
    claimed_ids = [r for r in results if r is not None]

    # Verify all 6 unique trials were acquired without duplication
    assert len(claimed_ids) == 6
    assert len(set(claimed_ids)) == 6, f"Duplicate trial claims detected: {claimed_ids}"


@pytest.mark.asyncio
async def test_expired_lease_reclamation_and_reacquisition(
    in_memory_session_factory, seeded_run_and_trials
) -> None:
    """Ensure an expired lease is reclaimed back to PENDING and reacquired by a healthy worker."""
    worker_dead = LeaseManager(worker_id="worker-dead", default_lease_seconds=1)
    worker_healthy = LeaseManager(worker_id="worker-healthy", default_lease_seconds=30)

    async with in_memory_session_factory() as session:
        # Worker dead acquires trial tr-lease-0 with past expiration
        trial = await worker_dead.acquire_trial_lease(session)
        assert trial is not None
        trial.lease_expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=10)
        await session.commit()

    # Worker healthy reclaims expired leases
    async with in_memory_session_factory() as session:
        reclaimed = await worker_healthy.reclaim_expired_leases(session)
        assert trial.id in reclaimed

    # Worker healthy acquires the reclaimed trial
    async with in_memory_session_factory() as session:
        reacquired_trial = await worker_healthy.acquire_trial_lease(session)
        assert reacquired_trial is not None
        assert reacquired_trial.worker_id == "worker-healthy"
        assert reacquired_trial.state == "RUNNING"


@pytest.mark.asyncio
async def test_worker_lease_renewal_ownership_fencing(
    in_memory_session_factory, seeded_run_and_trials
) -> None:
    """Ensure only the owning worker can renew a lease; unauthorized workers are rejected."""
    worker_owner = LeaseManager(worker_id="worker-owner", default_lease_seconds=30)
    worker_imposter = LeaseManager(worker_id="worker-imposter", default_lease_seconds=30)

    async with in_memory_session_factory() as session:
        trial = await worker_owner.acquire_trial_lease(session)
        assert trial is not None

    async with in_memory_session_factory() as session:
        # Imposter attempts renewal -> must fail
        imposter_renewed = await worker_imposter.renew_lease(
            session, trial.id, extension_seconds=60
        )
        assert imposter_renewed is False

        # Owner attempts renewal -> must succeed
        owner_renewed = await worker_owner.renew_lease(session, trial.id, extension_seconds=60)
        assert owner_renewed is True

    # Owner releases lease upon completion
    async with in_memory_session_factory() as session:
        await worker_owner.release_lease(
            session, trial.id, new_state="COMPLETED", passed=True, score=1.0
        )

    # Verify finalized trial state
    async with in_memory_session_factory() as session:
        final_trial = await session.get(TrialModel, trial.id)
        assert final_trial is not None
        assert final_trial.state == "COMPLETED"
        assert final_trial.passed is True
        assert final_trial.worker_id is None
        assert final_trial.lease_expires_at is None


@pytest.mark.asyncio
async def test_live_postgres_concurrent_skip_locked() -> None:
    """Execute live PostgreSQL SKIP LOCKED test if PostgreSQL test database is configured."""
    pg_url = os.getenv("ARL_TEST_POSTGRES_URL")
    if not pg_url:
        pytest.skip(
            "ARL_TEST_POSTGRES_URL not configured. Skipping live PostgreSQL container test."
        )

    pg_engine = create_async_engine(pg_url, pool_size=10, max_overflow=5)
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    pg_session_factory = async_sessionmaker(pg_engine, expire_on_commit=False)

    # Seed parent entities and trials
    async with pg_session_factory() as session:
        proj = ProjectModel(id="proj-pg-test", name="PG Test Project", slug="pg-test-project")
        session.add(proj)

        agent = AgentDefinitionModel(
            id="agent-def-pg",
            project_id=proj.id,
            name="PG Test Agent",
            framework="http",
        )
        session.add(agent)
        agent_ver = AgentVersionModel(
            id="ag-v1",
            agent_definition_id=agent.id,
            version_tag="1.0.0",
            endpoint_url="http://127.0.0.1:8088",
        )
        session.add(agent_ver)

        sc = ScenarioModel(
            id="sc-pg-test",
            project_id=proj.id,
            name="PG Scenario",
            category="tool-correctness",
        )
        session.add(sc)
        sc_ver = ScenarioVersionModel(
            id="sc-v1",
            scenario_id=sc.id,
            version_tag="1.0.0",
            schema_version="2020-12",
            environment_name="customer-support",
            environment_version="1.0.0",
            seed=42,
            source_yaml="id: sc-pg-test\ntitle: Test\ncategory: tool-correctness\nseverity: medium\nbudgets:\n  max_turns: 5\n  max_tool_calls: 3\nconversation: []\ninitial_state: {}\nenvironment:\n  name: customer-support\n  version: 1.0.0\n  seed: 42\nfault_plan: []\nexpected_effects: []\nforbidden_effects: []",
            source_hash="sc-hash-pg-123",
        )
        session.add(sc_ver)

        run = EvaluationRunModel(
            id="run-pg-test",
            project_id=proj.id,
            state="RUNNING",
            run_seed=42,
            created_by="test-suite",
            trial_count_total=4,
        )
        session.add(run)

        for i in range(4):
            session.add(
                TrialModel(
                    id=f"tr-pg-lease-{i}",
                    run_id=run.id,
                    scenario_version_id=sc_ver.id,
                    agent_version_id=agent_ver.id,
                    trial_index=i,
                    trial_seed=200 + i,
                    state="PENDING",
                )
            )
        await session.commit()

    # Concurrent claims across distinct connections without application-level locks
    async def claim_from_pg(worker_id: str) -> str | None:
        async with pg_session_factory() as s:
            mgr = LeaseManager(worker_id=worker_id)
            t = await mgr.acquire_trial_lease(s)
            return t.id if t else None

    workers = [f"pg-worker-{i}" for i in range(4)]
    claimed = await asyncio.gather(*[claim_from_pg(w) for w in workers])
    valid_claims = [c for c in claimed if c is not None]

    assert len(valid_claims) == 4
    assert len(set(valid_claims)) == 4
    await pg_engine.dispose()
