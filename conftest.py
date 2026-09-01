"""Shared pytest configuration for Agent Reliability Lab test suites."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom marks to suppress PytestUnknownMarkWarning."""
    config.addinivalue_line("markers", "unit: fast unit tests (no I/O, no network)")
    config.addinivalue_line("markers", "integration: tests requiring external services")
    config.addinivalue_line("markers", "e2e: full end-to-end scenario execution tests")
    config.addinivalue_line("markers", "slow: tests that take more than 1 second")
