"""Shared pytest configuration for Agent Reliability Lab test suites."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure all workspace packages, adapters, environments, and apps are on sys.path
_REPO_ROOT = Path(__file__).resolve().parent
for _pattern in ("packages/*/src", "adapters/*/src", "apps/*/src", "environments/*/src"):
    for _src_dir in sorted(_REPO_ROOT.glob(_pattern)):
        if "dashboard" in _src_dir.parts:
            continue
        _str_path = str(_src_dir)
        if _str_path not in sys.path:
            sys.path.insert(0, _str_path)

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def pytest_configure(config: pytest.Config) -> None:
    """Register custom marks to suppress PytestUnknownMarkWarning."""
    config.addinivalue_line("markers", "unit: fast unit tests (no I/O, no network)")
    config.addinivalue_line("markers", "integration: tests requiring external services")
    config.addinivalue_line("markers", "e2e: full end-to-end scenario execution tests")
    config.addinivalue_line("markers", "slow: tests that take more than 1 second")
