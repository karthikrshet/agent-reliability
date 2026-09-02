"""
Unit and statistical property tests for grading stats (Wilson score interval, pass@k, mean CIs).
"""

from __future__ import annotations

import pytest

from arl.grading_engine.stats import (
    compute_mean_and_ci,
    compute_pass_at_k,
    compute_wilson_score_interval,
)


@pytest.mark.unit
def test_wilson_score_interval_boundaries() -> None:
    # 0 successes out of 10
    lower_0, upper_0 = compute_wilson_score_interval(successes=0, trials=10)
    assert lower_0 == 0.0
    assert 0.0 < upper_0 < 0.4

    # 10 successes out of 10
    lower_10, upper_10 = compute_wilson_score_interval(successes=10, trials=10)
    assert 0.6 < lower_10 < 1.0
    assert upper_10 == 1.0

    # 5 out of 10 (center should be 0.5)
    lower_5, upper_5 = compute_wilson_score_interval(successes=5, trials=10)
    assert lower_5 < 0.5 < upper_5
    assert (lower_5 + upper_5) / 2.0 == pytest.approx(0.5, abs=0.01)


@pytest.mark.unit
def test_wilson_score_interval_invalid_inputs() -> None:
    assert compute_wilson_score_interval(0, 0) == (0.0, 0.0)

    with pytest.raises(ValueError, match="between 0 and trials"):
        compute_wilson_score_interval(successes=12, trials=10)

    with pytest.raises(ValueError, match="between 0 and trials"):
        compute_wilson_score_interval(successes=-1, trials=10)


@pytest.mark.unit
def test_pass_at_k_exact_properties() -> None:
    # When k=1, pass@1 must equal c / n
    for n, c in [(10, 8), (20, 15), (5, 0), (5, 5)]:
        p1 = compute_pass_at_k(n=n, c=c, k=1)
        assert p1 == pytest.approx(c / n, abs=1e-4)

    # When all trials pass (c == n), pass@k must be 1.0 for any k <= n
    for k in [1, 2, 5]:
        assert compute_pass_at_k(n=5, c=5, k=k) == 1.0

    # When 0 trials pass (c == 0), pass@k must be 0.0
    for k in [1, 2, 5]:
        assert compute_pass_at_k(n=5, c=0, k=k) == 0.0

    # Pass@k must be monotonically increasing with k
    n = 10
    c = 3
    p1 = compute_pass_at_k(n, c, 1)
    p2 = compute_pass_at_k(n, c, 2)
    p3 = compute_pass_at_k(n, c, 3)
    assert p1 < p2 < p3


@pytest.mark.unit
def test_wilson_known_reference_values() -> None:
    """Validate Wilson score against standard textbook and SciPy reference values."""
    # 80 successes out of 100 at 95% confidence
    lower, upper = compute_wilson_score_interval(successes=80, trials=100, confidence=0.95)
    assert lower == pytest.approx(0.7115, abs=0.005)
    assert upper == pytest.approx(0.8666, abs=0.005)

    # 1 success out of 10 at 95% confidence
    l1, u1 = compute_wilson_score_interval(successes=1, trials=10, confidence=0.95)
    assert l1 == pytest.approx(0.0179, abs=0.005)
    assert u1 == pytest.approx(0.4041, abs=0.005)


@pytest.mark.unit
def test_pass_at_k_invalid_inputs() -> None:
    assert compute_pass_at_k(0, 0, 1) == 0.0

    with pytest.raises(ValueError, match="cannot be greater than total trials"):
        compute_pass_at_k(n=5, c=3, k=6)

    with pytest.raises(ValueError, match="must be between 0 and n"):
        compute_pass_at_k(n=5, c=6, k=2)


@pytest.mark.unit
def test_compute_mean_and_ci() -> None:
    assert compute_mean_and_ci([]) == (0.0, 0.0, 0.0)

    mean, lower, upper = compute_mean_and_ci([10.0])
    assert mean == 10.0
    assert lower == 10.0
    assert upper == 10.0

    values = [10.0, 12.0, 11.0, 9.0, 13.0]
    mean, lower, upper = compute_mean_and_ci(values)
    assert mean == 11.0
    assert lower < 11.0 < upper
