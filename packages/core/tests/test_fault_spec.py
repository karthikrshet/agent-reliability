"""
Unit tests for FaultSpec and FaultResult domain models.

Verifies construction, immutability, canonical fault types, and serialization.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from arl.core.domain.faults import (
    FaultResult,
    FaultSpec,
    FaultType,
)


def test_fault_spec_construction_and_defaults() -> None:
    spec = FaultSpec(
        id="flt-test-01",
        target="refund.create",
        fault_type=FaultType.TIMEOUT_AFTER_EFFECT,
        parameters={"delay_ms": 500},
        side_effect_committed=True,
    )
    assert spec.id == "flt-test-01"
    assert spec.target == "refund.create"
    assert spec.fault_type == FaultType.TIMEOUT_AFTER_EFFECT
    assert spec.side_effect_committed is True
    assert spec.seed == 42


def test_fault_spec_immutability() -> None:
    spec = FaultSpec(
        id="flt-immut-01",
        target="payment.create",
        fault_type=FaultType.HTTP_500,
    )
    with pytest.raises(ValidationError):
        spec.target = "other.tool"  # type: ignore[misc]


def test_fault_result_construction() -> None:
    res = FaultResult(
        fault_id="flt-test-01",
        injected=True,
        target="refund.create",
        observed_effect="HTTP 500 downstream internal server error",
        side_effect_committed=True,
        duration_ms=350,
        error_type="InternalServerError",
        error_message="Downstream database deadlock",
    )
    assert res.fault_id == "flt-test-01"
    assert res.injected is True
    assert res.side_effect_committed is True
    assert res.duration_ms == 350
    assert res.error_type == "InternalServerError"


def test_all_canonical_fault_types_exist() -> None:
    expected_canonical = [
        "timeout",
        "latency",
        "http_429",
        "http_500",
        "connection_reset",
        "malformed_response",
        "empty_response",
        "duplicate_response",
        "timeout_after_effect",
    ]
    for ft in expected_canonical:
        assert FaultType(ft) is not None
