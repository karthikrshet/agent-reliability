# ADR-001: Monorepo Architecture and Package Layout

## Status
Accepted

## Date
2026-09-01

## Context
Agent Reliability Lab (ARL) is an open-source evaluation and production-readiness testing platform for AI agents. The project requires several distinct subsystems:
- Domain models and core error primitives (`arl-core`)
- Framework-agnostic agent adapter protocols (`arl-protocol`)
- Scenario schemas, validation, and fail-closed loading (`arl-scenario-engine`)
- Seed-controlled deterministic fault injection (`arl-fault-engine`)
- Stateful sandboxed test environments (`environments/`)
- REST/gRPC API and execution orchestrator (`apps/api`, `apps/worker`)
- Modern web dashboard (`apps/web`)

We needed to decide between multiple independent repositories or a unified monorepo.

## Decision
We adopted a unified monorepo structure using:
- **Python**: `uv` workspace with independently versioned Hatchling/wheel packages under `packages/`
- **TypeScript**: `pnpm` workspace under `apps/`
- **Scenarios**: Declarative YAML scenario specifications under `scenarios/`

Each package maintains its own `pyproject.toml` or `package.json`, isolated dependencies, and strict type checking boundaries (`mypy --strict`, `tsc --noEmit`).

## Consequences

### Positive
- Unified versioning, atomic commits, and seamless cross-package refactoring.
- Single CI pipeline validating core models, scenario schemas, fault schedulers, and adapters together.
- Simplified local development with Docker Compose and standard `Makefile` recipes.

### Negative
- Monorepo tooling setup requires workspace-aware configuration across Python and Node.
- Care must be taken to prevent circular dependency cycles between packages (enforced via top-down dependency rules: `core` -> `protocol` / `scenario-engine` -> `fault-engine` -> `execution-engine`).
