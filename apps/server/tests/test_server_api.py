"""
Integration tests for FastAPI REST API endpoints.
"""

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
async def test_health_and_readiness_endpoints(client: AsyncClient) -> None:
    res_h = await client.get("/healthz")
    assert res_h.status_code == 200
    assert res_h.json()["status"] == "ok"

    res_r = await client.get("/readyz")
    assert res_r.status_code == 200
    assert res_r.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_projects_and_agents_crud(client: AsyncClient) -> None:
    # 1. Create project
    res_p = await client.post(
        "/api/v1/projects",
        json={
            "name": "Retail Support Bot",
            "slug": "retail-support-bot",
            "description": "Support evaluation",
        },
    )
    assert res_p.status_code == 201
    proj_data = res_p.json()
    proj_id = proj_data["id"]
    assert proj_data["name"] == "Retail Support Bot"

    # 2. List projects
    res_list = await client.get("/api/v1/projects")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 3. Get single project
    res_single = await client.get(f"/api/v1/projects/{proj_id}")
    assert res_single.status_code == 200
    assert res_single.json()["id"] == proj_id

    # 4. Register agent definition and version
    res_agent = await client.post(
        f"/api/v1/projects/{proj_id}/agents",
        json={
            "name": "Customer Care Agent",
            "framework": "http",
            "version_tag": "1.0.0",
            "endpoint_url": "http://localhost:9000",
        },
    )
    assert res_agent.status_code == 201
    agent_data = res_agent.json()
    assert agent_data["name"] == "Customer Care Agent"
    assert agent_data["latest_version_id"] is not None

    # 5. List agents
    res_agents = await client.get(f"/api/v1/projects/{proj_id}/agents")
    assert res_agents.status_code == 200
    assert len(res_agents.json()) == 1
    agent_id = res_agents.json()[0]["id"]

    # 6. Get single agent
    res_ag_get = await client.get(f"/api/v1/projects/{proj_id}/agents/{agent_id}")
    assert res_ag_get.status_code == 200
    assert res_ag_get.json()["id"] == agent_id

    # 7. Create new agent version
    res_ag_ver = await client.post(
        f"/api/v1/projects/{proj_id}/agents/{agent_id}/versions",
        json={"version_tag": "1.1.0", "endpoint_url": "http://localhost:9001"},
    )
    assert res_ag_ver.status_code == 201
    assert res_ag_ver.json()["version_tag"] == "1.1.0"

    # 8. Patch project
    res_patch = await client.patch(
        f"/api/v1/projects/{proj_id}",
        json={"name": "Retail Support Bot Updated"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["name"] == "Retail Support Bot Updated"

    # 9. Delete project
    res_del = await client.delete(f"/api/v1/projects/{proj_id}")
    assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_scenarios_endpoints(client: AsyncClient) -> None:
    # 1. List scenarios
    res_sc = await client.get("/api/v1/scenarios")
    assert res_sc.status_code == 200
    scenarios = res_sc.json()
    assert isinstance(scenarios, list)

    # 2. Validate valid scenario YAML
    valid_yaml = """
schema_version: "1.0"
id: test-valid-scenario
version: "1.0.0"
title: Test valid
category: tool-correctness
severity: medium
environment:
  name: customer-support
  version: "1.0.0"
  seed: 42
conversation:
  - role: user
    content: hello
budgets:
  max_turns: 5
  max_tool_calls: 3
  max_duration_seconds: 30.0
"""
    res_val = await client.post("/api/v1/scenarios/validate", json={"yaml_content": valid_yaml})
    assert res_val.status_code == 200
    assert res_val.json()["is_valid"] is True
    assert res_val.json()["scenario_id"] == "test-valid-scenario"


@pytest.mark.asyncio
async def test_runs_and_evidence_lifecycle(client: AsyncClient) -> None:
    # Create project & agent
    p_res = await client.post("/api/v1/projects", json={"name": "Run Test Project"})
    proj_id = p_res.json()["id"]

    a_res = await client.post(
        f"/api/v1/projects/{proj_id}/agents",
        json={"name": "Run Agent", "framework": "mock"},
    )
    agent_ver_id = a_res.json()["latest_version_id"]

    # 1. Create evaluation run
    res_run = await client.post(
        "/api/v1/runs",
        json={
            "project_id": proj_id,
            "agent_version_id": agent_ver_id,
            "scenario_ids": ["tc-01-order-lookup"],
            "trials_per_scenario": 2,
            "seed": 100,
        },
    )
    assert res_run.status_code == 201
    run_data = res_run.json()
    run_id = run_data["id"]
    assert run_data["total_trials"] == 2

    # 2. Get run status and list runs
    res_get_run = await client.get(f"/api/v1/runs/{run_id}")
    assert res_get_run.status_code == 200
    assert res_get_run.json()["id"] == run_id

    res_runs_all = await client.get("/api/v1/runs")
    assert res_runs_all.status_code == 200
    assert len(res_runs_all.json()) >= 1

    res_runs_proj = await client.get(f"/api/v1/runs?project_id={proj_id}")
    assert res_runs_proj.status_code == 200
    assert len(res_runs_proj.json()) >= 1

    # 3. List trials
    res_trials = await client.get(f"/api/v1/runs/{run_id}/trials")
    assert res_trials.status_code == 200
    trials = res_trials.json()
    assert len(trials) == 2
    trial_id = trials[0]["id"]

    # 4. Get trial detail
    res_td = await client.get(f"/api/v1/trials/{trial_id}")
    assert res_td.status_code == 200
    assert res_td.json()["id"] == trial_id

    # 5. Get report (json & markdown)
    res_rep_json = await client.get(f"/api/v1/runs/{run_id}/report?format=json")

    # 6. Fetch evidence and reports
    res_rep_md = await client.get(f"/api/v1/runs/{run_id}/report?format=markdown")
    assert res_rep_md.status_code == 200
    assert "# Agent Reliability Lab" in res_rep_md.text

    res_rep_json = await client.get(f"/api/v1/runs/{run_id}/report?format=json")
    assert res_rep_json.status_code == 200
    assert "run_id" in res_rep_json.json()

    res_ev = await client.get(f"/api/v1/runs/{run_id}/evidence")
    assert res_ev.status_code == 200
    assert res_ev.json()["integrity_verified"] is True

    # 7. Get single trial detail
    if trials:
        t_id = trials[0]["id"]
        res_td = await client.get(f"/api/v1/trials/{t_id}")
        assert res_td.status_code == 200
        assert res_td.json()["id"] == t_id

    # 8. Cancel run
    res_cancel = await client.post(f"/api/v1/runs/{run_id}/cancel")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["state"] == "CANCELLED"


@pytest.mark.asyncio
async def test_server_404_and_validation_error_paths(client: AsyncClient) -> None:
    # 1. Missing project
    res_np = await client.get("/api/v1/projects/nonexistent-proj")
    assert res_np.status_code == 404

    # 2. Register agent under missing project
    res_na = await client.post(
        "/api/v1/projects/nonexistent-proj/agents",
        json={"name": "Ghost Agent", "framework": "http"},
    )
    assert res_na.status_code == 404

    # 3. Create run with invalid project
    res_nr = await client.post(
        "/api/v1/runs",
        json={"project_id": "nonexistent-proj", "agent_version_id": "av-123"},
    )
    assert res_nr.status_code == 404

    # 4. Create project and attempt invalid agent version run
    p_res = await client.post("/api/v1/projects", json={"name": "P404"})
    pid = p_res.json()["id"]

    res_nav = await client.post(
        "/api/v1/runs",
        json={"project_id": pid, "agent_version_id": "av-nonexistent"},
    )
    assert res_nav.status_code == 404

    # 5. Missing scenario
    res_sc = await client.get("/api/v1/scenarios/nonexistent-scenario-id")
    assert res_sc.status_code == 404

    # 6. Invalid scenario YAML validation
    res_val_bad = await client.post(
        "/api/v1/scenarios/validate",
        json={"yaml_content": "invalid: yaml: ["},
    )
    assert res_val_bad.status_code == 200
    assert res_val_bad.json()["is_valid"] is False

    # 7. Missing trial
    res_tr = await client.get("/api/v1/trials/tr-missing")
    assert res_tr.status_code == 404

    # 8. Missing run report & evidence
    res_rep = await client.get("/api/v1/runs/run-missing/report")
    assert res_rep.status_code == 404
    res_ev = await client.get("/api/v1/runs/run-missing/evidence")
    assert res_ev.status_code == 404
    res_canc = await client.post("/api/v1/runs/run-missing/cancel")
    assert res_canc.status_code == 404
