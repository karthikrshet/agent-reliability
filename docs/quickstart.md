# Agent Reliability Lab (ARL) — 10-Minute Quickstart Guide

This guide takes you from an empty environment to running a stateful, fault-injected reliability evaluation against a real AI agent in under 10 minutes.

---

## 📋 Prerequisites

- **Python**: Version 3.12 or higher.
- **Package Manager**: `uv` or standard `pip`.
- **Node.js** (optional): Version 20+ for web dashboard.

---

## 🚀 Step 1: Clone and Set Up Workspace

```bash
git clone https://github.com/karthikrshet/agent-reliability.git
cd agent-reliability

# Create and activate a clean virtualenv
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all workspace packages in editable mode
uv pip install -e "packages/core" \
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

---

## 🩺 Step 2: Run Preflight Health Diagnostics

Validate your environment and canonical scenarios:
```bash
agentlab doctor
```
Expected output:
```text
              Agent Reliability Lab — Preflight Doctor Diagnostics              
╭─────────────────────────────┬────────┬───────────────────────────────────────╮
│ Diagnostic Check            │ Status │ Details                               │
├─────────────────────────────┼────────┼───────────────────────────────────────┤
│ Python Runtime (>=3.12)     │  PASS  │ Python 3.12.x                         │
│ Monorepo Packages           │  PASS  │ All 14 packages installed &           │
│                             │        │ importable                            │
│ Canonical Scenarios         │  PASS  │ 25 canonical scenarios validated      │
│ Agent Endpoint Reachability │  SKIP  │ Pass --agent-url to probe live        │
│                             │        │ endpoint                              │
│ Secret Redaction Invariants │  PASS  │ Zero unredacted credentials in        │
│                             │        │ environment                           │
╰─────────────────────────────┴────────┴───────────────────────────────────────╯
```

---

## 🤖 Step 3: Start the Sample Agent

Start the standalone customer support HTTP agent in a background terminal:
```bash
python examples/real-http-agent/server.py
```
The agent starts on `http://127.0.0.1:8088`.

---

## ⚡ Step 4: Run Reliability Evaluation

Execute 3 deterministic trials against your live agent:
```bash
agentlab run -s scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml \
             --agent-url http://127.0.0.1:8088 \
             --trials 3 \
             --seed 42 \
             --threshold 0.80
```

---

## 📊 Step 5: Export Evaluation Report & Verify Chain

Export an auditor-ready Markdown evaluation report:
```bash
agentlab report --run-id latest --format markdown --output audit-report.md
```

Verify cryptographic SHA-256 evidence chain integrity:
```bash
agentlab verify
```
