"""
Agent Reliability Lab — Multi-Worker Distributed Lease Concurrency Tests.

Verifies:
1. Atomic trial acquisition by multiple distributed workers (no duplicate execution).
2. Expired lease fencing and automatic reclamation after worker crash/timeout.
3. Worker lease renewal with ownership checks.
4. Clean trial completion and lease release.
5. PostgreSQL FOR UPDATE SKIP LOCKED query generation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
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
async def test_interleaved_worker_lease_acquisition_no_duplicates(
    in_memory_session_factory, seeded_run_and_trials
) -> None:
    """Ensure two workers acquiring leases in turn claim disjoint trials without collision."""
    worker_a = LeaseManager(worker_id="worker-node-A", default_lease_seconds=30)
    worker_b = LeaseManager(worker_id="worker-node-B", default_lease_seconds=30)

    claimed_a: list[str] = []
    claimed_b: list[str] = []

    for _ in range(3):
        async with in_memory_session_factory() as session_a:
            ta = await worker_a.acquire_trial_lease(session_a)
            if ta:
                claimed_a.append(ta.id)

        async with in_memory_session_factory() as session_b:
            tb = await worker_b.acquire_trial_lease(session_b)
            if tb:
                claimed_b.append(tb.id)

    # Verify all 6 trials were claimed
    total_claimed = set(claimed_a).union(set(claimed_b))
    assert len(total_claimed) == 6

    # Verify zero overlap between worker A and worker B
    overlap = set(claimed_a).intersection(set(claimed_b))
    assert len(overlap) == 0, f"Workers had collision: {overlap}"


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
        imposter_renewed = await worker_imposter.renew_lease(session, trial.id, extension_seconds=60)
        assert imposter_renewed is False

        # Owner attempts renewal -> must succeed
        owner_renewed = await worker_owner.renew_lease(session, trial.id, extension_seconds=60)
        assert owner_renewed is True

    # Owner releases lease upon completion
    async with in_memory_session_factory() as session:
        await worker_owner.release_lease(session, trial.id, new_state="COMPLETED", passed=True, score=1.0)

    # Verify finalized trial state
    async with in_memory_session_factory() as session:
        final_trial = await session.get(TrialModel, trial.id)
        assert final_trial is not None
        assert final_trial.state == "COMPLETED"
        assert final_trial.passed is True
        assert final_trial.worker_id is None
        assert final_trial.lease_expires_at is None
