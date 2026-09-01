"""
Agent Reliability Lab — Worker Service Entrypoint.

Continuously runs the execution worker loop:
1. Polls for available trial leases.
2. Loads trial, scenario, adapter, and environment.
3. Executes TrialExecutor with heartbeat renewal in the background.
4. Persists execution artifacts (turns, tool_calls, snapshots, fault_events).
5. Releases lease upon completion.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from arl.adapters.http.adapter import HttpAgentAdapter
from arl.adapters.reference.agent import MockAgentAdapter
from arl.core.domain.trial import Trial
from arl.core.storage.models import (
    AgentVersionModel,
    FaultEventModel,
    ScenarioVersionModel,
    ToolCallModel,
    ToolResultModel,
    TrialModel,
    WorldStateSnapshotModel,
)
from arl.environments.customer_support.environment import CustomerSupportEnvironment
from arl.execution_engine.executor import TrialExecutor
from arl.protocol.adapter import AgentAdapter
from arl.scenario_engine.loader import load_scenario_from_string
from arl.worker.lease import LeaseManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("arl.worker")


class ExecutionWorker:
    """Distributed execution worker managing trial lifecycles."""

    def __init__(self, database_url: str, worker_id: str | None = None) -> None:
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.database_url = database_url
        self.engine = create_async_engine(self.database_url, pool_pre_ping=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.lease_manager = LeaseManager(worker_id=self.worker_id)
        self.is_running = True

    def stop(self) -> None:
        """Request graceful shutdown."""
        logger.info("Worker %s received stop signal.", self.worker_id)
        self.is_running = False

    async def run_loop(self, poll_interval_seconds: float = 1.0) -> None:
        """Main worker loop."""
        logger.info("Worker %s started processing trials.", self.worker_id)

        while self.is_running:
            try:
                async with self.session_factory() as session:
                    # Periodically reclaim any orphaned expired leases
                    await self.lease_manager.reclaim_expired_leases(session)

                    # Acquire next available trial
                    trial_model = await self.lease_manager.acquire_trial_lease(session)
                    if trial_model is not None:
                        await self._process_trial(session, trial_model.id)
                    else:
                        await asyncio.sleep(poll_interval_seconds)
            except Exception:
                logger.exception("Error in worker execution loop")
                await asyncio.sleep(poll_interval_seconds)

        await self.engine.dispose()
        logger.info("Worker %s stopped cleanly.", self.worker_id)

    async def _process_trial(self, session: AsyncSession, trial_id: str) -> None:
        """Process an acquired trial."""
        logger.info("Worker %s processing trial %s", self.worker_id, trial_id)

        # 1. Load trial model and related models
        trial_model = await session.get(TrialModel, trial_id)
        if trial_model is None:
            return

        scenario_ver = await session.get(ScenarioVersionModel, trial_model.scenario_version_id)
        agent_ver = await session.get(AgentVersionModel, trial_model.agent_version_id)

        if scenario_ver is None or agent_ver is None:
            logger.error("Missing scenario_version or agent_version for trial %s", trial_id)
            await self.lease_manager.release_lease(session, trial_id, new_state="FAILED")
            return

        # 2. Parse scenario and instantiate environment
        parsed_scenario = load_scenario_from_string(scenario_ver.source_yaml)
        environment = CustomerSupportEnvironment(seed=parsed_scenario.environment.seed)

        # 3. Instantiate adapter
        adapter: AgentAdapter
        if agent_ver.endpoint_url:
            adapter = HttpAgentAdapter(endpoint_url=agent_ver.endpoint_url, allow_localhost=True)
        else:
            adapter = MockAgentAdapter()

        # 4. Domain Trial model
        domain_trial = Trial(
            id=trial_model.id,
            run_id=trial_model.run_id,
            trial_index=trial_model.trial_index,
            idempotency_key=f"idemp-{trial_model.id}",
            fault_seed=trial_model.trial_seed,
            worker_id=self.worker_id,
        )

        executor = TrialExecutor(
            trial=domain_trial,
            scenario=parsed_scenario,
            adapter=adapter,
            environment=environment,
        )

        # 5. Heartbeat task in background while executor runs
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(trial_id))

        try:
            result = await executor.run()
        finally:
            heartbeat_task.cancel()

        # 6. Persist execution records
        for tc in result.tool_calls:
            session.add(
                ToolCallModel(
                    id=tc.id,
                    trial_id=trial_id,
                    tool_name=tc.tool_name,
                    arguments=tc.call_arguments,
                    idempotency_key=tc.idempotency_key,
                    turn_index=tc.sequence_index,
                    call_index_in_turn=tc.sequence_index,
                    duration_ms=0,
                )
            )

        for tr in result.tool_results:
            session.add(
                ToolResultModel(
                    id=tr.id,
                    tool_call_id=tr.tool_call_id,
                    content=tr.content,
                    is_error=tr.is_error,
                    error_type=tr.error_code,
                )
            )

        for fe in result.fault_events:
            session.add(
                FaultEventModel(
                    id=fe.id,
                    trial_id=trial_id,
                    tool_call_id=fe.tool_call_id,
                    fault_type=fe.fault_type.value,
                    target_tool=fe.target_tool,
                    trigger_invocation=fe.trigger_invocation,
                    behaviour_data=fe.behaviour.model_dump(),
                    fault_seed=fe.fault_seed,
                )
            )

        if result.pre_snapshot:
            session.add(
                WorldStateSnapshotModel(
                    id=result.pre_snapshot.id,
                    trial_id=trial_id,
                    phase="pre_trial",
                    state_payload=result.pre_snapshot.state,
                )
            )

        if result.post_snapshot:
            session.add(
                WorldStateSnapshotModel(
                    id=result.post_snapshot.id,
                    trial_id=trial_id,
                    phase="post_trial",
                    state_payload=result.post_snapshot.state,
                )
            )

        # 7. Release lease with final status
        final_state = "COMPLETED" if result.completed_normally else "FAILED"
        await self.lease_manager.release_lease(
            session=session,
            trial_id=trial_id,
            new_state=final_state,
            duration_seconds=result.duration_seconds,
            total_tokens=result.total_tokens,
            total_cost_usd=result.total_cost_usd,
        )

    async def _heartbeat_loop(self, trial_id: str, interval_seconds: float = 10.0) -> None:
        """Renew lease periodically."""
        try:
            while self.is_running:
                await asyncio.sleep(interval_seconds)
                async with self.session_factory() as session:
                    await self.lease_manager.renew_lease(session, trial_id)
        except asyncio.CancelledError:
            pass


async def main() -> None:
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://arl:arl_secret_dev_only@localhost:5432/arl_dev")
    worker = ExecutionWorker(database_url=db_url)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, worker.stop)

    await worker.run_loop()


if __name__ == "__main__":
    asyncio.run(main())
