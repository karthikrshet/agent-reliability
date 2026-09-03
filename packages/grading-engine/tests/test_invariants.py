"""
Unit tests for Deterministic Invariant Engine.

Verifies:
- All 13 supported operators (eq, neq, lt, lte, gt, gte, exists, not_exists, count_eq, count_lte, count_gte, contains, not_contains)
- Handling of missing paths
- Unsupported operators and type errors returning ERROR (never converted to PASS)
- Critical invariant violation detection
"""

from __future__ import annotations

import pytest

from arl.grading_engine.invariants import (
    InvariantEngine,
    InvariantSeverity,
    InvariantSpec,
    InvariantStatus,
    evaluate_invariant,
)


@pytest.fixture
def sample_context() -> dict[str, object]:
    return {
        "order": {
            "id": "ord-100",
            "total_cents": 5000,
            "status": "cancelled",
        },
        "refunds": [
            {"id": "ref-1", "amount": 2500, "status": "settled"},
        ],
        "audit_tags": ["security", "billing", "automated"],
        "empty_list": [],
        "null_field": None,
    }


def test_existence_operators(sample_context: dict[str, object]) -> None:
    # exists
    spec_exists = InvariantSpec(id="inv-ex", path="order.id", operator="exists")
    res = evaluate_invariant(spec_exists, sample_context)
    assert res.status == InvariantStatus.PASS

    # not_exists on missing
    spec_not_ex = InvariantSpec(id="inv-nex", path="order.non_existent", operator="not_exists")
    res_not_ex = evaluate_invariant(spec_not_ex, sample_context)
    assert res_not_ex.status == InvariantStatus.PASS

    # not_exists on empty list
    spec_empty = InvariantSpec(id="inv-empty", path="empty_list", operator="not_exists")
    assert evaluate_invariant(spec_empty, sample_context).status == InvariantStatus.PASS


def test_equality_operators(sample_context: dict[str, object]) -> None:
    spec_eq = InvariantSpec(id="inv-eq", path="order.status", operator="eq", value="cancelled")
    assert evaluate_invariant(spec_eq, sample_context).status == InvariantStatus.PASS

    spec_neq = InvariantSpec(id="inv-neq", path="order.status", operator="neq", value="active")
    assert evaluate_invariant(spec_neq, sample_context).status == InvariantStatus.PASS

    # Fail case
    spec_fail = InvariantSpec(id="inv-fail", path="order.status", operator="eq", value="refunded")
    assert evaluate_invariant(spec_fail, sample_context).status == InvariantStatus.FAIL


def test_numeric_ordering_operators(sample_context: dict[str, object]) -> None:
    spec_lt = InvariantSpec(id="inv-lt", path="order.total_cents", operator="lt", value=6000)
    assert evaluate_invariant(spec_lt, sample_context).status == InvariantStatus.PASS

    spec_lte = InvariantSpec(id="inv-lte", path="order.total_cents", operator="lte", value=5000)
    assert evaluate_invariant(spec_lte, sample_context).status == InvariantStatus.PASS

    spec_gt = InvariantSpec(id="inv-gt", path="order.total_cents", operator="gt", value=4000)
    assert evaluate_invariant(spec_gt, sample_context).status == InvariantStatus.PASS

    spec_gte = InvariantSpec(id="inv-gte", path="order.total_cents", operator="gte", value=5000)
    assert evaluate_invariant(spec_gte, sample_context).status == InvariantStatus.PASS


