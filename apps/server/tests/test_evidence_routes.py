"""
Integration tests for server evidence and reporting routes.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from arl.core.storage.models import Base
from arl.server.db import engine
from arl.server.main import app


@pytest.fixture(autouse=True)
async def prepare_database() -> AsyncGenerator[None, None]:
    """Ensure in-memory SQLite schema tables exist for tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_evidence_and_report_endpoints(client: AsyncClient) -> None:
    # 1. Test 404 for non-existent run
    res_404 = await client.get("/api/v1/runs/nonexistent-run/report")
    assert res_404.status_code == 404

    res_ev_404 = await client.get("/api/v1/runs/nonexistent-run/evidence")
    assert res_ev_404.status_code == 404

    # 2. Create project
    res_proj = await client.post(
        "/api/v1/projects",
        json={"name": "Report Test Project", "slug": "report-test"},
    )
    assert res_proj.status_code == 201
    proj_id = res_proj.json()["id"]

    # 3. Create agent and version
    res_agent = await client.post(
        f"/api/v1/projects/{proj_id}/agents",
        json={
            "name": "Report Test Agent",
            "framework": "http",
            "version_tag": "1.0.0",
            "endpoint_url": "http://localhost:9000",
        },
    )
    assert res_agent.status_code == 201
    agent_ver_id = res_agent.json()["latest_version_id"]

    # 4. Create run
    res_run = await client.post(
        "/api/v1/runs",
        json={
            "project_id": proj_id,
            "agent_version_id": agent_ver_id,
            "scenario_ids": ["order-lookup-correct-arguments"],
            "trials_per_scenario": 1,
            "seed": 42,
        },
    )
    assert res_run.status_code == 201
    run_id = res_run.json()["id"]

    # 5. Fetch JSON report
    res_rep_json = await client.get(f"/api/v1/runs/{run_id}/report?format=json")
    assert res_rep_json.status_code == 200
    data_json = res_rep_json.json()
    assert "run_id" in data_json

    # 6. Fetch Markdown report
    res_rep_md = await client.get(f"/api/v1/runs/{run_id}/report?format=markdown")
    assert res_rep_md.status_code == 200
    assert "# Agent Reliability Lab" in res_rep_md.text

    # 7. Invalid report format
    res_rep_inv = await client.get(f"/api/v1/runs/{run_id}/report?format=pdf")
    assert res_rep_inv.status_code in (400, 422)

    # 8. Fetch Evidence chain
    res_ev = await client.get(f"/api/v1/runs/{run_id}/evidence")
    assert res_ev.status_code == 200
    data_ev = res_ev.json()
    assert data_ev["integrity_verified"] is True
    assert len(data_ev["blocks"]) >= 1

    # 9. Cancel run
    res_cancel = await client.post(f"/api/v1/runs/{run_id}/cancel")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["state"] == "CANCELLED"
