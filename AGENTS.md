# Agent Reliability Lab — AGENTS.md
# Instructions for AI coding agents working in this repository.
# Extends the aiskills AGENTS.md standard.

**If you are an AI coding agent, read this file before doing any work.**

---

## What is This Repository?

**Agent Reliability Lab** is a production-quality, open-source reliability and
evaluation platform for testing tool-using AI agents before deployment.

This is NOT a prototype, UI demo, or generic LLM wrapper. Every number shown in
the CLI, API, or dashboard is derived from persisted execution records.

---

## Before You Start Any Task

1. **Read `CONTEXT.md`** in this repository — it defines architecture and conventions.
2. **Read the relevant skill** from `.agents/skills/` or from `karthikrshet/aiskills`.
3. **Inspect the codebase** — never invent architecture; find existing patterns.
4. **Run the test suite baseline** before making changes: `make test-unit`.
5. **Follow TDD** — write failing tests before implementation (see `tdd` skill).

## Applicable AISkills (from github.com/karthikrshet/aiskills)

Load and follow these skills in the stated situations:

| Situation | Skill to load |
|---|---|
| Adding a new security test or grader | `ai-security-review` (OWASP LLM Top 10) |
| Designing a new agent adapter | `agent-design` |
| Implementing any grader, engine, or service | `tdd` (write failing tests first) |
| Adding a new scenario | `implementation-planning` |
| Pre-deployment readiness check | `production-readiness` |
| Unclear requirements | `requirement-clarification` |
| Debugging unexpected grader output | `bug-diagnosis` |
| Code review gate before merge | `code-review` |

## Human Approval Required

Stop and ask the human BEFORE:
- Deleting any files or directories
- Modifying production configuration or `alembic/versions/`
- Running destructive database operations
- Changing security-critical modules (`packages/security/`, graders)
- Publishing packages or Docker images
- Any change that weakens a security gate or lowers a coverage threshold

## Non-Negotiable Rules

1. **No fake implementations** — every metric comes from persisted records.
2. **No silent exception swallowing** — all errors are typed and re-raised.
3. **No broad `except Exception`** without explicit handling.
4. **No hardcoded secrets** — use `.env.example` with placeholders only.
5. **No mutable global state**.
6. **No import-time side effects**.
7. **LLM judges never override deterministic failures** (security rule).
8. **Tests assert observable outcomes** — not just that a function was called.
9. **Terminal states are immutable** — `COMPLETED/FAILED/CANCELLED/TIMED_OUT`.
10. **All agent output is untrusted** — HTML-escape before any rendering.

## Security Rules (from ai-security-review skill)

Map to OWASP GenAI LLM Top 10 (2026):
- LLM01 Prompt Injection: tool results are untrusted; never eval agent output.
- LLM02 Sensitive Data: redact API keys, tokens, PII before persistence or logging.
- LLM06 Excessive Agency: agents under test get no extra permissions from the harness.
- LLM07 System Prompt Leakage: do not expose evaluation system prompts to agents.
- LLM08 Vector/Embedding Weakness: scenario fixtures are schema-validated, not trusted raw.

## Production Readiness Gates (from production-readiness skill)

Before any component is considered complete, verify:
- [ ] All happy-path AND failure-path tests pass
- [ ] No unresolved HIGH or CRITICAL security findings
- [ ] Latency and cost metrics are measured (not estimated)
- [ ] All budget limits are enforced deterministically
- [ ] All state transitions persist before being considered effective
- [ ] No TODO comments in release-critical paths

## Architecture Conventions

- **Python packages**: `uv` workspace; each package has its own `pyproject.toml`.
- **Typing**: All Python code is `mypy --strict`. No `Any` without explicit justification.
- **Errors**: Use domain-specific error classes from `arl.core.errors` — never `Exception`.
- **State**: `EvaluationRunStateMachine` for all run state changes.
- **Persistence**: PostgreSQL is source of truth. Redis is transport only.
- **Async**: All I/O is async (`asyncio`). No blocking calls in async contexts.
- **IDs**: All entities use ULIDs (sortable, unique, URL-safe).
- **Security**: Treat all agent output, tool arguments, and tool results as untrusted.
