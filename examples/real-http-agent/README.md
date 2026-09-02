# Real HTTP Agent Quickstart (10-Minute Walkthrough)

This example provides a standalone, runnable customer support AI agent endpoint demonstrating how to connect real external agents to **Agent Reliability Lab (ARL)** for evaluation.

---

## 🚀 Step 1: Start the Real Agent Endpoint

In a terminal, start the reference agent server:
```bash
python examples/real-http-agent/server.py
```
The agent starts on `http://127.0.0.1:8088`.

Verify connectivity:
```bash
curl http://127.0.0.1:8088/healthz
# Response: {"status":"ok","agent":"arl-reference-http-agent"}
```

---

## 🩺 Step 2: Run Preflight Diagnostics

Check agent endpoint reachability and environment health with `agentlab doctor`:
```bash
agentlab doctor --agent-url http://127.0.0.1:8088
```

---

## ⚡ Step 3: Run Reliability Evaluation

Execute 3 deterministic trials against your live agent endpoint:
```bash
agentlab run -s scenarios/tool-correctness/01-order-lookup-correct-arguments.yaml \
             --agent-url http://127.0.0.1:8088 \
             --trials 3 \
             --seed 42 \
             --threshold 0.80
```

### What Happens Behind the Scenes:
1. **SSRF Pre-Validation**: ARL verifies the endpoint URL does not breach cloud metadata or private network boundaries.
2. **Session Initialization**: `HttpAgentAdapter` creates a stateful session on `/sessions`.
3. **Multi-Turn Interaction**: The agent receives conversation turns and dispatches `lookup_order` tool calls.
4. **Fault Proxy Interception**: ARL intercepts the tool call, applies deterministic seed-controlled fault schedules (e.g. latency, HTTP 500, schema alterations), and records the post-state.
5. **Observable Trajectory Logging**: Observable messages, tool arguments, fault events, and state diffs are recorded without exposing private chain-of-thought tokens.
6. **Deterministic Grading**: `DeterministicTrialEvaluator` verifies argument types, state transitions, and absence of forbidden side-effects.
7. **Statistical Aggregation**: Computes 95% Wilson confidence intervals, Pass@1, and Pass@3.
8. **Cryptographic Proof Ledger**: Commits all execution records into an append-only SHA-256 hash chain.

---

## 📄 Step 4: Export Auditor-Ready Report

Export the evaluation findings to Markdown or JSON:
```bash
agentlab report --run-id latest --format markdown --output agent-audit.md
```