def test_count_operators(sample_context: dict[str, object]) -> None:
    # $.refunds count_eq 1
    spec_cnt_eq = InvariantSpec(id="inv-cnt-eq", path="refunds", operator="count_eq", value=1)
    assert evaluate_invariant(spec_cnt_eq, sample_context).status == InvariantStatus.PASS

    # $.refunds count_lte 1 (single refund invariant)
    spec_cnt_lte = InvariantSpec(
        id="single_refund",
        description="A successful order must never be refunded twice.",
        severity=InvariantSeverity.CRITICAL,
        path="refunds",
        operator="count_lte",
        value=1,
    )
    assert evaluate_invariant(spec_cnt_lte, sample_context).status == InvariantStatus.PASS

    # $.refunds count_gte 1
    spec_cnt_gte = InvariantSpec(id="inv-cnt-gte", path="refunds", operator="count_gte", value=1)
    assert evaluate_invariant(spec_cnt_gte, sample_context).status == InvariantStatus.PASS

    # Test count violation when duplicate refunds exist
    corrupt_context = {
        **sample_context,
        "refunds": [
            {"id": "ref-1", "amount": 2500},
            {"id": "ref-2", "amount": 2500},
        ],
    }
    violation_res = evaluate_invariant(spec_cnt_lte, corrupt_context)
    assert violation_res.status == InvariantStatus.FAIL
    assert violation_res.severity == InvariantSeverity.CRITICAL


def test_containment_operators(sample_context: dict[str, object]) -> None:
    spec_contains = InvariantSpec(
        id="inv-contains", path="audit_tags", operator="contains", value="security"
    )
    assert evaluate_invariant(spec_contains, sample_context).status == InvariantStatus.PASS

    spec_not_contains = InvariantSpec(
        id="inv-not-contains", path="audit_tags", operator="not_contains", value="pii_leaked"
    )
    assert evaluate_invariant(spec_not_contains, sample_context).status == InvariantStatus.PASS


def test_unsupported_operator_returns_error_never_pass() -> None:
    spec_bad = InvariantSpec(id="inv-bad", path="order.id", operator="arbitrary_eval", value=123)
    res = evaluate_invariant(spec_bad, {"order": {"id": 123}})
    assert res.status == InvariantStatus.ERROR
    assert res.error_detail is not None
    assert "Unsupported invariant operator" in res.error_detail


def test_type_error_returns_error_never_pass() -> None:
    spec_type_err = InvariantSpec(id="inv-type", path="order.status", operator="lt", value=100)
    res = evaluate_invariant(spec_type_err, {"order": {"status": "not_a_number"}})
    assert res.status == InvariantStatus.ERROR
    assert res.error_detail is not None


def test_invariant_engine_critical_failure_detection(sample_context: dict[str, object]) -> None:
    invariants = [
        InvariantSpec(
            id="inv-1", path="order.id", operator="exists", severity=InvariantSeverity.LOW
        ),
        InvariantSpec(
            id="inv-2",
            path="refunds",
            operator="count_lte",
            value=0,  # Will fail because refunds has 1 element
            severity=InvariantSeverity.CRITICAL,
        ),
    ]
    results = InvariantEngine.evaluate_all(invariants, sample_context, evidence_refs=["ev-01"])
    assert len(results) == 2
    assert results[0].status == InvariantStatus.PASS
    assert results[1].status == InvariantStatus.FAIL
    assert InvariantEngine.has_critical_failure(results) is True

    summary = InvariantEngine.summary(results)
    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["critical_failures"] == 1


def test_safe_path_search_prefixes_and_indexes() -> None:
    from arl.grading_engine.invariants import _values_equal, safe_path_search

    ctx = {
        "user": {"name": "Alice"},
        "items": [{"id": "item-1"}, {"id": "item-2"}],
    }
    # Root path "$"
    assert safe_path_search("$", ctx) == ctx
    # Prefix "$."
    assert safe_path_search("$.user.name", ctx) == "Alice"
    # List index access
    assert safe_path_search("items.0.id", ctx) == "item-1"
    # List index out of bounds
    assert safe_path_search("items.99.id", ctx) is None
    # Invalid traversal on non-collection
    assert safe_path_search("user.name.invalid", ctx) is None

    # Values equal edge cases
    assert _values_equal(None, None) is True
    assert _values_equal(10.0, 10.0000001) is True
    assert _values_equal({"a": 1}, {"a": 1}) is True
    assert _values_equal([1, 2], [1]) is False
    assert _values_equal("/^ord-\\d+$/", "ord-999") is True
    assert _values_equal("hello", 123) is False
