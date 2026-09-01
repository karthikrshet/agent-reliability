# ADR-002: EvaluationRun State Machine and Lifecycle Invariants

## Status
Accepted

## Date
2026-09-01

## Context
In evaluation and benchmarking platforms, runs often undergo complex distributed lifecycles across multiple workers and external API calls. Without strict state machine guarantees, race conditions, accidental double completions, or malicious attempts to alter finished evaluation verdicts can compromise integrity.

## Decision
We implement a strictly validated, immutable state machine (`EvaluationRunStateMachine`) with the following rules:
1. **Explicit Allowlist**: Transitions only occur through an allowlisted transition graph (`CREATED -> VALIDATING -> QUEUED -> PROVISIONING -> RUNNING -> GRADING -> AGGREGATING -> COMPLETED`).
2. **Terminal State Immutability**: States `COMPLETED`, `FAILED`, `CANCELLED`, and `TIMED_OUT` are strictly terminal. Attempting to transition out of a terminal state raises `TerminalStateImmutableError`.
3. **Audited Transitions**: Every state transition returns an immutable `StateTransition` record with timestamps, actor identity, reason, and optimistic version numbers.
4. **Optimistic Concurrency**: Monotonically increasing version counters prevent lost updates in concurrent distributed worker environments.

## Consequences

### Positive
- Prevents post-hoc manipulation of evaluation scores or test verdicts.
- Clear cancellation flow: `CANCEL_REQUESTED` is propagated and workers gracefully terminate before entering `CANCELLED`.
- Full auditability for every evaluation run transition.

### Negative
- All callers and workers must explicitly handle state transition errors and respect transition prerequisites.
