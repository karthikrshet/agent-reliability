# Agent Reliability Lab (ARL) — Troubleshooting Guide

This guide provides solutions to common setup, execution, network, and statistical issues encountered when testing AI agents with ARL.

---

## 🔍 Common Errors & Solutions

### 1. `SecurityViolationError: SSRF protection: Target IP falls within blocked network`
- **Cause**: ARL strictly blocks requests to localhost, loopback (`127.0.0.1`), private RFC 1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), and cloud metadata (`169.254.169.254`).
- **Solution**: For local development and testing, set the environment variable:
  ```bash
  export ARL_ALLOW_LOCALHOST_TARGETS=true  # Linux / macOS
  $env:ARL_ALLOW_LOCALHOST_TARGETS="true"   # Windows PowerShell
  ```

---

### 2. `ReadinessThresholdError: Agent readiness threshold not met` (Exit Code 1)
- **Cause**: The lower bound of the 95% Wilson score confidence interval fell below your configured `--threshold` (e.g. 0.80), or one or more `SAFETY VETO` invariants were triggered (such as cross-tenant data access).
- **Solution**:
  1. Inspect the observable trajectory in the report (`agentlab report --run-id latest`).
  2. Check if faults (e.g. transient 500s or 429 rate limits) caused the agent to abort or loop recursively.
  3. Increase the number of trials (`--trials 10`) to narrow the Wilson score confidence interval if empirical pass rate was high.

---

### 3. `ModuleNotFoundError: No module named 'arl'`
- **Cause**: Monorepo packages were not installed in editable mode.
- **Solution**: Re-run the editable package installation from the project root:
  ```bash
  pip install -e "packages/core" -e "packages/protocol" -e "packages/scenario-engine" \
              -e "packages/fault-engine" -e "packages/execution-engine" -e "packages/grading-engine" \
              -e "packages/evidence" -e "environments/customer-support" -e "adapters/reference" \
              -e "adapters/http" -e "adapters/openai-agents" -e "apps/worker" -e "apps/server" \
              -e "apps/cli" -e "apps/mcp"
  ```

---

### 4. `ScenarioValidationError: JSON Schema 2020-12 validation failed`
- **Cause**: The YAML scenario is missing mandatory fields (`id`, `category`, `initial_state`, `expected_effects`, or `evaluation_rules`).
- **Solution**: Validate the file against the schema before execution:
  ```bash
  agentlab validate scenarios/path/to/scenario.yaml
  ```
