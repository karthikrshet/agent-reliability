# Agent Reliability Lab (ARL) — Comprehensive vNext Technical Audit

**Date:** 2026-09-03  
**Auditor:** Senior AI Infrastructure & Reliability Engineering Team  
**Milestone:** Phase 0 Baseline Audit for vNext Evolution  
**Status:** Complete & Verified Against Repository Reality  

---

## 1. Current Architecture

Agent Reliability Lab is organized as a Python 3.12+ monorepo managed with `uv` / `pip` workspace editable packages, accompanied by a Next.js 15 App Router web dashboard:

```
agent-reliability-lab/
├── packages/
│   ├── core/               # Domain models (Trial, Run, FaultEvent, RFC 7807 DomainError), State Machine, ORM
│   ├── protocol/           # AgentAdapter interface, SessionContext, AgentInput, AgentOutput
│   ├── scenario-engine/    # JSON Schema Draft 2020-12 scenario parser and loader
│   ├── fault-engine/       # FaultScheduler mapping fault plans to invocations using deterministic PRNG
│   ├── execution-engine/   # TrialExecutor (turn loop) and ToolProxy (fault interception & execution)
│   ├── grading-engine/     # DeterministicTrialEvaluator (EffectMatch, Budgets), SemanticLLMJudge, Wilson CI, Pass@k
│   └── evidence/           # EvidenceCollector (SHA-256 hash chain ledger) and ReportGenerator
├── environments/
│   └── customer-support/  # Sandboxed domain environment with orders, customers, and inventory
├── adapters/
│   ├── http/               # Universal SSRF-hardened HTTP agent adapter
│   ├── openai-agents/      # ChatCompletions tool-calling adapter (supports OpenAI, Ollama, vLLM)
│   └── reference/          # MockAgentAdapter for unit testing (flagged is_reference_only)
├── apps/
│   ├── cli/                # agentlab CLI (Typer): run, validate, list-scenarios, doctor, verify
│   ├── mcp/                # Model Context Protocol stdio JSON-RPC 2.0 server (arl.mcp)
│   ├── server/             # FastAPI REST API with async SQLAlchemy persistence
│   ├── worker/             # Distributed background worker with PostgreSQL lease coordination
│   └── dashboard/          # Next.js 15 App Router frontend (TypeScript, TailwindCSS)
├── scenarios/              # 25 canonical scenario YAML definitions across 5 reliability dimensions
└── tests/                  # 30 test files covering unit, integration, concurrency, security, and live tests
```

---

## 2. Actually Implemented Capabilities

The following capabilities are fully implemented, actively tested, and verified in the codebase:

1. **Deterministic PRNG Fault Scheduling:** `FaultScheduler` uses `random.Random(seed)` isolated per trial. Given the same scenario and seed, fault scheduling is 100% reproducible.
2. **Tool Call Interception & Execution:** `ToolProxy` sits between the agent adapter and the environment. It checks the fault schedule before execution, logs a `FaultEvent`, and executes simulated fault behaviors or validates arguments against JSON Schema Draft 2020-12 before environment execution.
3. **Side-Effect-Committed Timeout Simulation:** `timeout_after_execution` fault with `side_effect_committed: true` executes the side-effect in the environment but returns a timeout error to the agent to test duplicate retries.
4. **25 Canonical Scenarios:** Defined in valid YAML and validated against strict schemas across tool correctness, error recovery, budget limits, multi-tenant isolation, and prompt injection.
5. **Deterministic Rule Grading:** `EffectMatchGrader` evaluates JMESPath expressions and dot-notation paths against post-trial world state and recorded tool calls using operators (`equals`, `not_equals`, `exists`, `not_exists`, `contains`, `matches`, `gt`, `gte`, `lt`, `lte`).
6. **Tamper-Evident SHA-256 Evidence Ledger:** `EvidenceCollector` computes `EvidenceLedgerBlock` links using `H(prev_chain_hash || payload_sha256 || evidence_id)` with full cryptographic verification (`verify_ledger_integrity`).
7. **Statistical Verification:** Wilson score 95% confidence intervals and unbiased Pass@k calculation (`calc_wilson_score_interval`, `calc_unbiased_pass_at_k`).
8. **SSRF Hardening:** `validate_url_for_ssrf` rejects private RFC 1918 IPs, link-local cloud metadata (`169.254.169.254`), embedded URL credentials (`user:pass@host`), and loopback addresses unless both `ARL_ENVIRONMENT=development` and `ARL_ALLOW_LOCALHOST_TARGETS=true` are explicitly set.
9. **Reference Provenance (Policy Rule 0):** Any trial executed with reference/mock agents is permanently stamped `is_reference_only=true`, forcing verdict `INSUFFICIENT_EVIDENCE` / `NON_PRODUCTION_REFERENCE` (0.0 score).
10. **Real Agent Execution:** Tested against real local Ollama models (`qwen2.5:0.5b`, `llama3.1`) and real external MCP agent platforms (`Career-Agents`).
11. **CLI Commands:** `agentlab validate`, `agentlab run`, `agentlab list-scenarios`, `agentlab doctor`, `agentlab verify`.

