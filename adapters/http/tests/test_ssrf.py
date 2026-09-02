"""
Unit tests for HTTP Agent Adapter SSRF validation.
"""

from __future__ import annotations

import pytest

from arl.adapters.http.adapter import validate_url_for_ssrf
from arl.core.errors import SecurityViolationError


@pytest.mark.unit
def test_ssrf_rejects_private_ips() -> None:
    private_urls = [
        "http://10.0.0.1:8000/agent",
        "http://192.168.1.1:8000/agent",
        "http://172.16.0.1:8000/agent",
        "http://169.254.169.254/latest/meta-data",  # AWS/GCP metadata
    ]
    for url in private_urls:
        with pytest.raises(SecurityViolationError) as exc_info:
            validate_url_for_ssrf(url)
        assert "SSRF_PROTECTION" in str(exc_info.value)


@pytest.mark.unit
def test_ssrf_rejects_invalid_scheme() -> None:
    with pytest.raises(SecurityViolationError) as exc_info:
        validate_url_for_ssrf("file:///etc/passwd")
    assert "INVALID_SCHEME" in str(exc_info.value)

    with pytest.raises(SecurityViolationError):
        validate_url_for_ssrf("gopher://127.0.0.1:70")


@pytest.mark.unit
def test_ssrf_rejects_localhost_without_dual_environment_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 1. Neither flag set -> Rejection
    monkeypatch.delenv("ARL_ENVIRONMENT", raising=False)
    monkeypatch.delenv("ARL_ALLOW_LOCALHOST_TARGETS", raising=False)
    with pytest.raises(SecurityViolationError) as exc:
        validate_url_for_ssrf("http://127.0.0.1:8088/agent")
    assert "LOCALHOST_PROHIBITED" in str(exc.value)

    # 2. Only ARL_ENVIRONMENT=development set -> Rejection
    monkeypatch.setenv("ARL_ENVIRONMENT", "development")
    monkeypatch.delenv("ARL_ALLOW_LOCALHOST_TARGETS", raising=False)
    with pytest.raises(SecurityViolationError) as exc:
        validate_url_for_ssrf("http://localhost:8088/agent")
    assert "LOCALHOST_PROHIBITED" in str(exc.value)

    # 3. Only ARL_ALLOW_LOCALHOST_TARGETS=true set -> Rejection
    monkeypatch.setenv("ARL_ENVIRONMENT", "production")
    monkeypatch.setenv("ARL_ALLOW_LOCALHOST_TARGETS", "true")
    with pytest.raises(SecurityViolationError) as exc:
        validate_url_for_ssrf("http://127.0.0.1:8088/agent")
    assert "LOCALHOST_PROHIBITED" in str(exc.value)


@pytest.mark.unit
def test_ssrf_allows_localhost_only_when_both_flags_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARL_ENVIRONMENT", "development")
    monkeypatch.setenv("ARL_ALLOW_LOCALHOST_TARGETS", "true")

    # Should not raise
    validate_url_for_ssrf("http://localhost:8000/agent")
    validate_url_for_ssrf("http://127.0.0.1:8000/agent")
