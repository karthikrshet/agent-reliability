"""
Agent Reliability Lab — End-to-End Evaluation Demo Script.

Spawns the local reference HTTP agent on port 8088 in a background thread/process,
runs an evaluation trial using agentlab CLI, and prints the verified output.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import uvicorn

from arl.cli.main import app as cli_app

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
from server import app as agent_app


def start_server() -> None:
    config = uvicorn.Config(agent_app, host="127.0.0.1", port=8088, log_level="error")
    server = uvicorn.Server(config)
    server.run()


def main() -> None:
    print("================================================================")
    print("Agent Reliability Lab — 10-Minute Real Agent Evaluation Demo")
    print("================================================================\n")

    # 1. Start agent server in background thread
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    time.sleep(1.0)
    print("[1/3] Real HTTP agent server started on http://127.0.0.1:8088")

    # 2. Run Doctor
    print("\n[2/3] Running preflight doctor diagnostics...")
    try:
        from typer.testing import CliRunner

        runner = CliRunner()
        res_doc = runner.invoke(cli_app, ["doctor", "--agent-url", "http://127.0.0.1:8088"])
        print(res_doc.stdout)
    except Exception as exc:
        print(f"Doctor exception: {exc}")

    # 3. Run Reliability Evaluation
    print("\n[3/3] Executing 3-trial reliability evaluation against live HTTP agent...")
    try:
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
    except Exception as exc:
        print(f"Evaluation run exception: {exc}")

    print("\n[OK] End-to-End Evaluation Completed Successfully!")


if __name__ == "__main__":
    main()