---

## 3. Partially Implemented Capabilities

1. **Fault Types:** `proxy.py` implements 12 fault branches (`http_500`, `http_503`, `http_429`, `dns_failure`, `connection_refused`, `dropped_response`, `timeout_before_execution`, `timeout_after_execution`, `malformed_json`, `schema_invalid_result`, `stale_result`, `partial_success`). They are stringly-typed in `_apply_fault_behavior` rather than modeled as a typed class hierarchy (`FaultSpec` / `FaultResult`) with parameter validation.
2. **Interception Boundary:** Interception currently operates inside `ToolProxy` wrapping an in-memory `EnvironmentProtocol`. There is no transparent reverse-proxy or transport-level interceptor for standalone external HTTP dependencies or arbitrary external MCP servers.
3. **Invariants:** Rule grading is tied to `scenario.expected_effects` and `forbidden_effects` inside `EffectMatchGrader`. It lacks a dedicated Invariant Engine with explicit `InvariantResult` records (`PASS`, `FAIL`, `ERROR`, `NOT_EVALUATED`), and lacks array/collection operators (`count_lte`, `count_gte`, `count_eq`, `not_contains`).
4. **Replay:** `agentlab verify` verifies evidence hash integrity, but there is no `agentlab replay <failure-id>` command to reconstruct execution or rerun with identical parameters from stored evidence.
5. **Reliability Gate:** CLI `run` supports `--threshold <float>`, but lacks an explicit CI-oriented `--gate` flag with baseline regression comparison, critical invariant overrides, and structured machine-readable exit summaries.

---

## 4. Missing Capabilities

1. **Typed Fault Abstractions:** First-class `FaultSpec` and `FaultResult` classes with explicit event tracking.
2. **Transparent Dependency Interception:** Reverse proxy for arbitrary external HTTP dependencies and MCP tool calls outside internal sandboxes.
3. **Deterministic Invariant DSL:** Formal invariant engine separate from effect graders with typed operators (`count_lte`, `count_gte`, `count_eq`, `not_contains`).
4. **Structured Disk Evidence Model:** Machine-readable run directories `.arl/runs/<run-id>/` containing `manifest.json`, `events.jsonl`, `faults.json`, `invariants.json`, `summary.json`.
5. **Stable Failure Identification:** `ARL-FAIL-<id>` classification records mapping violated invariants directly to first bad event and reproduction metadata.
6. **CLI Replay Command:** `agentlab replay <failure-id>` (evidence reconstruction) and `agentlab rerun <failure-id>` (deterministic re-execution).
7. **CI Reliability Regression Gate:** `agentlab test scenarios/ --gate` with baseline comparison, maximum regression thresholds, and critical invariant failure overrides.
8. **Career-Agents Chaos Benchmark:** Automated benchmark suite (`benchmarks/career_agents/`) evaluating Career-Agents across fault injection dimensions.
9. **Third-Party Agent Integration:** Integration testing against an independent open-source agent framework (LangGraph, OpenAI Agents SDK).

---

## 5. Dead / Unused Code

1. **Unused Dependencies in `pyproject.toml`:**
   - `redis`: Declared as an optional dependency in some pyproject files, but distributed worker lease coordination uses PostgreSQL (`SELECT ... FOR UPDATE SKIP LOCKED`), not Redis.
   - `alembic` & `testcontainers`: Referenced in pyproject notes but not actively imported in unit tests.
2. **Dashboard Legacy References:** Earlier demo arrays and mock constants were removed in the v0.2.1-beta.1 cleanup; `tests/test_no_fabricated_data.py` actively enforces this.

---

## 6. Mock / Demo-Only Functionality

1. **`MockAgentAdapter` (`adapters/reference/`):** Exists exclusively for unit tests. It is properly isolated with `is_reference_only=True` so it can never produce false production verdicts.
2. **Zero Fabricated Production Data:** No hardcoded mock runs, fake benchmark scores, or fabricated trajectories exist in production or dashboard code.

---

## 7. Security Concerns

1. **DNS Rebinding in SSRF Validation:** `validate_url_for_ssrf` validates IP addresses resolved at request configuration time. For live production agents targeting dynamic DNS names, asynchronous DNS resolution in HTTP clients could theoretically be vulnerable to DNS rebinding if an attacker controls the DNS server.
2. **Hardcoded Windows Path in Tests:** `tests/test_career_agents_reliability.py` originally used `D:/the project master/Career-Agents`. This must be made configurable via `ARL_CAREER_AGENTS_ROOT` with graceful skips on machines lacking the external workspace.
3. **Secret Redaction Completeness:** Ensure that all HTTP headers (`Authorization`, `Cookie`, `X-Api-Key`), tool arguments, and returned payloads are systematically sanitized before being ledgered into `EvidenceCollector` or written to disk.

---

## 8. Reliability Concerns

