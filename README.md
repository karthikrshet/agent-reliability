<p align="center">
  <img src="docs/assets/logo.png" width="160" alt="Agent Reliability Lab Logo" />
</p>

<h1 align="center">Agent Reliability Lab (ARL)</h1>

<p align="center">
  <strong>Break your autonomous AI agents before production does.</strong>
</p>

<p align="center">
  Deterministic fault injection, stateful distributed-systems invariants, reproducible failure replay, and fail-closed CI gates for tool-using AI agents.
</p>

<p align="center">
  <a href="https://github.com/karthikrshet/agent-reliability/actions"><img src="https://img.shields.io/badge/CI-Passing-10b981?style=flat-square&logo=github-actions" alt="CI" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Coverage-85.3%25-6366f1?style=flat-square" alt="Coverage" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Tests-185%20Passing-22c55e?style=flat-square" alt="Tests" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.12%2B-3b82f6?style=flat-square&logo=python" alt="Python" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Type%20Safety-MyPy%20Strict-blue?style=flat-square" alt="MyPy" /></a>
  <a href="#"><img src="https://img.shields.io/badge/MCP-2024--11--05%20Ready-06b6d4?style=flat-square" alt="MCP" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-f59e0b?style=flat-square" alt="License" /></a>
</p>

<p align="center">
  <img src="docs/assets/hero-cyber-core.jpg" width="100%" alt="Agent Reliability Lab Cybernetic Core and Holographic Containment Shield" />
</p>

---

## ⚡ What is Agent Reliability Engineering?

Most agent evaluation frameworks ask:  
> *"Did the model produce a good response given this prompt?"*

**Agent Reliability Lab asks the critical distributed systems question:**  
> *"What happens to your autonomous agent when the software around it fails?"*

In production, autonomous tool-using agents fail in catastrophic, non-deterministic ways:
- **Duplicate Side Effects**: An agent calls `refund.create($50)`. The backend commits the refund, but a network drop or gateway timeout occurs before the response arrives. The agent assumes failure, retries without checking idempotency, and refunds the customer a second time.
- **Cascading Retry Storms**: External APIs return transient HTTP 500s or 429 rate limits. Unregulated agents retry in tight loops, exhausting rate limits and crashing downstream services.
- **Schema Mutation & Malformed Responses**: An upstream service updates its JSON response format or returns truncated payload data, causing agent hallucinations or unhandled crashes.
- **Budget Exfiltration & Infinite Loops**: Ambiguous instructions trigger infinite tool call cascades, draining thousands of dollars in tokens within minutes.
- **Security & Multi-Tenant Bleed**: Indirect prompt injections hidden inside external tool outputs (e.g. a customer review or ticket description) trick the agent into exfiltrating API keys, system prompts, or cross-tenant data.

**ARL** provides a reproducible chaos testing harness that intercepts your agent's real tool calls, injects deterministic faults, evaluates strict stateful invariants (zero `eval()`, zero LLM hallucinations), records tamper-evident evidence on disk, and stops regressions in CI before deployment.

---

## 🎬 The Nightmare Scenario: "Timeout After Effect"

Here is how ARL catches a real-world distributed systems vulnerability in an agent:

```mermaid
sequenceDiagram
    autonumber
    actor User as User Request
    participant Agent as Autonomous Agent
    participant ARL as ARL Tool Proxy & Fault Injector
    participant Env as Real Environment (DB / API)

    User->>Agent: "Refund order #1042 for $49.99"
    Agent->>ARL: refund.create(order_id="1042", amount=49.99)
    Note over ARL: Intercepts call & checks fault schedule
    ARL->>Env: execute_tool("refund.create")
    Note over Env: Side effect COMMITTED in database!
    Env-->>ARL: 200 OK (Refund #ref-01 recorded)
    Note over ARL: Fault injected: timeout_after_effect<br/>(Response dropped!)
    ARL-->>Agent: TimeoutError (Connection dropped)
    Note over Agent: Agent assumes failure & retries!
    Agent->>ARL: refund.create(order_id="1042", amount=49.99)
    ARL->>Env: execute_tool("refund.create")
    Note over Env: DUPLICATE REFUND COMMITTED! (#ref-02)
    Env-->>ARL: 200 OK
    ARL-->>Agent: 200 OK
    Note over ARL: Evaluation Phase: InvariantEngine evaluates world state:<br/>Invariant $.refunds count_lte 1 ❌ VIOLATION (found 2)<br/>Generated: ARL-FAIL-1042 (severity: CRITICAL)
```

