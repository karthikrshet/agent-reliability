# ADR-005: Deterministic Seed-Controlled Fault Injection Architecture

## Status
Accepted

## Date
2026-09-01

## Context
Production readiness requires testing how AI agents behave when downstream tools, APIs, and networks fail (e.g. rate limits, HTTP 500s, timeouts, stale data, dropped responses). However, nondeterministic fault generation makes flaky test debugging impossible.

## Decision
We implement a seed-controlled fault scheduler (`FaultScheduler` in `arl-fault-engine`):
1. **Isolated RNG**: The scheduler uses an isolated `random.Random(seed)` instance initialized with a trial-specific derived seed (`derive_trial_fault_seed(run_seed, trial_index)`).
2. **Proxy Layer Injection**: Faults are intercepted and injected at the tool proxy layer without monkey-patching global standard libraries.
3. **Pre-Injection Audit**: A `FaultEvent` record is constructed and persisted before the fault behavior is applied to ensure full auditability even during worker crashes.

## Consequences

### Positive
- Guarantee of determinism: identical run seed + scenario version produces the exact same fault schedule every time.
- 20 standardized fault types covering network, HTTP, data, and system-level failures.
- Zero leakage of random state between concurrent evaluation trials.

### Negative
- Dynamic runtime triggers dependent on complex external timing require calibrated delay parameters.