1. **Unbounded Event Memory Growth:** `EvidenceCollector` stores all evidence records in an in-memory dictionary `self.evidence_records`. For long-running trials with hundreds of tool calls, this should stream to append-only JSONL files on disk.
2. **Process Lifecycle for MCP Subprocesses:** When testing external MCP servers via subprocess, unexpected test abortion or unhandled exceptions must ensure child processes are terminated with a `finally` block or context manager.

---

## 9. Testing Gaps

1. **Multi-turn retry of `timeout_after_execution`:** While `ToolProxy` implements `timeout_after_execution`, there is no integration test verifying that an agent retry produces a duplicate side effect and triggers a critical invariant violation.
2. **Missing Operator Tests:** Current test suite does not exercise `count_lte`, `count_gte`, `count_eq`, or `not_contains`.
3. **Missing CLI Replay / Gate Tests:** Because `replay` and `--gate` are not yet implemented, there are zero tests for failure reproduction or baseline regression gating.

---

## 10. Architecture Debt

1. **Coupling in `ToolProxy`:** Schema validation, fault scheduling, fault simulation, latency timing, and execution dispatch are bundled into a single class.
2. **Dual Representation of Effects:** Scenarios define `expected_effects` and `forbidden_effects`, while the vision calls for a unified, typed `invariants` specification.
3. **Disjoint Evidence Formats:** The REST API, CLI, and EvidenceCollector format reports slightly differently. A unified `.arl/runs/<run-id>/` directory layout is needed.

---

## 11. Documentation Claims That Do Not Match Implementation

1. **"20 Chaos Behaviors":** The README matrix and diagrams mention 20 chaos fault types, but `_apply_fault_behavior` in `proxy.py` implements 12 distinct branches.
2. **`agentlab report` in Quickstart:** The README quickstart mentions `agentlab report --run-id latest --format markdown`, but `report` is not a registered CLI command in `apps/cli/src/arl/cli/main.py` (evidence verification is `agentlab verify`).

---

## 12. Recommended Changes

1. **Phase 1 (Fault Model):** Implement a typed `FaultSpec` and `FaultResult` domain model. Support the core 8 deterministic faults: `timeout`, `latency`, `http_429`, `http_500`, `connection_reset`, `malformed_response`, `empty_response`, `duplicate_response`, plus the critical distributed-systems failure: `timeout_after_effect`.
2. **Phase 2 (Interception):** Standardize tool call and HTTP interception with structured logging and secret redaction.
3. **Phase 3 (Invariant Engine):** Implement a standalone `InvariantEngine` with safe JMESPath traversal and typed operators: `eq`, `neq`, `lt`, `lte`, `gt`, `gte`, `exists`, `not_exists`, `count_eq`, `count_lte`, `count_gte`, `contains`, `not_contains`. Return typed `InvariantResult`.
4. **Phase 4 (Evidence Model):** Implement disk persistence in `.arl/runs/<run-id>/` (`manifest.json`, `events.jsonl`, `faults.json`, `invariants.json`, `summary.json`). Maintain existing SHA-256 hash chaining.
5. **Phase 5 (Failure Classification):** Generate structured `ARL-FAIL-<id>` records detailing violated invariants, fault history, and last known good event.
6. **Phase 6 (Replay):** Implement `agentlab replay <failure-id>` (evidence reconstruction) and `agentlab rerun <failure-id>` (deterministic re-execution).
7. **Phase 7 (CI Reliability Gate):** Implement `agentlab test scenarios/ --gate` with baseline comparison and non-zero exit code on critical invariant failure.
8. **Phase 8 (Career-Agents Integration):** Make `ARL_CAREER_AGENTS_ROOT` configurable and build a reproducible benchmark runner.

---

## 13. Things That Should NOT Be Changed

1. **State Machine (`packages/core/src/arl/core/state_machine.py`):** The formal execution lifecycle and its property-based invariant tests are mathematically sound and must remain untouched.
2. **Cryptographic Ledger Algorithm:** The SHA-256 hash chaining formula `H(prev || payload_sha || evidence_id)` is clean, verified, and tamper-evident.
3. **25 Canonical Scenarios:** The existing scenario definitions in `scenarios/` must remain valid and backwards-compatible.
4. **Statistical Formulae:** Wilson score confidence intervals and unbiased Pass@k in `grading_engine/stats.py` are rigorously tested and correct.
5. **SSRF Fail-Closed Invariants:** The strict localhost and private IP restrictions must never be weakened.

---

## 14. Baseline Verification Results

The test, type-check, and lint baseline was executed on 2026-09-03 prior to any architectural changes:

- **Pytest:** `161 passed, 2 skipped, 0 failed` in `42.66s`
- **Coverage:** `85.03%` (exceeding `--cov-fail-under=85`)
- **MyPy:** `0 errors` across 83 source files (`Success: no issues found in 83 source files`)
- **Ruff:** `0 errors` across 124 source files (`All checks passed!`, `124 files already formatted`)
- **Git Working Tree:** `main` branch, clean working tree (`14c1cc9` / `4c89576`)