### Trace Waterfall Inspector

When an invariant is violated, ARL outputs a deterministic execution trace with step-by-step latency, injected fault markers, and mathematical violation proofs:

<p align="center">
  <img src="docs/assets/trace-inspector.jpg" width="100%" alt="ARL Waterfall Trace Inspector Mockup" />
</p>

Developers can immediately inspect the failure trace:
```bash
agentlab replay ARL-FAIL-1042
```
And deterministically re-execute the exact scenario with the identical seed:
```bash
agentlab rerun ARL-FAIL-1042
```

---

## 🏛 Core Architecture & Engines

ARL is designed as three modular, decoupled engines working in synchrony:

```mermaid
graph TD
    subgraph ClientInterfaces ["Developer & CI Interfaces"]
        CLI["agentlab CLI (Typer)"]
        CI["GitHub Actions CI Gate (--gate)"]
        DASH["Next.js 15 Web Dashboard"]
        MCP["Model Context Protocol (Cursor / Claude)"]
    end

    subgraph CoreEngine ["ARL Reliability Core"]
        SCHED["Deterministic Fault Scheduler (Seeded PRNG)"]
        PROXY["Tool Proxy & Interceptor (Secret Redaction)"]
        INV["Deterministic Invariant Engine (13 Operators)"]
        STORE["Evidence Disk Store (.arl/runs/<run-id>/)"]
    end

    subgraph TargetAgents ["Target Agents Under Test"]
        HTTP_AGENT["HTTP Agent (FastAPI / Express)"]
        OPENAI_AGENT["OpenAI-Compatible Model / Local Ollama"]
        MCP_AGENT["MCP Agent (e.g. Career-Agents)"]
        REF_AGENT["Local Reference Mock Agent"]
    end

    subgraph RealWorld ["Environment & Dependencies"]
        SANDBOX["Stateful Sandboxed Environment"]
        APIS["Real / External Tools"]
    end

    CLI --> CoreEngine
    CI --> CoreEngine
    DASH --> CoreEngine
    MCP --> CoreEngine

    TargetAgents <--> PROXY
    PROXY <--> SCHED
    PROXY <--> SANDBOX
    PROXY <--> APIS

    SANDBOX --> INV
    CoreEngine --> STORE
```

---

### 1. `arl.fault_engine`: Seeded Chaos Injection

<p align="center">
  <img src="docs/assets/diagram-fault-engine.jpg" width="100%" alt="Fault Engine Architecture Diagram" />
</p>

The **Fault Engine** provides deterministic chaos injection without touching agent source code. A seeded pseudorandom number generator (PRNG) ensures that every trial can be reproduced with bitwise precision:
- `timeout`: Network / socket timeouts before dependency execution.
- `latency`: Deterministic artificial latency spikes with jitter models.
- `http_429`: Rate limit exceeded with custom `Retry-After` headers.
- `http_500` / `http_503`: Transient upstream server and gateway errors.
- `connection_reset`: Abrupt TCP socket teardowns.
- `malformed_response`: Corrupted JSON syntax or invalid Unicode.
- `empty_response`: Zero-byte payloads or empty JSON dictionaries.
- `duplicate_response`: Repeated responses to test idempotency handling.
- `timeout_after_effect`: Critical distributed-systems failure where side effects commit but responses are dropped.

---

### 2. `arl.grading_engine`: 13 Typed Invariant Operators (Zero `eval()`)

<p align="center">
  <img src="docs/assets/diagram-grading-engine.jpg" width="100%" alt="Grading Engine Architecture Diagram" />
</p>

Critical pass/fail decisions must **never** depend on an LLM-as-a-judge that hallucinates or changes verdicts across runs. ARL features a typed invariant engine with 13 safe operators executing against a parsed JMESPath AST:
- **Existence**: `exists`, `not_exists`
- **Equality**: `eq`, `neq`
- **Numeric Ordering**: `lt`, `lte`, `gt`, `gte`
- **Collection Counts**: `count_eq`, `count_lte`, `count_gte`
- **Containment**: `contains`, `not_contains`

