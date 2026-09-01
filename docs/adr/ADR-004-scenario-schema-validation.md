# ADR-004: Scenario Specification Schema and Fail-Closed Validation

## Status
Accepted

## Date
2026-09-01

## Context
Scenarios define the test suite for agent evaluations: initial state, conversation openers, fault injection plans, budgets, expected effects, and forbidden side effects. Unvalidated or loosely validated scenario formats can cause silent test skips, undefined grader states, or false passes.

## Decision
We enforce a strict JSON Schema (Draft 2020-12) with fail-closed validation:
1. Every scenario must specify an explicit `schema_version` (e.g. `"1.0"`).
2. Unknown fields, missing budgets, or unrecognized fault types immediately fail validation.
3. Loading raises `ScenarioValidationError` with all detected issues; partial execution of malformed scenarios is strictly prohibited.
4. Each scenario version is hashed (SHA-256) to ensure historical execution integrity.

## Consequences

### Positive
- Prevents silent test drift and guarantees reproducible test specifications.
- Clear error messages during scenario authoring and CI schema checks.

### Negative
- Authors must conform strictly to the versioned schema; schema updates require explicit version bumps.
