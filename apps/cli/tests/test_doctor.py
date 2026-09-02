"""
Unit tests for CLI doctor and verify commands.
"""

from __future__ import annotations

from typer.testing import CliRunner

from arl.cli.main import app

runner = CliRunner()


def test_cli_doctor_healthy() -> None:
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "Preflight Doctor Diagnostics" in res.stdout
    assert "DOCTOR STATUS: HEALTHY" in res.stdout


def test_cli_doctor_with_agent_url() -> None:
    res = runner.invoke(app, ["doctor", "--agent-url", "http://127.0.0.1:8088"])
    # May pass or fail depending on whether local server is up, but exercises the code path
    assert "Agent Endpoint Reachability" in res.stdout


def test_cli_verify_evidence() -> None:
    res = runner.invoke(app, ["verify"])
    assert res.exit_code == 0
    assert "CRYPTOGRAPHIC INTEGRITY VERIFIED" in res.stdout