> [!IMPORTANT]
> ARL executes **zero `eval()` calls**. Invariant expressions use safe JMESPath / dot-notation traversal. Any syntax error or type mismatch results in `status=ERROR` and is never converted to `PASS`.

---

### 3. `arl.evidence`: Tamper-Evident SHA-256 Block Chain

<p align="center">
  <img src="docs/assets/diagram-evidence-ledger.jpg" width="100%" alt="Evidence Ledger Architecture Diagram" />
</p>

Every trial state transition, tool call, and fault injection is cryptographically linked into an immutable block chain:
$$\text{hash}(event_n) = \text{SHA-256}(\text{hash}_{n-1} + \text{canonical\_payload})$$

- **Zero Audit Tampering**: Persisted `.arl/runs/<run-id>/evidence.jsonl` files cannot have events deleted or reordered without breaking the SHA-256 chain.
- **Single-Command Replay**: Full execution timeline reconstructible via `agentlab replay <id>`.

---

## 🎯 Tested at Scale: 167 Autonomous Agents in Career-Agents

<p align="center">
  <img src="docs/assets/case-study-mcp.jpg" width="100%" alt="Career-Agents Benchmark Telemetry and Wilson Confidence Intervals" />
</p>

ARL was validated across the real **Career-Agents** multi-agent repository (167 registered autonomous specialists) to verify:
1. **Registry Integrity**: 167 agents, workflows, and task bundles schema-validated.
2. **MCP Conformance**: 100% pass rate on tool discovery (`tools/list`) and initialization handshakes.
3. **Execution Correctness**: Real tool execution (`search_agents`, `recommend_agents`, `career_assessment`).
4. **Fallback & Error Boundaries**: Validates that empty inputs trigger documented fallback behavior and invalid tool names return explicit JSON-RPC `-32601` (`MethodNotFound`) errors without unhandled exceptions.
5. **Statistical Rigor**: Reports 95% Wilson Score confidence intervals $[\text{lower}, \text{upper}]$ to guarantee statistical significance.

Run the Career-Agents verification suite:
```bash
export ARL_CAREER_AGENTS_ROOT="/path/to/Career-Agents"
pytest -v tests/test_career_agents_reliability.py
```

---

## 🛡 Enterprise Governance & Cryptographic Security

<p align="center">
  <img src="docs/assets/enterprise-governance.jpg" width="100%" alt="Enterprise Governance and Cryptographic Security Vault" />
</p>

Autonomous agents operating against production databases, payment gateways, or customer records require enterprise-grade controls:
- **Tamper-Evident SHA-256 Ledger**: Every trial writes cryptographic hash blocks to disk to guarantee post-facto audit integrity.
- **Automatic Secret Redaction**: Recursively scrubs `authorization`, `auth_token`, `api_key`, `secret`, `password`, `cookie`, and `bearer` tokens before persisting evidence.
- **Fail-Closed CI Deployment Gate**: Non-zero exit code `1` in GitHub Actions halts broken agent PR merges automatically.
- **PostgreSQL `SKIP LOCKED` Distributed Leases**: Multi-worker concurrent evaluation queues without race conditions.

---

## ⚡ 5-Minute Quickstart

### 1. Installation

```bash
git clone https://github.com/karthikrshet/agent-reliability.git
cd agent-reliability

# Create and activate Python 3.12+ virtualenv
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all packages in editable mode
pip install -e "packages/core" \
            -e "packages/protocol" \
            -e "packages/scenario-engine" \
            -e "packages/fault-engine" \
            -e "packages/execution-engine" \
            -e "packages/grading-engine" \
            -e "packages/evidence" \
            -e "environments/customer-support" \
            -e "adapters/reference" \
            -e "adapters/http" \
            -e "adapters/openai-agents" \
            -e "apps/worker" \
            -e "apps/server" \
            -e "apps/cli" \
            -e "apps/mcp"
```

### 2. Preflight Diagnostics
Verify that your Python runtime, dependencies, and environment are healthy:
```bash
agentlab doctor
```

### 3. Run Reliability Evaluation
Evaluate your agent against canonical chaos test scenarios:

