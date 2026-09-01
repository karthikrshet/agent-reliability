"""
Agent Reliability Lab — Statistical Interpretations & Confidence Intervals.

Functions:
- Wilson score interval for binomial proportions (pass/fail rates)
- Unbiased pass@k estimator
- Continuous metric mean and confidence interval estimation
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from scipy import stats  # type: ignore[import-untyped]


def compute_wilson_score_interval(
    successes: int,
    trials: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Compute the Wilson score interval for a binomial proportion.

    Preferred over the normal approximation (Wald interval) because it
    maintains coverage near p=0 and p=1 and for small sample sizes.

    Returns (lower_bound, upper_bound) clamped to [0.0, 1.0].
    """
    if trials <= 0:
        return 0.0, 0.0
    if successes < 0 or successes > trials:
        raise ValueError(f"Successes ({successes}) must be between 0 and trials ({trials})")

    # Quantile for the two-sided confidence interval
    z = float(stats.norm.ppf(1.0 - (1.0 - confidence) / 2.0))
    z2 = z * z
    n = float(trials)
    k = float(successes)
    p_hat = k / n

    denominator = 1.0 + z2 / n
    center = (p_hat + z2 / (2.0 * n)) / denominator
    spread = (z / denominator) * math.sqrt((p_hat * (1.0 - p_hat) / n) + (z2 / (4.0 * n * n)))

    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)

    return round(lower, 4), round(upper, 4)


def compute_pass_at_k(n: int, c: int, k: int) -> float:
    """Compute the unbiased pass@k estimator.

    Formula:
        pass@k = 1.0 - comb(n - c, k) / comb(n, k)

    where:
        n = total number of trials
        c = number of successful (passing) trials
        k = sample size parameter (e.g. k=1, k=3, k=5)
    """
    if n <= 0 or k <= 0:
        return 0.0
    if k > n:
        raise ValueError(f"k ({k}) cannot be greater than total trials n ({n})")
    if c < 0 or c > n:
        raise ValueError(f"c ({c}) must be between 0 and n ({n})")

    if n - c < k:
        return 1.0

    # comb(n - c, k) / comb(n, k) = prod_{i=1}^k (n - c - i + 1) / (n - i + 1)
    fail_prob = 1.0
    for i in range(1, k + 1):
        fail_prob *= (n - c - i + 1.0) / (n - i + 1.0)

    pass_at_k = 1.0 - fail_prob
    return round(max(0.0, min(1.0, pass_at_k)), 4)


def compute_mean_and_ci(
    values: Sequence[float],
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Compute arithmetic mean and Student-t confidence interval.

    Returns (mean, ci_lower, ci_upper).
    """
    if not values:
        return 0.0, 0.0, 0.0

    n = len(values)
    mean_val = float(sum(values) / n)

    if n == 1:
        return round(mean_val, 4), round(mean_val, 4), round(mean_val, 4)

    variance = sum((x - mean_val) ** 2 for x in values) / (n - 1)
    std_dev = math.sqrt(variance)
    sem = std_dev / math.sqrt(n)

    t_crit = float(stats.t.ppf((1.0 + confidence) / 2.0, df=n - 1))
    margin = t_crit * sem

    return round(mean_val, 4), round(mean_val - margin, 4), round(mean_val + margin, 4)
