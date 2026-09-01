"""
Integration tests for ExecutionWorker lifecycle and trial execution.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

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
from arl.worker.main import ExecutionWorker


@pytest.mark.asyncio
async def test_execution_worker_process_trial(tmp_path: Path) -> None:
    db_file = tmp_path / "worker_test.db"
    database_url = f"sqlite+aiosqlite:///{db_file}"

    worker = ExecutionWorker(database_url=database_url, worker_id="test-worker-1")

    # Initialize schema
    async with worker.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed test project, agent, scenario, run, and trial
    raw_yaml = """
schema_version: "1.0"
id: tc-worker-order-lookup
version: "1.0.0"
title: Worker Order Lookup
category: tool-correctness
severity: medium
environment:
  name: customer-support
  version: "1.0.0"
  seed: 42
conversation:
  - role: user
    content: Could you please check the status of order ord-1001?
budgets:
  max_turns: 5
  max_tool_calls: 3
  max_duration_seconds: 30.0
"""
    async with worker.session_factory() as session:
        proj = ProjectModel(id="proj-w1", name="Worker Test Proj", slug="worker-test-proj")
        agent = AgentDefinitionModel(id="ad-w1", project_id="proj-w1", name="Bot", framework="mock")
        agent_ver = AgentVersionModel(id="av-w1", agent_definition_id="ad-w1", version_tag="1.0.0")
        scenario = ScenarioModel(
            id="sc-w1", project_id="proj-w1", name="Worker Sc", category="tool-correctness"
        )
        scenario_ver = ScenarioVersionModel(
            id="sv-w1",
            scenario_id="sc-w1",
            version_tag="1.0.0",
            schema_version="1.0",
            environment_name="customer-support",
            environment_version="1.0.0",
            seed=42,
            source_yaml=raw_yaml,
            source_hash="hash-123",
        )
        eval_run = EvaluationRunModel(
            id="run-w1",
            project_id="proj-w1",
            state="RUNNING",
            run_seed=42,
            created_by="tester",
        )
        trial = TrialModel(
            id="tr-w1",
            run_id="run-w1",
            agent_version_id="av-w1",
            scenario_version_id="sv-w1",
            trial_index=0,
            trial_seed=42,
            state="PENDING",
            created_at=datetime.now(UTC),
        )
        session.add_all([proj, agent, agent_ver, scenario, scenario_ver, eval_run, trial])
        await session.commit()

    # Worker acquires and processes trial
    async with worker.session_factory() as session:
        acquired = await worker.lease_manager.acquire_trial_lease(session)
        assert acquired is not None
        assert acquired.id == "tr-w1"

        await worker._process_trial(session, "tr-w1")

    # Verify trial completed and records were persisted
    async with worker.session_factory() as session:
        updated_trial = await session.get(TrialModel, "tr-w1")
        assert updated_trial is not None
        assert updated_trial.state in ("COMPLETED", "FAILED")
        assert updated_trial.worker_id is None  # Lease released

    # Test stop flag
    worker.stop()
    assert worker.is_running is False
    await worker.engine.dispose()


@pytest.mark.asyncio
async def test_execution_worker_missing_scenario(tmp_path: Path) -> None:
    db_file = tmp_path / "worker_missing.db"
    database_url = f"sqlite+aiosqlite:///{db_file}"
    worker = ExecutionWorker(database_url=database_url, worker_id="test-worker-2")

    async with worker.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with worker.session_factory() as session:
        trial = TrialModel(
            id="tr-missing-sc",
            run_id="run-missing",
            agent_version_id="av-nonexistent",
            scenario_version_id="sv-nonexistent",
            trial_index=0,
            trial_seed=42,
            state="CLAIMED",
            worker_id="test-worker-2",
            created_at=datetime.now(UTC),
        )
        session.add(trial)
        await session.commit()

    async with worker.session_factory() as session:
        await worker._process_trial(session, "tr-missing-sc")

    async with worker.session_factory() as session:
        updated = await session.get(TrialModel, "tr-missing-sc")
        assert updated is not None
        assert updated.state == "FAILED"

    await worker.engine.dispose()
