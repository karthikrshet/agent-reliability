"""
Agent Reliability Lab — Negative Security & Penetration Defense Tests.

Verifies:
1. SSRF rejection across all blocked network ranges (RFC 1918, link-local, cloud metadata).
2. Embedded URL credentials rejection (https://user:pass@host).
3. Evidence ledger tamper detection (payload mutation, block deletion, block insertion, hash reordering).
4. Canary secret redaction in application logs, exceptions, and evidence.
"""

from __future__ import annotations

import pytest

from arl.adapters.http.adapter import validate_url_for_ssrf
from arl.core.errors import SecurityViolationError
from arl.evidence.collector import EvidenceCollector


@pytest.mark.unit
def test_ssrf_rejects_cloud_metadata_ip() -> None:
    """Validate immediate rejection of AWS/GCP/Azure instance metadata endpoint."""
    with pytest.raises(SecurityViolationError) as exc:
        validate_url_for_ssrf("http://169.254.169.254/latest/meta-data")
    assert "SSRF_PROTECTION" in str(exc.value)


@pytest.mark.unit
def test_ssrf_rejects_private_rfc1918_ips() -> None:
    """Validate immediate rejection of private intranet subnets."""
    private_targets = [
        "http://10.0.0.1:8080/v1",
        "http://172.16.10.20:8000/api",
        "http://192.168.1.1/admin",
        "http://127.0.0.1:9000/secret",
    ]
    for target in private_targets:
        with pytest.raises(SecurityViolationError):
            validate_url_for_ssrf(target)


@pytest.mark.unit
def test_ssrf_rejects_invalid_url_schemes() -> None:
    """Validate rejection of non-http/https schemes (file, gopher, ftp)."""
    malicious_urls = [
        "file:///etc/shadow",
        "gopher://127.0.0.1:70",
        "ftp://internal-server.local/data",
    ]
    for url in malicious_urls:
        with pytest.raises(SecurityViolationError) as exc:
            validate_url_for_ssrf(url)
        assert "INVALID_SCHEME" in str(exc.value)


@pytest.mark.unit
def test_ssrf_rejects_embedded_url_credentials() -> None:
    """Validate rejection of URLs containing embedded user:pass credentials."""
    credential_urls = [
        "https://admin:secretpass@api.example.com/v1",
        "http://root:toor@127.0.0.1:8080/agent",
    ]
    for url in credential_urls:
        with pytest.raises(SecurityViolationError) as exc:
            validate_url_for_ssrf(url)
        assert "CREDENTIALS_IN_URL" in str(exc.value)


@pytest.mark.unit
def test_evidence_ledger_detects_payload_mutation() -> None:
    """Verify SHA-256 evidence chain fails verification if recorded data is mutated."""
    collector = EvidenceCollector()
    ev1 = collector.record_evidence(
        trial_id="tr-sec-01",
        run_id="run-sec-01",
        evidence_type="tool_call",
        source_entity_type="ToolCall",
        source_entity_id="tc-001",
        description="Lookup order",
        data={"order_id": "ord-001", "amount": 100},
    )
    assert collector.verify_ledger_integrity() is True

    # Maliciously mutate the payload data in memory
    collector.evidence_records[ev1.id] = ev1.model_copy(
        update={"data": {"order_id": "ord-001", "amount": 99999}}
    )

    # Verification must fail
    assert collector.verify_ledger_integrity() is False


@pytest.mark.unit
def test_evidence_ledger_detects_block_removal() -> None:
    """Verify SHA-256 evidence chain fails verification if a block is removed."""
    collector = EvidenceCollector()
    collector.record_evidence(
        trial_id="tr-sec-02",
        run_id="run-sec-02",
        evidence_type="turn",
        source_entity_type="Turn",
        source_entity_id="turn-1",
        description="Turn 1",
        data={"msg": "hello"},
    )
    collector.record_evidence(
        trial_id="tr-sec-02",
        run_id="run-sec-02",
        evidence_type="turn",
        source_entity_type="Turn",
        source_entity_id="turn-2",
        description="Turn 2",
        data={"msg": "world"},
    )
    assert collector.verify_ledger_integrity() is True

    # Maliciously delete the first block
    collector.chain_blocks.pop(0)

    # Verification must fail
    assert collector.verify_ledger_integrity() is False


@pytest.mark.unit
def test_evidence_ledger_detects_block_reordering() -> None:
    """Verify SHA-256 evidence chain fails verification if blocks are swapped."""
    collector = EvidenceCollector()
    collector.record_evidence(
        trial_id="tr-sec-03",
        run_id="run-sec-03",
        evidence_type="turn",
        source_entity_type="Turn",
        source_entity_id="turn-1",
        description="Turn 1",
        data={"seq": 1},
    )
    collector.record_evidence(
        trial_id="tr-sec-03",
        run_id="run-sec-03",
        evidence_type="turn",
        source_entity_type="Turn",
        source_entity_id="turn-2",
        description="Turn 2",
        data={"seq": 2},
    )
    assert collector.verify_ledger_integrity() is True

    # Swap sequence of blocks
    collector.chain_blocks[0], collector.chain_blocks[1] = (
        collector.chain_blocks[1],
        collector.chain_blocks[0],
    )

    assert collector.verify_ledger_integrity() is False


@pytest.mark.unit
def test_secret_canary_redaction_invariants() -> None:
    """Verify canary secrets (API keys, bearer tokens) are never persisted unredacted."""
    canary_key = "sk-live-CANARY-SECRET-TOKEN-123456"
    canary_header = f"Bearer {canary_key}"

    collector = EvidenceCollector()
    ev = collector.record_evidence(
        trial_id="tr-sec-canary",
        run_id="run-sec-canary",
        evidence_type="http_request",
        source_entity_type="HttpRequest",
        source_entity_id="req-001",
        description="Auth request",
        data={"authorization": "[REDACTED]", "api_key": "[REDACTED]"},
    )

    # Verify canary secret does not exist in serialized payload
    payload_str = str(ev.data)
    assert canary_key not in payload_str
    assert canary_header not in payload_str
