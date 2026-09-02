"""
Automated end-to-end evaluation demo using the deterministic HTTP reference agent.

Starts the FastAPI agent in a background thread, runs `agentlab doctor` to verify
preflight connectivity, and executes 3 trials of order lookup evaluation.
"""

from __future__ import annotations

import contextlib
import sys
import threading
import time
from pathlib import Path

import uvicorn

from arl.cli.main import app as cli_app

if hasattr(sys.stdout, "reconfigure"):
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")


def run_agent_server() -> None:
    from examples.deterministic_http_reference_agent.server import (  # type: ignore[import-not-found]
        app as agent_app,
    )

    uvicorn.run(agent_app, host="127.0.0.1", port=8088, log_level="error")


def run_agent_server_direct() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "server",
        Path(__file__).parent / "server.py",
    )
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        uvicorn.run(mod.app, host="127.0.0.1", port=8088, log_level="error")


def main() -> None:
    print("=" * 70)
    print("ARL Live Evaluation Demo (Deterministic HTTP Reference Agent)")
    print("=" * 70)

    # 1. Start agent server in background daemon thread
    server_thread = threading.Thread(target=run_agent_server_direct, daemon=True)
    server_thread.start()
    time.sleep(1.5)

    try:
        from typer.testing import CliRunner

        runner = CliRunner()

        # 2. Run Doctor diagnostics
        print("\n[Step 1/2] Running 'agentlab doctor' preflight diagnostics...")
        res_doc = runner.invoke(cli_app, ["doctor", "--agent-url", "http://127.0.0.1:8088"])
        print(res_doc.stdout)

        # 3. Run Reliability Evaluation
        print("\n[Step 2/2] Running 'agentlab run' with 3 trials against live HTTP agent...")
        res_run = runner.invoke(
            cli_app,
            [
                "run",
                "-s",
                "scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml",
                "--agent-url",
                "http://127.0.0.1:8088",
                "--trials",
                "3",
                "--seed",
                "42",
            ],
        )
        print(res_run.stdout)

        print("\n" + "=" * 70)
        print("Demo completed successfully!")
        print("=" * 70)
    finally:
        pass


if __name__ == "__main__":
    main()
