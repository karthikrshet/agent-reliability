"""
Unit and CLI invocation tests for agentlab.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from arl.cli.main import app

runner = CliRunner()


@pytest.mark.unit
def test_cli_list_scenarios() -> None:
    res = runner.invoke(app, ["list-scenarios"])
    assert res.exit_code == 0
    assert "Agent Reliability Lab" in res.output


@pytest.mark.unit
def test_cli_validate_scenario() -> None:
    yaml_path = Path("scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml")
    if yaml_path.exists():
        res = runner.invoke(app, ["validate", str(yaml_path)])
        assert res.exit_code == 0
        assert "VALID SCENARIO" in res.output


@pytest.mark.unit
def test_cli_validate_nonexistent() -> None:
    res = runner.invoke(app, ["validate", "nonexistent_scenario.yaml"])
    assert res.exit_code != 0
    assert "File not found" in res.output


@pytest.mark.unit
def test_cli_list_scenarios_with_category() -> None:
    res = runner.invoke(app, ["list-scenarios", "--category", "tool-correctness"])
    assert res.exit_code == 0
    assert "Agent Reliability Lab" in res.output


@pytest.mark.unit
def test_cli_run_without_target_fails_with_config_error() -> None:
    """Ensure running without an explicit target exits with configuration error code 2."""
    yaml_path = Path("scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml")
    if yaml_path.exists():
        res = runner.invoke(
            app, ["run", "--scenario", str(yaml_path), "--trials", "1", "--seed", "42"]
        )
        assert res.exit_code == 2
        assert "CONFIGURATION ERROR: No target agent specified" in res.output


@pytest.mark.unit
def test_cli_run_reference_agent() -> None:
    """Ensure explicit --reference-agent executes with NON_PRODUCTION_REFERENCE notice."""
    yaml_path = Path("scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml")
    if yaml_path.exists():
        res = runner.invoke(
            app,
            [
                "run",
                "--scenario",
                str(yaml_path),
                "--reference-agent",
                "--trials",
                "1",
                "--seed",
                "42",
            ],
        )
        assert res.exit_code == 0
        assert "Execution Progress" in res.output
        assert "NON_PRODUCTION_REFERENCE" in res.output


@pytest.mark.unit
def test_cli_run_conflicting_targets_fails() -> None:
    """Ensure specifying multiple targets exits with configuration error."""
    yaml_path = Path("scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml")
    if yaml_path.exists():
        res = runner.invoke(
            app,
            [
                "run",
                "--scenario",
                str(yaml_path),
                "--reference-agent",
                "--agent-url",
                "http://127.0.0.1:8088",
            ],
        )
        assert res.exit_code == 2
        assert "CONFIGURATION ERROR: Multiple target agents specified" in res.output


@pytest.mark.unit
def test_cli_run_missing_scenario() -> None:
    res = runner.invoke(
        app, ["run", "--scenario", "nonexistent_scenario.yaml", "--reference-agent"]
    )
    assert res.exit_code != 0


@pytest.mark.unit
def test_cli_fuzz(tmp_path: Path) -> None:
    yaml_path = Path("scenarios/failure-recovery/04-http-500-retry.yaml")
    if yaml_path.exists():
        res = runner.invoke(
            app,
            [
                "fuzz",
                str(yaml_path),
                "--variants",
                "2",
                "--out-dir",
                str(tmp_path),
                "--seed",
                "42",
            ],
        )
        assert res.exit_code == 0
        assert "ARL Scenario Fuzzer" in res.output
        assert "Generated Schema-Valid Mutants" in res.output
        assert len(list(tmp_path.glob("*.yaml"))) == 2


@pytest.mark.unit
def test_cli_fuzz_missing_file() -> None:
    res = runner.invoke(app, ["fuzz", "nonexistent_scenario.yaml"])
    assert res.exit_code != 0
    assert "not found" in res.output


@pytest.mark.unit
def test_cli_compare() -> None:
    res = runner.invoke(app, ["compare", "run-2a432c75", "run-5c30c699"])
    assert res.exit_code == 0
    assert "ARL Paired Statistical Run Comparison" in res.output
    assert "Verdict" in res.output


@pytest.mark.unit
def test_cli_compare_missing_run() -> None:
    res = runner.invoke(app, ["compare", "run-nonexistent-1234", "run-nonexistent-5678"])
    assert res.exit_code != 0
