# Agent Reliability Lab (ARL)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12%2B-blue.svg" alt="Python 3.12+" />
  <img src="https://img.shields.io/badge/Typing-Strict%20PEP%20561-brightgreen.svg" alt="Strict Typing" />
  <img src="https://img.shields.io/badge/Coverage-85.8%25-success.svg" alt="Test Coverage" />
  <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License" />
  <img src="https://img.shields.io/badge/Architecture-Monorepo%20(uv%20%2B%20pnpm)-orange.svg" alt="Architecture" />
</p>

> **Agent Reliability Lab (ARL)** is a production-readiness evaluation and verification platform for tool-using AI agents. It rigorously tests whether an agent can complete stateful multi-step tasks, recover from network and infrastructure faults, maintain data boundaries, control cost/tokens, and prevent unauthorized external side effects before deployment.

---

## 🎯 Key Capabilities

- **Deterministic Rule & Semantic Grading**: Combines sub-millisecond AST/JMESPath deterministic effect matchers with structured schema-validated LLM judges.
- **Fail-Closed Safety Invariant**: Violations of security boundaries or detected forbidden side effects trigger an immediate non-negotiable **Safety Veto** (`CRITICAL_FAIL`), which cannot be overridden by qualitative judge scores.
- **Controlled Fault Injection**: Injects 20 real-world fault behaviors (timeouts, partial payloads, rate limits, schema corruption, 500/503 errors, duplicate requests) with seed-controlled deterministic replayability.
- **Statistical Rigor**: Computes asymmetric **95% Wilson score confidence intervals** and unbiased **pass@k** estimators ($k=1, 3, 5$) rather than naive point-estimate percentages.
- **Immutable SHA-256 Evidence Ledger**: Every verdict is backed by an auditable cryptographic hash chain linking world state snapshots, tool invocations, and fault logs.
- **Framework-Independent Protocol**: Standard async streaming protocol compatible with LangChain, LlamaIndex, AutoGen, CrewAI, OpenAI Assistants, or raw HTTP/SSE agents with built-in SSRF defense.

---

## 🏗 Architecture Overview

```
agent-reliability-lab/
├── packages/
│   ├── core/               # 28 typed domain entities, error hierarchy, state machine, storage models
│   ├── protocol/           # AgentAdapter protocol, session contexts, streaming generator interfaces
│   ├── scenario-engine/    # JSON Schema 2020-12 validator and 25 canonical test scenario definitions
│   ├── fault-engine/       # Seed-controlled fault scheduler supporting 20 interception behaviors
│   ├── execution-engine/   # Intercepting ToolProxy and budget-enforcing multi-turn TrialExecutor
│   ├── grading-engine/     # Deterministic rule graders, semantic LLM judges, Wilson CI & pass@k stats
│   └── evidence/           # SHA-256 cryptographic ledger collector and Markdown/JSON audit reporter
├── environments/
│   └── customer-support/   # Stateful multi-tenant retail sandbox (orders, refunds, shipping, carts)
├── adapters/
│   ├── reference/          # Deterministic mock adapter for offline benchmarking and unit tests
│   └── http/               # HTTP/SSE agent adapter with private IP and loopback SSRF defenses
├── apps/
│   ├── worker/             # Distributed background worker with PostgreSQL SKIP LOCKED leasing
│   └── server/             # FastAPI evaluation server & task queue orchestrator
├── scenarios/              # 25 production scenarios across 5 critical reliability categories
└── docs/adr/               # Architecture Decision Records (ADR-001 through ADR-005)
```

---

## 🧪 25 Canonical Reliability Scenarios

ARL ships with 25 ready-to-run scenarios covering 5 critical production dimensions:

| Category | Scenarios | Target Verification |
| :--- | :--- | :--- |
| **Tool Correctness** | `tc-01` to `tc-05` | Argument validation, correct tool selection, parameter hallucination prevention, call sequencing |
| **Failure Recovery** | `fr-01` to `fr-05` | HTTP 500 retry, timeout exponential backoff, rate limit handling, partial payload recovery |
| **State & Memory** | `sm-01` to `sm-05` | Multi-turn constraint retention, state mutation tracking, transaction rollback on failure |
| **Security & Isolation** | `sec-01` to `sec-05` | Cross-tenant data isolation, prompt injection via tool outputs, PII masking, system prompt defense |
| **Resource Control** | `rc-01` to `rc-05` | Infinite tool-loop termination, turn budget capping, cost budget and token ceiling enforcement |

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.12+**
- **uv** (fast Python package manager)
- **Node.js 20+ & pnpm** (for web dashboard & frontend workspace)

### Installation

```bash
# Clone the repository
git clone https://github.com/karthikrshet/agent-reliability.git
cd agent-reliability

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Running the Test Suite

```bash
# Execute unit, property-based, and integration tests across all packages
pytest -v --cov=. --cov-fail-under=85

# Run strict type checking (0 errors across 45 source files)
mypy packages/ apps/ adapters/ environments/

# Run code style and linter checks
ruff check .
```

---

## 📊 Evaluation Report Sample

Each evaluation run produces an immutable audit record and rich summary report:

```markdown
# Agent Reliability Lab — Evaluation Audit Report
**Readiness Verdict**: 🟢 READY FOR PRODUCTION (95% Wilson Lower Bound: 88.4%)
**Evidence Chain Hash**: `3f8a91c78...` (Tamper-evident chain verified ✅)

| Category | Completed | Passed | Pass Rate | 95% Wilson CI | Pass@3 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `tool-correctness` | 5 / 5 | 5 | 100.0% | [56.6%, 100.0%] | 1.000 |
| `failure-recovery` | 5 / 5 | 5 | 100.0% | [56.6%, 100.0%] | 1.000 |
| `state-and-memory` | 5 / 5 | 5 | 100.0% | [56.6%, 100.0%] | 1.000 |
| `security` | 5 / 5 | 5 | 100.0% | [56.6%, 100.0%] | 1.000 |
| `resource-control` | 5 / 5 | 5 | 100.0% | [56.6%, 100.0%] | 1.000 |
```

---

## 🛡 Security Mandates

1. **Deterministic Veto**: Security violations, prompt injection leakages, or cross-tenant data corruption immediately force a `CRITICAL_FAIL` verdict.
2. **SSRF Defense**: The HTTP Adapter enforces strict DNS resolution and blocks private (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.0/8`, `::1`), link-local, and cloud metadata (`169.254.169.254`) addresses.
3. **Optimistic Locking**: Every state transition in the evaluation run lifecycle uses optimistic version locking (`version_id`) to eliminate race conditions.

---

## 👤 Author & Maintainer

- **Author**: **Karthik Rajesh Shet** ([@karthikrshet](https://github.com/karthikrshet))
- **Email**: `kartikrshet@gmail.com`
- **Repository**: [https://github.com/karthikrshet/agent-reliability](https://github.com/karthikrshet/agent-reliability)

---

## 📜 License

Distributed under the **Apache License 2.0**. See [`LICENSE`](./LICENSE) for more information.
