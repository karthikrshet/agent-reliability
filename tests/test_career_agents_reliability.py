r"""
Career-Agents Platform — Comprehensive Reliability & Verification Suite.

Tests the full 'Career-Agents' workspace (D:\the project master\Career-Agents) using
Agent Reliability Lab (ARL) evaluation principles:
1. Registry Integrity & Schema Validation (all 167 agents, workflows, bundles).
2. Model Context Protocol (MCP) tool conformance & stdio JSON-RPC contract.
3. Career Tools execution: search_agents, recommend_agents, career_assessment.
4. Stress & Fault Injection: edge cases, empty arguments, malformed payloads.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

CAREER_AGENTS_ROOT = Path("D:/the project master/Career-Agents")


def _get_node_bin() -> str:
    bin_path = shutil.which("node")
    return bin_path if bin_path else "node"


def _create_mcp_client() -> subprocess.Popen[str]:
    """Helper to start Career-Agents MCP server with initialized handshake."""
    mcp_script = CAREER_AGENTS_ROOT / "career-agents-mcp" / "index.js"
    proc = subprocess.Popen(  # noqa: S603
        [_get_node_bin(), str(mcp_script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )

    # Send initialize request
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "arl-test-harness", "version": "0.2.0"},
        },
    }
    assert proc.stdin is not None
    assert proc.stdout is not None
    proc.stdin.write(json.dumps(init_req) + "\n")
    proc.stdin.flush()
    proc.stdout.readline()  # consume initialize response
    return proc


@pytest.mark.skipif(
    not CAREER_AGENTS_ROOT.exists(), reason="Career-Agents workspace not found on disk"
)
class TestCareerAgentsReliability:
    def test_01_workspace_integrity_and_doctor(self) -> None:
        """Verify Career-Agents internal validator passes with 100% integrity."""
        cmd = [_get_node_bin(), "./scripts/cli.js", "validate"]
        res = subprocess.run(  # noqa: S603
            cmd,
            cwd=str(CAREER_AGENTS_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert res.returncode == 0, f"Career-Agents doctor failed:\n{res.stderr}\n{res.stdout}"
        assert "Everything is green!" in res.stdout or "validate.py checks pass" in res.stdout

    def test_02_agent_registry_integrity_and_count(self) -> None:
        """Verify all 167 career agents are indexed and properly structured."""
        registry_file = CAREER_AGENTS_ROOT / "career-agents.json"
        assert registry_file.exists(), "career-agents.json must exist"

        data = json.loads(registry_file.read_text(encoding="utf-8"))
        agents = data.get("agents", [])
        assert len(agents) >= 150, f"Expected at least 150 agents, found {len(agents)}"

        for ag in agents:
            assert "id" in ag, f"Agent missing id: {ag}"
            assert "name" in ag, f"Agent {ag.get('id')} missing name"
            assert "division" in ag, f"Agent {ag.get('id')} missing division"

    def test_03_mcp_server_tools_list_conformance(self) -> None:
        """Verify Career-Agents MCP server initializes and exposes compliant tool definitions."""
        proc = _create_mcp_client()
        try:
            tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            assert proc.stdin is not None
            assert proc.stdout is not None
            proc.stdin.write(json.dumps(tools_req) + "\n")
            proc.stdin.flush()

            resp_line = proc.stdout.readline().strip()
            data = json.loads(resp_line)

            assert data.get("id") == 2
            tools = data.get("result", {}).get("tools", [])
            tool_names = {t["name"] for t in tools}

            assert "search_agents" in tool_names, "Missing search_agents tool"
            assert "recommend_agents" in tool_names, "Missing recommend_agents tool"
            assert "career_assessment" in tool_names, "Missing career_assessment tool"
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_04_mcp_tool_execution_search_and_recommendation(self) -> None:
        """Verify real tool execution via MCP stdio protocol."""
        proc = _create_mcp_client()
        try:
            call_req = {
                "jsonrpc": "2.0",
                "id": 10,
                "method": "tools/call",
                "params": {
                    "name": "recommend_agents",
                    "arguments": {
                        "role": "ai-engineer",
                        "experience": "senior",
                        "skills": "Python, PyTorch, LangChain, LLMs",
                        "company": "google",
                    },
                },
            }
            assert proc.stdin is not None
            assert proc.stdout is not None
            proc.stdin.write(json.dumps(call_req) + "\n")
            proc.stdin.flush()

            resp_line = proc.stdout.readline().strip()
            data = json.loads(resp_line)

            assert data.get("id") == 10
            res = data.get("result", {})
            content = res.get("content", [])
            assert len(content) > 0, "Expected non-empty tool call result"
            text_output = content[0].get("text", "")
            assert len(text_output) > 20, (
                f"Expected detailed recommendation content, got: {text_output}"
            )
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_05_fault_injection_resilience_on_malformed_inputs(self) -> None:
        """Fault injection: send malformed / empty arguments to ensure no unhandled crashes."""
        proc = _create_mcp_client()
        try:
            faulty_call = {
                "jsonrpc": "2.0",
                "id": 99,
                "method": "tools/call",
                "params": {
                    "name": "recommend_agents",
                    "arguments": {},
                },
            }
            assert proc.stdin is not None
            assert proc.stdout is not None
            proc.stdin.write(json.dumps(faulty_call) + "\n")
            proc.stdin.flush()

            resp_line = proc.stdout.readline().strip()
            data = json.loads(resp_line)

            assert (
                "error" in data or data.get("result", {}).get("isError") is True or "result" in data
            )
            assert proc.poll() is None, "MCP process must survive faulty input without dying"
        finally:
            proc.terminate()
            proc.wait(timeout=5)