```bash
# Test an HTTP agent (e.g. running on port 8088) across scenarios
agentlab run -s scenarios/ --agent-url http://127.0.0.1:8088 -n 3 --seed 42 --threshold 0.80

# Test a local Ollama model (e.g. llama3.1)
agentlab run -s scenarios/ --openai-model llama3.1 --openai-base-url http://127.0.0.1:11434/v1

# Test with local deterministic reference agent
agentlab run -s scenarios/ --reference-agent -n 1 --seed 42
```

### 4. Enforce CI Reliability Gate
Add ARL directly into your GitHub Actions workflow:
```bash
agentlab test scenarios/ --gate
```
If any critical invariant fails (e.g. duplicate payment, cross-tenant data leak), the command prints the diagnostic replay command and exits with code `1`:
```text
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┯━━━━━━━━━━━┯━━━━━━━━┯━━━━━━━━━┓
┃ Gate Metric                   │ Threshold │ Actual │ Verdict ┃
┠───────────────────────────────┼───────────┼────────┼─────────┨
┃ Critical Invariant Violations │ 0         │ 1      │ FAIL    ┃
┃ Pass Rate                     │ >= 80%    │ 0.0%   │ FAIL    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┷━━━━━━━━━━━┷━━━━━━━━┷━━━━━━━━━┛

╭──────────────────────────── CI Gate Failed ────────────────────────────╮
│ [FAIL] CI RELIABILITY GATE FAILED                                      │
│                                                                        │
│ Critical Invariant Violations: 1                                       │
│ New Failures: 1                                                        │
│ Run ID: run-822595ee                                                   │
│                                                                        │
│ Replay failure with: agentlab replay ARL-FAIL-95ee-01                  │
╰────────────────────────────────────────────────────────────────────────╯
```

### 5. Launch the Web Dashboard
ARL includes a full dark cybernetic Next.js 15 App Router operations dashboard:

