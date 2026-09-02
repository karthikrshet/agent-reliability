# Contributing to Agent Reliability Lab (ARL)

Thank you for your interest in contributing to **Agent Reliability Lab**! This project provides production-grade testing, fault injection, and statistical verification frameworks for tool-using AI agents.

---

## 🏛 Architectural Principles

1. **Deterministic Control, Probabilistic Interpretation**: Evaluation runs use fixed PRNG seeds and deterministic fault injectors. Outputs are evaluated statistically via 95% Wilson score confidence intervals and unbiased Pass@k metrics.
2. **Fail Closed**: Any invalid scenario schema, unhandled fault state, security isolation boundary breach, or prompt injection vulnerability triggers an immediate `CRITICAL_FAIL` or `NOT_READY` verdict.
3. **Immutable Cryptographic Proofs**: All trial outputs, world snapshots, and grader findings are cryptographically hashed using SHA-256 and chained into an tamper-evident ledger.
4. **Strict Typing & Zero Warnings**: All codebases must pass strict MyPy (`--strict`) and Ruff (`check` and `format`) with zero errors and maintain test coverage `>= 85%`.

---

## 🛠 Local Development Setup

### Prerequisites
- **Python 3.12+** (`uv` or `venv`)
- **Node.js 20+** & **pnpm 9+** or **npm**
- **Docker** & **Docker Compose** (for PostgreSQL and Redis integration tests)

### 1. Clone & Set Up Virtualenv
```bash
git clone https://github.com/karthikrshet/agent-reliability.git
cd agent-reliability

# Set up Python virtual environment
uv venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all workspace packages in editable mode with development dependencies
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

### 2. Set Up Web Dashboard (Next.js 15)
```bash
cd apps/dashboard
npm install
npm run dev
# Dashboard opens on http://localhost:3000
```

---

## 🧪 Testing & Quality Gates

Before submitting a Pull Request, verify that all quality gates pass:

```bash
# 1. Strict MyPy Type Checking across all packages and apps
mypy packages apps adapters environments

# 2. Linting & Formatting Check with Ruff
ruff check .
ruff format --check .

# 3. Complete Test Suite with 85%+ Coverage Threshold
pytest -v --cov --cov-fail-under=85
```

---

## 📦 Model Context Protocol (MCP) Server

To run the local MCP server for AI agent pair-programming:
```bash
# Start MCP server over stdio
python -m arl.mcp
```

Configure `mcp_config.json` in your client:
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

## 📝 Commit Conventions

All commits follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat(scope)`: A new user-facing feature or domain model
- `fix(scope)`: A bug fix in execution engine, grader, or CLI
- `test(scope)`: Adding new unit, contract, or scenario tests
- `docs(scope)`: Documentation changes or ADR additions
- `refactor(scope)`: Refactoring code without changing public APIs

---

## 💬 Questions or Help

Feel free to open an Issue or start a Discussion on GitHub, or reach out to the project maintainer:
**Karthik Rajesh Shet** — [kartikrshet@gmail.com](mailto:kartikrshet@gmail.com).
