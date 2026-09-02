"""
Agent Reliability Lab — Durable Worker Lease Management.

Coordinates distributed workers using database-backed leases:
1. Workers acquire leases on pending trials via SELECT ... FOR UPDATE SKIP LOCKED.
2. Active workers periodically send heartbeats to extend their lease.
3. If a worker crashes or fails to heartbeat, reclaim_expired_leases() resets
   the trial to PENDING so another healthy worker can pick it up.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from arl.core.storage.models import TrialModel

logger = logging.getLogger(__name__)


class LeaseManager:
    """Manages worker trial leases with heartbeat renewal and crash recovery."""

    def __init__(self, worker_id: str, default_lease_seconds: int = 30) -> None:
        self.worker_id = worker_id
        self.default_lease_seconds = default_lease_seconds

    async def acquire_trial_lease(self, session: AsyncSession) -> TrialModel | None:
        """Acquire the next pending trial using SKIP LOCKED concurrency control.

        Returns TrialModel if a trial was claimed, or None if no work is available.
        """
        now = datetime.now(UTC)
        lease_expiration = now + timedelta(seconds=self.default_lease_seconds)

        bind = session.get_bind()
        is_sqlite = bind is not None and bind.dialect.name == "sqlite"
        now_cmp = now.replace(tzinfo=None) if is_sqlite else now
        lease_exp = lease_expiration.replace(tzinfo=None) if is_sqlite else lease_expiration

        # Find pending or expired-lease running trials
        base_stmt = (
            select(TrialModel)
            .where(
                (TrialModel.state == "PENDING")
                | ((TrialModel.state == "RUNNING") & (TrialModel.lease_expires_at < now_cmp))
            )
            .order_by(TrialModel.created_at.asc())
            .limit(1)
        )

        if bind is not None and bind.dialect.name == "postgresql":
            stmt = base_stmt.with_for_update(skip_locked=True)
        else:
            stmt = base_stmt

        result = await session.execute(stmt)
        trial = result.scalars().first()

        if trial is not None:
            trial.worker_id = self.worker_id
            trial.state = "RUNNING"
            trial.lease_expires_at = lease_exp
            await session.commit()
            logger.info(
                "Worker %s acquired lease on trial %s until %s",
                self.worker_id,
                trial.id,
                lease_exp,
            )
            return trial

        return None

    async def renew_lease(
        self, session: AsyncSession, trial_id: str, extension_seconds: int | None = None
    ) -> bool:
        """Extend lease expiration for an actively running trial."""
        secs = extension_seconds or self.default_lease_seconds
        new_exp_dt = datetime.now(UTC) + timedelta(seconds=secs)
        bind = session.get_bind()
        is_sqlite = bind is not None and bind.dialect.name == "sqlite"
        new_expiry = new_exp_dt.replace(tzinfo=None) if is_sqlite else new_exp_dt

        stmt = (
            update(TrialModel)
            .where(
                TrialModel.id == trial_id,
                TrialModel.worker_id == self.worker_id,
                TrialModel.state == "RUNNING",
            )
            .values(lease_expires_at=new_expiry)
        )
        result = await session.execute(stmt)
        await session.commit()
        rowcount = getattr(result, "rowcount", 0)
        return bool(rowcount > 0)

    async def release_lease(
        self,
        session: AsyncSession,
        trial_id: str,
        new_state: str = "COMPLETED",
        passed: bool | None = None,
        score: float | None = None,
        duration_seconds: float = 0.0,
        total_tokens: int = 0,
        total_cost_usd: float = 0.0,
    ) -> None:
        """Release lease upon completion or failure of a trial."""
        now = datetime.now(UTC)
        stmt = (
            update(TrialModel)
            .where(TrialModel.id == trial_id, TrialModel.worker_id == self.worker_id)
            .values(
                state=new_state,
                passed=passed,
                score=score,
                duration_seconds=duration_seconds,
                total_tokens=total_tokens,
                total_cost_usd=total_cost_usd,
                worker_id=None,
                completed_at=now,
                lease_expires_at=None,
            )
        )
        await session.execute(stmt)
        await session.commit()
        logger.info(
            "Worker %s released lease on trial %s (state=%s)", self.worker_id, trial_id, new_state
        )

    async def reclaim_expired_leases(self, session: AsyncSession) -> list[str]:
        """Reset running trials with expired leases back to PENDING."""
        now = datetime.now(UTC)
        bind = session.get_bind()
        is_sqlite = bind is not None and bind.dialect.name == "sqlite"
        now_cmp = now.replace(tzinfo=None) if is_sqlite else now

        stmt = select(TrialModel.id).where(
            TrialModel.state == "RUNNING", TrialModel.lease_expires_at < now_cmp
        )
        result = await session.execute(stmt)
        expired_ids = list(result.scalars().all())

        if expired_ids:
            reset_stmt = (
                update(TrialModel)
                .where(TrialModel.id.in_(expired_ids))
                .values(state="PENDING", worker_id=None, lease_expires_at=None)
            )
            await session.execute(reset_stmt)
            await session.commit()
            logger.warning(
                "Reclaimed %d orphaned trials with expired leases: %s",
                len(expired_ids),
                expired_ids,
            )

        return expired_ids
