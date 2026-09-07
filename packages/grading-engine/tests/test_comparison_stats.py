"""
Tests for McNemar paired hypothesis testing, Brier score calibration, and run comparison.
"""

from __future__ import annotations

import pytest

from arl.grading_engine.stats import (
    compare_runs,
    compute_brier_score,
    compute_mcnemar_test,
)


def test_mcnemar_zero_discordant() -> None:
    """When b=0 and c=0, chi2 must be 0 and p-value 1.0 (no significant difference)."""
    chi2, p_val, is_sig = compute_mcnemar_test((10, 0, 0, 10))
    assert chi2 == 0.0
    assert p_val == 1.0
    assert is_sig is False


def test_mcnemar_balanced_discordant() -> None:
    """When b == c, chi2 must be 0 (equal number of changes in each direction)."""
    chi2, p_val, is_sig = compute_mcnemar_test((15, 5, 5, 15))
    assert chi2 == 0.0
    assert p_val == 1.0
    assert is_sig is False


def test_mcnemar_statistically_significant() -> None:
    """A large imbalance in discordant pairs (e.g., b=30, c=2) must yield p < 0.001."""
    chi2, p_val, is_sig = compute_mcnemar_test((50, 30, 2, 20), continuity_correction=True)
    assert chi2 > 20.0
    assert p_val < 0.001
    assert is_sig is True


def test_mcnemar_invalid_counts() -> None:
    """Negative counts in contingency table must raise ValueError."""
    with pytest.raises(ValueError, match="must be non-negative integers"):
        compute_mcnemar_test((-1, 5, 2, 10))


def test_brier_score_calibration() -> None:
    """Test Brier score calculation against known values."""
    # Perfect forecast
    assert compute_brier_score([1.0, 0.0], [1, 0]) == 0.0
    # Complete inversion
    assert compute_brier_score([0.0, 1.0], [1, 0]) == 1.0
    # 50/50 uncertainty
    assert compute_brier_score([0.5, 0.5], [1, 0]) == 0.25
    # Empty forecast list
    assert compute_brier_score([], []) == 0.0


def test_brier_score_validation() -> None:
    """Invalid input values must raise ValueError."""
    with pytest.raises(ValueError, match="must match outcomes length"):
        compute_brier_score([0.5], [1, 0])

    with pytest.raises(ValueError, match=r"must be between 0\.0 and 1\.0"):
        compute_brier_score([1.5], [1])

    with pytest.raises(ValueError, match="must be binary 0 or 1"):
        compute_brier_score([0.5], [2])


def test_compare_runs_scenarios() -> None:
    """Test compare_runs with two structured run payloads."""
    run_a = {
        "manifest": {"run_id": "run-base-01"},
        "trials": [
            {"scenario_id": "sc-01", "verdict": "PASS"},
            {"scenario_id": "sc-02", "verdict": "PASS"},
            {"scenario_id": "sc-03", "verdict": "PASS"},
            {"scenario_id": "sc-04", "verdict": "FAIL"},
        ],
    }
    run_b = {
        "manifest": {"run_id": "run-cand-01"},
        "trials": [
            {"scenario_id": "sc-01", "verdict": "PASS"},
            {"scenario_id": "sc-02", "verdict": "FAIL"},  # Regressed!
            {"scenario_id": "sc-03", "verdict": "PASS"},
            {"scenario_id": "sc-04", "verdict": "PASS"},  # Improved!
        ],
    }

    res = compare_runs(run_a, run_b)
    assert res["run_id_a"] == "run-base-01"
    assert res["run_id_b"] == "run-cand-01"
    assert res["common_scenarios_count"] == 4
    assert res["run_a_pass_rate"] == 0.75
    assert res["run_b_pass_rate"] == 0.75
    assert res["delta_pass_rate"] == 0.0
    assert "sc-02" in res["regressions"]
    assert "sc-04" in res["improvements"]
    assert res["verdict"] == "NO_STATISTICALLY_SIGNIFICANT_DIFFERENCE"


def test_compare_runs_significant_verdicts() -> None:
    # 25 common scenarios: all pass in A, all fail in B -> significant regression
    run_a = {"trials": [{"scenario_id": f"sc-{i}", "verdict": "PASS"} for i in range(25)]}
    run_b = {"trials": [{"scenario_id": f"sc-{i}", "verdict": "FAIL"} for i in range(25)]}
    res_reg = compare_runs(run_a, run_b)
    assert res_reg["verdict"] == "STATISTICALLY_SIGNIFICANT_REGRESSION"
    assert res_reg["is_statistically_significant"] is True

    # Reverse: all fail in A, all pass in B -> significant improvement
    res_imp = compare_runs(run_b, run_a)
    assert res_imp["verdict"] == "STATISTICALLY_SIGNIFICANT_IMPROVEMENT"
    assert res_imp["is_statistically_significant"] is True

    # Both fail
    run_fail = {"trials": [{"scenario_id": f"sc-{i}", "verdict": "FAIL"} for i in range(5)]}
    res_both_fail = compare_runs(run_fail, run_fail)
    assert res_both_fail["contingency_table"]["both_fail"] == 5
