# Deterministic HTTP Reference Agent

This example runs a standalone, deterministic HTTP agent server implementing the ARL `AgentAdapter` contract using keyword matching logic (no external LLM required).

> [!NOTE]
> This is a **deterministic reference agent** intended to verify infrastructure, network connectivity, and protocol conformance without consuming LLM API credits. It is not an AI model.

---

## 🚀 Quickstart

### 1. Start Reference Agent Server

```bash
python examples/deterministic-http-reference-agent/server.py
```
The server listens on `http://127.0.0.1:8088`.

### 2. Run Diagnostics & Reliability Evaluation

In a second terminal:

```bash
# Verify preflight diagnostics
agentlab doctor --agent-url http://127.0.0.1:8088

# Run 3 trials of order lookup evaluation
agentlab run -s scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml \
             --agent-url http://127.0.0.1:8088 \
             --trials 3 \
             --seed 42
```

---

## 🤖 Automated End-to-End Demo Script

To run the entire flow automatically:

```bash
python examples/deterministic-http-reference-agent/run_demo.py
```
