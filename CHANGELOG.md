# Changelog

All notable changes to **Agent Reliability Lab (ARL)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0-beta] - 2026-09-02

### Added
- **`agentlab doctor` command**: Automated diagnostic preflight check verifying Python environment, database connectivity, worker leases, agent endpoint reachability, scenario schemas, and secret redaction.
- **OpenAI-Compatible Agent Adapter** (`arl-adapter-openai`): Native support for testing remote agents implementing the OpenAI ChatCompletions & Tool Call contract.
- **10-Minute Real Agent Quickstart** (`examples/real-http-agent/`): Standalone runnable reference agent server demonstrating multi-turn tool calling and error recovery.
- **Comprehensive Threat Model** (`docs/security/threat-model.md`): Full asset mapping, trust boundaries, SSRF mitigations, DNS rebinding defenses, and prompt injection threat vectors.
- **Evaluation Metrics Guide** (`docs/evaluation-metrics.md`): Detailed statistical derivations for 95% Wilson score confidence intervals, Pass@k, and safety veto rules.
- **Developer Documentation Suite**: `docs/quickstart.md`, `docs/troubleshooting.md`, `docs/adapters.md`, `docs/scenario-authoring.md`, and `docs/deployment.md`.
- **Negative Security Test Suite** (`tests/test_security_negative.py`): Automated verification of SSRF blocking, private IP filtering, secret redaction, and SHA-256 evidence ledger tampering detection.
- **Next.js 15 Web Dashboard State Hardening**: Dedicated empty, loading, error, and disconnected states without fallback to mock benchmark telemetry.

### Changed
- Refactored `apps/cli/pyproject.toml` dependencies to match exact workspace package names (`arl-env-customer-support`, `arl-adapter-reference`, `arl-adapter-http`).
- Renamed all dashboard and documentation references from "thought process" to "observable execution trajectory" to protect model privacy.
- Updated GitHub Actions CI workflow with full dependency installation, strict MyPy, Ruff format/lint check, and Next.js 15 production build.

### Fixed
- Fixed hatchling editable build configuration for `apps/mcp` and subpackages by adding `[tool.hatch.build.targets.wheel]` tables.
- Fixed cp1252 Windows console encoding issue in `agentlab` CLI by replacing raw Unicode emojis with cross-platform ANSI formatters.

---

## [0.1.0] - 2026-09-02

### Added
- Initial release of Agent Reliability Lab core engine.
- 25 Canonical test scenarios across 5 reliability dimensions.
- 20 Deterministic chaos fault types with seed-controlled scheduling.
- `DeterministicTrialEvaluator`, `BudgetGrader`, and `SemanticLLMJudge`.
- Cryptographic SHA-256 evidence chain collector and report generator.
- FastAPI server (`apps/server/`) with RFC 7807 problem details.
- Model Context Protocol (MCP) server (`apps/mcp/`) over JSON-RPC 2.0 stdio.
- Next.js 15 App Router web dashboard (`apps/dashboard/`).
- MIT License and Contributor Covenant Code of Conduct.
