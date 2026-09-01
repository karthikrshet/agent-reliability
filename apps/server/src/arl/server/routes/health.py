"""
Health and readiness probes router.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from arl.server.db import get_db_session

router = APIRouter(tags=["Health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe returning service health status."""
    return {"status": "ok", "service": "arl-server", "version": "0.1.0"}


@router.get("/readyz")
async def readyz(session: AsyncSession = Depends(get_db_session)) -> dict[str, str]:
    """Readiness probe verifying database connectivity."""
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unreachable: {exc}",
        ) from exc
