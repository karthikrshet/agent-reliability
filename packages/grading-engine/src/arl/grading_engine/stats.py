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
from typing import Any

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


def compute_mcnemar_test(
    contingency_table: tuple[int, int, int, int],
    continuity_correction: bool = True,
    confidence: float = 0.95,
) -> tuple[float, float, bool]:
    """Compute McNemar's test for paired nominal data (Run A vs Run B).

    Used to determine whether there is a statistically significant difference
    in reliability between two agent versions evaluated on the identical scenarios.

    contingency_table: (a, b, c, d)
        a: Both Run A and Run B PASSED
        b: Run A PASSED, Run B FAILED (discordant)
        c: Run A FAILED, Run B PASSED (discordant)
        d: Both Run A and Run B FAILED

    Returns (chi2_statistic, p_value, is_significant).
    """
    a, b, c, d = contingency_table
    if any(count < 0 for count in (a, b, c, d)):
        raise ValueError("Contingency table counts must be non-negative integers")

    discordant = b + c
    if discordant == 0:
        return 0.0, 1.0, False

    diff = abs(b - c)
    numerator = max(0.0, diff - 1.0) ** 2 if continuity_correction else float(diff**2)

    chi2 = numerator / discordant
    p_val = float(1.0 - stats.chi2.cdf(chi2, df=1))
    alpha = 1.0 - confidence
    is_sig = p_val < alpha

    return round(chi2, 4), round(p_val, 4), is_sig


def compute_brier_score(
    forecasts: Sequence[float],
    outcomes: Sequence[int],
) -> float:
    """Compute the Brier calibration score for probabilistic reliability predictions.

    BS = (1 / N) * sum((forecast_i - outcome_i) ^ 2)

    Lower scores indicate better calibrated reliability models (0.0 = perfect, 1.0 = completely inverted).
    """
    if len(forecasts) != len(outcomes):
        raise ValueError(
            f"Forecasts length ({len(forecasts)}) must match outcomes length ({len(outcomes)})"
        )
    if not forecasts:
        return 0.0

    total_error = 0.0
    for f, o in zip(forecasts, outcomes, strict=True):
        if not (0.0 <= f <= 1.0):
            raise ValueError(f"Forecast value {f} must be between 0.0 and 1.0")
        if o not in (0, 1):
            raise ValueError(f"Outcome value {o} must be binary 0 or 1")
        total_error += (f - float(o)) ** 2

    return round(total_error / len(forecasts), 4)


def compare_runs(
    run_a: dict[str, Any],
    run_b: dict[str, Any],
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Compare two evaluation runs paired across matching scenarios.

    Computes:
    - Pass rate delta: Run B - Run A
    - McNemar chi-square test and p-value on discordant pairs
    - Regressions: Scenarios passed in A but failed in B
    - Improvements: Scenarios failed in A but passed in B
    - Reliability verdict: REGRESSION, IMPROVEMENT, or EQUIVALENT
    """
    manifest_a = run_a.get("manifest", {})
    manifest_b = run_b.get("manifest", {})
    trials_a = run_a.get("trials", [])
    trials_b = run_b.get("trials", [])

    # Map scenario_id -> pass status (True if passed, False otherwise)
    a_results: dict[str, bool] = {}
    for t in trials_a:
        sc_id = t.get("scenario_id") or t.get("scenario_title", "unknown")
        passed = t.get("verdict") in ("PASS", "READINESS_APPROVED", "PASSED")
        a_results[sc_id] = passed

    b_results: dict[str, bool] = {}
    for t in trials_b:
        sc_id = t.get("scenario_id") or t.get("scenario_title", "unknown")
        passed = t.get("verdict") in ("PASS", "READINESS_APPROVED", "PASSED")
        b_results[sc_id] = passed

    common_scenarios = sorted(set(a_results.keys()) & set(b_results.keys()))

    both_pass = 0
    a_pass_b_fail = 0
    a_fail_b_pass = 0
    both_fail = 0

    regressions: list[str] = []
    improvements: list[str] = []

    for sc in common_scenarios:
        pass_a = a_results[sc]
        pass_b = b_results[sc]

        if pass_a and pass_b:
            both_pass += 1
        elif pass_a and not pass_b:
            a_pass_b_fail += 1
            regressions.append(sc)
        elif not pass_a and pass_b:
            a_fail_b_pass += 1
            improvements.append(sc)
        else:
            both_fail += 1

    contingency = (both_pass, a_pass_b_fail, a_fail_b_pass, both_fail)
    chi2, p_val, is_sig = compute_mcnemar_test(contingency, confidence=confidence)

    total_common = len(common_scenarios)
    rate_a = (both_pass + a_pass_b_fail) / total_common if total_common > 0 else 0.0
    rate_b = (both_pass + a_fail_b_pass) / total_common if total_common > 0 else 0.0
    delta = rate_b - rate_a

    if is_sig and delta < 0:
        verdict = "STATISTICALLY_SIGNIFICANT_REGRESSION"
    elif is_sig and delta > 0:
        verdict = "STATISTICALLY_SIGNIFICANT_IMPROVEMENT"
    else:
        verdict = "NO_STATISTICALLY_SIGNIFICANT_DIFFERENCE"

    return {
        "run_id_a": manifest_a.get("run_id", "run-a"),
        "run_id_b": manifest_b.get("run_id", "run-b"),
        "common_scenarios_count": total_common,
        "run_a_pass_rate": round(rate_a, 4),
        "run_b_pass_rate": round(rate_b, 4),
        "delta_pass_rate": round(delta, 4),
        "contingency_table": {
            "both_pass": both_pass,
            "a_pass_b_fail": a_pass_b_fail,
            "a_fail_b_pass": a_fail_b_pass,
            "both_fail": both_fail,
        },
        "mcnemar_chi2": chi2,
        "mcnemar_p_value": p_val,
        "is_statistically_significant": is_sig,
        "regressions": regressions,
        "improvements": improvements,
        "verdict": verdict,
    }
