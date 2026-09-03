"""
Regression test ensuring no fabricated evaluation data exists in dashboard source or examples.

Verifies that production dashboard source files and public examples do not contain
hardcoded mock constants, invented benchmark scores, fake mock LLM servers, or hardcoded run identifiers.
"""

from __future__ import annotations

from pathlib import Path

FORBIDDEN_IDENTIFIERS = [
    "run-e2e-canary-01",
    "Retail Support Bot",
    "Production Approved",
    "sampleMarkdownReport",
    "SAMPLE_TRAJECTORY",
    "92.0%",
]


def test_no_fabricated_data_in_dashboard_source() -> None:
    dashboard_src = Path("apps/dashboard/src")
    assert dashboard_src.exists(), "apps/dashboard/src directory must exist"

    violations: list[str] = []

    for file_path in dashboard_src.glob("**/*"):
        if file_path.suffix in (".ts", ".tsx", ".js", ".jsx", ".json"):
            content = file_path.read_text(encoding="utf-8")
            violations.extend(
                f"Found forbidden fabricated identifier '{identifier}' in {file_path}"
                for identifier in FORBIDDEN_IDENTIFIERS
                if identifier in content
            )

    assert not violations, (
        "Production dashboard contains fabricated data violations:\n" + "\n".join(violations)
    )


def test_no_mock_llm_server_in_examples() -> None:
    """Ensure no fake mock OpenAI server script exists in examples/openai-compatible-agent/."""
    mock_server_path = Path("examples/openai-compatible-agent/server.py")
    assert not mock_server_path.exists(), (
        "examples/openai-compatible-agent/server.py must not exist. "
        "OpenAI-compatible evaluations must run against real endpoints (OpenAI, Ollama, vLLM)."
    )
