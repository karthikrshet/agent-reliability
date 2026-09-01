"""
Agent Reliability Lab — FastAPI REST API Server Entrypoint.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from arl.core.errors import DomainError
from arl.core.storage.models import Base
from arl.server.db import engine
from arl.server.routes.evidence import router as evidence_router
from arl.server.routes.health import router as health_router
from arl.server.routes.projects import router as projects_router
from arl.server.routes.runs import router as runs_router
from arl.server.routes.scenarios import router as scenarios_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler creating tables in test environments and closing engine on shutdown."""
    logger.info("Initializing ARL REST API server...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("Shutting down ARL REST API server...")
    await engine.dispose()


def create_app() -> FastAPI:
    """Application factory for FastAPI REST server."""
    app = FastAPI(
        title="Agent Reliability Lab API",
        version="0.1.0",
        description="Production readiness testing & verification REST API for tool-using AI agents",
        lifespan=lifespan,
    )

    # CORS configuration for Next.js frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Domain error RFC 7807 handler
    @app.exception_handler(DomainError)
    async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
        err_code = getattr(exc, "code", "DOMAIN_ERROR")
        exit_code = getattr(exc, "exit_code", 1)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "type": f"https://agent-reliability.dev/errors/{err_code}",
                "title": exc.__class__.__name__,
                "status": 400,
                "detail": str(exc),
                "code": err_code,
                "exit_code": exit_code,
            },
        )

    # Include API Routers
    app.include_router(health_router)
    app.include_router(projects_router)
    app.include_router(scenarios_router)
    app.include_router(runs_router)
    app.include_router(evidence_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("arl.server.main:app", host="127.0.0.1", port=8000, reload=True)