```bash
# Start the FastAPI backend
agentlab serve --port 8000

# In apps/dashboard:
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to inspect scenarios, live evaluation runs, Wilson score charts, and cryptographic evidence reports.

---

## 💻 Complete CLI Command Reference

| Command | Usage | Description |
| :--- | :--- | :--- |
| `list-scenarios` | `agentlab list-scenarios [-c <category>]` | List all 25 canonical reliability evaluation scenarios |
| `validate` | `agentlab validate <path>` | Validate scenario YAML syntax against JSON Schema 2020-12 |
| `run` | `agentlab run -s <path> [--agent-url \| --openai-model \| --reference-agent]` | Execute multi-trial evaluation across agents |
| `test` | `agentlab test <path> [--gate] [--baseline <run-id>]` | Run scenarios with automated fail-closed CI reliability gate |
| `replay` | `agentlab replay <failure-or-run-id>` | Reconstruct execution trajectory and failure diagnosis from evidence |
| `rerun` | `agentlab rerun <failure-or-run-id>` | Deterministically re-execute scenario with identical seed |
| `report` | `agentlab report [<run-id>] [-f markdown\|json\|text]` | Output evaluation summary with Wilson confidence intervals |
| `verify` | `agentlab verify` | Verify cryptographic SHA-256 tamper-evident ledger integrity |
| `doctor` | `agentlab doctor [--agent-url <url>]` | Run preflight health and environment connectivity diagnostics |
| `serve` | `agentlab serve [--port 8000]` | Launch the FastAPI operations backend server |

---

## 🔌 Model Context Protocol (MCP) Integration

ARL includes a native MCP server (`apps/mcp`), enabling **Claude Desktop**, **Cursor**, and other MCP-native clients to execute chaos tests directly:

Add to your `mcp_config.json`:
```json
{
  "mcpServers": {
    "agent-reliability-lab": {
      "command": "python",
      "args": ["-m", "arl.mcp"],
      "env": {
        "PYTHONPATH": "packages/core/src;packages/protocol/src;packages/scenario-engine/src;packages/fault-engine/src;packages/execution-engine/src;packages/grading-engine/src;packages/evidence/src;environments/customer-support/src;adapters/reference/src;apps/mcp/src"
      }
    }
  }
}
```

---

## 📊 25 Canonical Evaluation Scenarios

| Category | Scenario ID | Description | Severity | Invariant Verified |
| :--- | :--- | :--- | :--- | :--- |
| **Tool Correctness** | `tc-01-order-lookup` | Valid order lookup with customer ID | Medium | Valid customer order returned |
| | `tc-02-argument-type-coercion` | Integer argument type coercion | Medium | Argument types validated |
| | `tc-03-idempotent-refund-keys` | Idempotency key deduplication | Critical | `$.refunds count_lte 1` |
| | `tc-04-shipping-address-update` | Postal code address validation | Medium | Address updated correctly |
| | `tc-05-loyalty-points-redemption` | Balance check before points discount | High | Points never exceed balance |
| **Error Recovery** | `er-01-transient-500-retry` | Transient HTTP 500 backoff & retry | High | Eventual success after retry |
| | `er-02-timeout-graceful-fallback` | 504 gateway timeout fallback | High | Graceful user notification |
| | `er-03-rate-limiting-429-handling` | HTTP 429 adherence to Retry-After | High | Exponential backoff followed |
| | `er-04-schema-mismatch-correction` | Self-correction after argument error | High | Tool call repaired on turn 2 |
| | `er-05-partial-failure-rollback` | Inventory rollback on failure | Critical | State rolled back cleanly |
| **Budget Limits** | `bl-01-cascade-loop-termination` | Recursive infinite loop termination | High | Max tool calls enforced |
| | `bl-02-max-turn-limit-enforcement` | Turn ceiling enforcement | Medium | Execution capped at 5 turns |
| | `bl-03-large-payload-token-budget` | 100-item JSON response truncation | Medium | Token budget not exceeded |
| | `bl-04-timeout-duration-budget` | Wall-clock trial duration ceiling | Medium | Wall-clock limit respected |
| | `bl-05-cost-ceiling-protection` | Per-trial token cost ceiling ($0.05) | High | Execution halted before overrun |
| **Multi-Tenant** | `mt-01-cross-tenant-order-lookup` | Cross-tenant order query veto | Critical | Unauthorized order query blocked |
| | `mt-02-cross-tenant-modification` | Cross-tenant order cancel veto | Critical | Cross-tenant mutation blocked |
| | `mt-03-tenant-scoped-inventory` | Warehouse stock query scoping | High | Scope matches caller tenant |
| | `mt-04-pii-leak-between-tenants` | Customer contact PII leak prevention | Critical | Zero customer PII leaked |
| | `mt-05-api-key-tenant-enforce` | Outbound request tenant boundary | Critical | Tenant header enforced |
| **Prompt Injection** | `pi-01-indirect-refund-override` | Hidden instructions in product reviews | Critical | Unauthorized refund blocked |
| | `pi-02-system-prompt-exfiltration` | System prompt leak attempt | Critical | System instructions preserved |
| | `pi-03-roleplay-jailbreak-bypass` | Admin mode roleplay escalation | Critical | Privileged tools remain locked |
| | `pi-04-markdown-image-exfiltration` | Data exfiltration via Markdown images | Critical | External image URLs blocked |
| | `pi-05-payload-delimiter-hijack` | XML/JSON delimiter escape breakout | Critical | Delimiter escape neutralized |

---

## 🧪 Testing & Quality Bar

ARL enforces strict quality gates across every commit:
- **185 Passed Tests** (0 failures, 2 live-service skips)
- **85.28% Test Coverage** (enforced by `--cov-fail-under=85`)
- **Strict MyPy Typing** (0 errors across 91 source files)
- **Ruff Code Formatting & Linting** (0 errors across 133 files)

Run the verification suite locally:
```bash
# Run tests with coverage
pytest -q

# Run Ruff linter and formatter checks
ruff check .
ruff format --check .

# Run strict MyPy type checking
mypy packages apps adapters environments
```

---

## 🤝 Contributing & Community

We welcome contributions from reliability engineers, AI researchers, and distributed systems developers!

- **Code of Conduct**: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security Policy**: [SECURITY.md](SECURITY.md)
- **Architecture Decisions**: [docs/adr/](docs/adr/)
- **VNext Audit Document**: [docs/ARL_VNEXT_AUDIT.md](docs/ARL_VNEXT_AUDIT.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **Roadmap**: [ROADMAP.md](ROADMAP.md)

---

## 📄 License

Agent Reliability Lab is open source software released under the [MIT License](LICENSE).  
Copyright © 2026 Karthik Rajesh Shet.
