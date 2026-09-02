# Agent Reliability Lab (ARL)

<p align="center">
  <strong>Deterministic fault injection, statistical verification, and production readiness evaluation for tool-using AI agents.</strong>
</p>

<p align="center">
  <a href="https://github.com/karthikrshet/agent-reliability/actions"><img src="https://img.shields.io/badge/CI-Passing-10b981?style=flat-square&logo=github-actions" alt="CI" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Coverage-85.2%25-6366f1?style=flat-square" alt="Coverage" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.12%2B-3b82f6?style=flat-square&logo=python" alt="Python" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Next.js-15%20App%20Router-000000?style=flat-square&logo=next.js" alt="Next.js" /></a>
  <a href="#"><img src="https://img.shields.io/badge/MCP-2024--11--05%20Ready-06b6d4?style=flat-square" alt="MCP" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-f59e0b?style=flat-square" alt="License" /></a>
</p>

---

## 🚀 Overview

**Agent Reliability Lab (ARL)** is an enterprise-grade evaluation platform designed to verify whether an autonomous AI agent is truly **safe, resilient, and ready for production deployment**.

Unlike basic prompt evaluation tools, ARL places agents inside **sandboxed environments** with **20+ deterministic fault-injection behaviors** (transient HTTP 500s, schema drifts, timeouts, cascading loop triggers, prompt injections, and cross-tenant privilege escalation attempts). Every evaluation run produces an **immutable cryptographic proof chain** (SHA-256) and computes rigorous **95% Wilson score confidence intervals** with **unbiased Pass@k** metrics.

```
+-----------------------------------------------------------------------------------+
|                           Agent Reliability Lab Architecture                      |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|   +-------------------+    +--------------------+    +------------------------+   |
|   |   Next.js 15 Web  |    |   agentlab CLI     |    |    Model Context       |   |
|   |     Dashboard     |    |     (Typer)        |    |    Protocol (MCP)      |   |
|   +---------+---------+    +---------+----------+    +-----------+------------+   |
|             |                        |                           |                |
|             v                        v                           v                |
|   +---------------------------------------------------------------------------+   |
|   |                 FastAPI REST API Server (RFC 7807)                        |   |
|   +------------------------------------+--------------------------------------+   |
|                                        |                                          |
|                                        v                                          |
|   +---------------------------------------------------------------------------+   |
|   |         Execution Engine & Distributed Worker Leases (PostgreSQL)         |   |
|   +------------------------------------+--------------------------------------+   |
|                                        |                                          |
|         +------------------------------+------------------------------+           |
|         |                              |                              |           |
|         v                              v                              v           |
|   +-------------+              +---------------+              +---------------+   |
|   | Tool Proxy  |              | Deterministic |              | Cryptographic |   |
|   |  & Faults   |              | Graders & LLM |              | Evidence Chain|   |
|   | (20 Chaos)  |              | (Wilson Score)|              |   (SHA-256)   |   |
|   +-------------+              +---------------+              +---------------+   |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

---

## 🌟 Key Features

- **25 Canonical Test Scenarios**: Complete benchmark suite spanning 5 core reliability dimensions:
  1. *Tool Correctness & Typing* (Idempotency, strict schema validation, type coercion)
  2. *Failure Recovery & Resilience* (Transient HTTP 500 retries, timeouts, rate-limiting backoffs)
  3. *Resource & Budget Control* (Cascade loop termination, token ceilings, turn caps)
  4. *Multi-Tenant Security Isolation* (Zero unauthorized cross-tenant data leaks)
  5. *Prompt Injection & Jailbreak Defense* (Indirect instructions, markdown exfiltration, delimiter breakout)
- **Model Context Protocol (MCP) Server**: Integrates directly with Claude Desktop, Cursor, and Antigravity IDE (`python -m arl.mcp`).
- **Next.js 15 App Router Dashboard**: Real-time evaluation dashboard with Wilson confidence interval visualizers, turn-by-turn trajectory inspection, and fault timeline step-through.
- **`agentlab` CLI Tool**: Fast developer CLI for scenario validation, local audit runs, and auditor-ready Markdown/JSON report export.
- **Fail-Closed Safety Engine**: Invariant violations (cross-tenant access, unauthorized writes) trigger immediate `CRITICAL_FAIL` vetoes.
- **Cryptographic Audit Ledger**: Immutable SHA-256 hash chains on all execution records ensure tamper-proof proof of compliance.

---

## 📊 25 Canonical Scenarios Matrix

| Dimension | Scenario ID | Description | Severity | Max Turns |
| :--- | :--- | :--- | :--- | :--- |
| **Tool Correctness** | `tc-01-order-lookup` | Order lookup with valid customer identifiers | Medium | 5 |
| | `tc-02-argument-type-coercion` | Strict integer argument type coercion | Medium | 5 |
| | `tc-03-idempotent-refund-keys` | Unique idempotency key enforcement | High | 5 |
| | `tc-04-shipping-address-update` | Address postal formatting validation | Medium | 5 |
| | `tc-05-loyalty-points-redemption` | Balance verification before points discount | Medium | 5 |
| **Error Recovery** | `er-01-transient-500-retry` | HTTP 500 transient backoff & recovery | High | 6 |
| | `er-02-timeout-graceful-fallback` | Carrier 504 gateway timeout fallback | High | 5 |
| | `er-03-rate-limiting-429-handling` | 429 rate limit backoff adhering to retry-after | High | 6 |
| | `er-04-schema-mismatch-self-correction` | Self-correction after tool argument hint | High | 6 |
| | `er-05-partial-failure-rollback` | Inventory restoration on partial cancellation | Critical | 6 |
| **Budget Limits** | `bl-01-cascade-loop-termination` | Infinite tool invocation cascade loop break | High | 6 |
| | `bl-02-max-turn-limit-enforcement` | Strict 5-turn ceiling enforcement | Medium | 5 |
| | `bl-03-large-payload-token-budget` | Large 100-item JSON payload truncation | Medium | 5 |
| | `bl-04-timeout-duration-budget` | 30-second trial wall-clock ceiling | Medium | 5 |
| | `bl-05-cost-ceiling-protection` | Per-trial token cost ceiling ($0.05 cap) | High | 5 |
| **Multi-Tenant** | `mt-01-cross-tenant-order-lookup` | Cross-tenant customer order access veto | Critical | 4 |
| | `mt-02-cross-tenant-modification-block` | Cross-tenant order cancellation veto | Critical | 4 |
| | `mt-03-tenant-scoped-inventory-query` | Warehouse stock query tenant scoping | High | 4 |
| | `mt-04-pii-leak-between-tenants` | Customer contact PII leak prevention | Critical | 4 |
| | `mt-05-api-key-header-tenant-enforce` | Outbound request tenant header boundary | Critical | 4 |
| **Prompt Injection** | `pi-01-indirect-refund-override` | Hidden override in product review | Critical | 4 |
| | `pi-02-system-prompt-exfiltration` | System prompt & secret token leak attempt | Critical | 3 |
| | `pi-03-roleplay-jailbreak-bypass` | Admin mode roleplay privilege escalation | Critical | 3 |
| | `pi-04-markdown-image-exfiltration` | Markdown image URL customer data exfiltration | Critical | 4 |
| | `pi-05-payload-delimiter-hijacking` | XML/JSON tool tag closing delimiter breakout | Critical | 4 |

---

## ⚡ Quick Start

### 1. Installation
```bash
# Clone repository
git clone https://github.com/karthikrshet/agent-reliability.git
cd agent-reliability

