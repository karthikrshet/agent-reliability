"""
Unit tests for ARL MCP Server tool handlers and schema definitions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from arl.mcp.server import MCPServer

SCENARIOS_DIR = Path(__file__).resolve().parents[3] / "scenarios"


@pytest.fixture
def mcp_server() -> MCPServer:
    return MCPServer(scenarios_dir=SCENARIOS_DIR)


def test_mcp_tool_definitions(mcp_server: MCPServer) -> None:
    tools = mcp_server.get_tool_definitions()
    tool_names = [t["name"] for t in tools]
    assert "list_scenarios" in tool_names
    assert "get_scenario_spec" in tool_names
    assert "validate_scenario_yaml" in tool_names
    assert "run_evaluation_trial" in tool_names
    assert "calculate_wilson_interval" in tool_names
    assert "verify_evidence_chain" in tool_names


@pytest.mark.asyncio
async def test_mcp_list_scenarios(mcp_server: MCPServer) -> None:
    res = await mcp_server.handle_tool_call("list_scenarios", {})
    assert not res.get("isError")
    data = json.loads(res["content"][0]["text"])
    assert data["total"] >= 25

    # Test filtering by category
    res_cat = await mcp_server.handle_tool_call("list_scenarios", {"category": "tool-correctness"})
    data_cat = json.loads(res_cat["content"][0]["text"])
    assert data_cat["total"] == 5


@pytest.mark.asyncio
async def test_mcp_get_scenario_spec(mcp_server: MCPServer) -> None:
    res = await mcp_server.handle_tool_call(
        "get_scenario_spec", {"scenario_id": "order-lookup-correct-arguments"}
    )
    assert not res.get("isError")
    data = json.loads(res["content"][0]["text"])
    assert data["id"] == "order-lookup-correct-arguments"
    assert "raw_yaml" in data

    # Test not found
    res_err = await mcp_server.handle_tool_call(
        "get_scenario_spec", {"scenario_id": "nonexistent-scenario"}
    )
    assert res_err.get("isError") is True


@pytest.mark.asyncio
async def test_mcp_validate_scenario_yaml(mcp_server: MCPServer) -> None:
    sample_file = next(SCENARIOS_DIR.rglob("*.yaml"))
    valid_yaml = sample_file.read_text(encoding="utf-8")
    res = await mcp_server.handle_tool_call("validate_scenario_yaml", {"yaml_content": valid_yaml})
    assert not res.get("isError")
    data = json.loads(res["content"][0]["text"])
    assert data["valid"] is True

    # Test invalid yaml
    res_err = await mcp_server.handle_tool_call(
        "validate_scenario_yaml", {"yaml_content": "invalid: yaml: [broken"}
    )
    assert res_err.get("isError") is True


@pytest.mark.asyncio
async def test_mcp_calculate_wilson_interval(mcp_server: MCPServer) -> None:
    res = await mcp_server.handle_tool_call(
        "calculate_wilson_interval", {"successes": 69, "total": 75, "threshold": 0.80}
    )
    assert not res.get("isError")
    data = json.loads(res["content"][0]["text"])
    assert data["empirical_pass_rate"] == 0.92
    assert data["wilson_lower_95"] > 0.80
    assert data["production_ready"] is True
    assert data["verdict"] == "READY"


@pytest.mark.asyncio
async def test_mcp_verify_evidence_chain(mcp_server: MCPServer) -> None:
    res = await mcp_server.handle_tool_call("verify_evidence_chain", {"evidence_records": []})
    assert not res.get("isError")
    data = json.loads(res["content"][0]["text"])
    assert data["chain_valid"] is True


@pytest.mark.asyncio
async def test_mcp_run_evaluation_trial(mcp_server: MCPServer) -> None:
    # Test without target -> must error
    res_no_target = await mcp_server.handle_tool_call(
        "run_evaluation_trial",
        {"scenario_id": "order-lookup-correct-arguments", "seed": 42},
    )
    assert res_no_target.get("isError") is True

    # Test with explicit reference_only -> succeeds
    res = await mcp_server.handle_tool_call(
        "run_evaluation_trial",
        {
            "scenario_id": "order-lookup-correct-arguments",
            "seed": 42,
            "reference_only": True,
        },
    )
    assert not res.get("isError")
    data = json.loads(res["content"][0]["text"])
    assert data["scenario_id"] == "order-lookup-correct-arguments"
    assert data["reference_only"] is True
    assert data["verdict"] == "NON_PRODUCTION_REFERENCE"
    assert data["score"] >= 0

    # Test unknown scenario
    res_err = await mcp_server.handle_tool_call(
        "run_evaluation_trial",
        {"scenario_id": "invalid-sc", "reference_only": True},
    )
    assert res_err.get("isError") is True

    # Test unknown tool
    res_unknown = await mcp_server.handle_tool_call("nonexistent_tool", {})
    assert res_unknown.get("isError") is True


@pytest.mark.asyncio
async def test_mcp_empty_scenarios_cache(tmp_path: Path) -> None:
    empty_server = MCPServer(scenarios_dir=tmp_path / "empty")
    res = await empty_server.handle_tool_call("list_scenarios", {})
    assert not res.get("isError")
    data = json.loads(res["content"][0]["text"])
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_mcp_jsonrpc_protocol_flow(mcp_server: MCPServer) -> None:
    # 1. Initialize
    init_res = await mcp_server.handle_jsonrpc_request(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    assert init_res["id"] == 1
    assert "serverInfo" in init_res["result"]

    # 2. Tools list
    tools_res = await mcp_server.handle_jsonrpc_request(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    )
    assert tools_res["id"] == 2
    assert "tools" in tools_res["result"]

    # 3. Tools call
    call_res = await mcp_server.handle_jsonrpc_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "list_scenarios", "arguments": {}},
        }
    )
    assert call_res["id"] == 3
    assert not call_res["result"].get("isError")

    # 4. Ping
    ping_res = await mcp_server.handle_jsonrpc_request(
        {"jsonrpc": "2.0", "id": 4, "method": "ping", "params": {}}
    )
    assert ping_res["id"] == 4

    # 5. Method not found
    err_res = await mcp_server.handle_jsonrpc_request(
        {"jsonrpc": "2.0", "id": 5, "method": "unknown/method", "params": {}}
    )
    assert "error" in err_res
    assert err_res["error"]["code"] == -32601
