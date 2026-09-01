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
            validate_url_for_ssrf(url, allow_localhost=False)
        assert "SSRF protection" in str(exc_info.value)


@pytest.mark.unit
def test_ssrf_rejects_invalid_scheme() -> None:
    with pytest.raises(SecurityViolationError) as exc_info:
        validate_url_for_ssrf("file:///etc/passwd")
    assert "Invalid URL scheme" in str(exc_info.value)

    with pytest.raises(SecurityViolationError):
        validate_url_for_ssrf("gopher://127.0.0.1:70")


@pytest.mark.unit
def test_ssrf_allows_localhost_when_explicitly_enabled() -> None:
    # When allow_localhost=True, 127.0.0.1 and localhost are permitted
    validate_url_for_ssrf("http://localhost:8000/agent", allow_localhost=True)
    validate_url_for_ssrf("http://127.0.0.1:8000/agent", allow_localhost=True)