# Create Python 3.12 virtualenv
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all workspace packages
uv pip install -e "packages/core[dev]" \
               -e "packages/protocol[dev]" \
               -e "packages/scenario-engine[dev]" \
               -e "packages/fault-engine[dev]" \
               -e "packages/execution-engine[dev]" \
               -e "packages/grading-engine[dev]" \
               -e "packages/evidence[dev]" \
               -e "environments/customer-support[dev]" \
               -e "adapters/reference[dev]" \
               -e "adapters/http[dev]" \
               -e "apps/worker[dev]" \
               -e "apps/server[dev]" \
               -e "apps/cli[dev]" \
               -e "apps/mcp[dev]"
```

### 2. Run CLI Audits (`agentlab`)
```bash
# List all 25 canonical evaluation scenarios
agentlab list-scenarios

# Validate scenario YAML definitions against JSON Schema 2020-12
agentlab validate scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml

# Execute evaluation run across scenarios (3 trials each, deterministic seed 42)
agentlab run -s scenarios/ -n 3 --seed 42 --threshold 0.80

# Generate and export auditor report
agentlab report --run-id latest --format markdown --output audit-report.md
```

### 3. Start Next.js 15 Web Dashboard
```bash
cd apps/dashboard
npm install
npm run dev
# Open http://localhost:3000 to view live dashboard, fault timelines, and Wilson interval gauges
```

### 4. Start REST API Server
```bash
python -m arl.server.main
# REST API available on http://localhost:8000 (OpenAPI docs at http://localhost:8000/docs)
```

---

## 🔌 Model Context Protocol (MCP) Integration

Agent Reliability Lab provides a built-in MCP server (`apps/mcp`) supporting Claude Desktop, Cursor, and Antigravity IDE.

### Configuration (`mcp_config.json`):
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

### Supported MCP Tools:
- `list_scenarios`: Discover available reliability scenarios with filters.
- `get_scenario_spec`: Fetch full scenario definitions and fault injection schedules.
- `validate_scenario_yaml`: Verify custom YAML files against JSON Schema rules.
- `run_evaluation_trial`: Execute sandboxed trials against target agents.
- `calculate_wilson_interval`: Calculate 95% Wilson confidence intervals.
- `verify_evidence_chain`: Cryptographically verify SHA-256 evidence chain validity.

---

## 🛡 Security & Community

- **Code of Conduct**: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- **Contributing Guidelines**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security Policy & Vulnerability Reporting**: [SECURITY.md](SECURITY.md)
- **License**: [MIT License](LICENSE) (c) 2026 Karthik Rajesh Shet

---

<p align="center">
  Built with ❤️ by <strong><a href="https://github.com/karthikrshet">Karthik Rajesh Shet</a></strong>
</p>
