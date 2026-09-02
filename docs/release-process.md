# Agent Reliability Lab — Release & Governance Process

## 1. Release Philosophy
Agent Reliability Lab (ARL) follows strict release integrity rules:
1. **Never publish fabricated scores or mock metrics.** Production dashboards, benchmarks, and reports must reflect verifiable execution data from connected agent endpoints.
2. **Deterministic Reproducibility.** Any evaluation result must be reproducible given the same scenario YAML, initial state, agent version, and deterministic PRNG seed.
3. **Immutable Release History.** Existing public tags (`v0.1.0`, `v0.2.0-beta`, `v0.2.0`) are permanent history and must never be force-moved or overwritten. All corrective changes are versioned forward (e.g. `v0.2.1-beta.1`).

---

## 2. Pre-Release Verification Checklist

Before tagging any release or release candidate:
1. **Run Full Test Suite with Coverage:**
   ```bash
   pytest -v --cov-fail-under=85
   ```
2. **Run Security & Regression Checks:**
   ```bash
   pytest -v tests/test_security_negative.py tests/test_no_fabricated_data.py tests/test_leases_concurrency.py
   ```
3. **Run Type Checking & Linting:**
   ```bash
   mypy packages apps adapters environments
   ruff check .
   ```
4. **Validate Next.js Dashboard Build:**
   ```bash
   npm --prefix apps/dashboard run build
   ```
5. **Verify All 25 Scenarios:**
   ```bash
   agentlab validate scenarios/
   ```

---

## 3. Tagging and Publishing

1. Ensure the working branch is cleanly rebased on `main` or the corrective release branch.
2. Update `CHANGELOG.md` with structured release notes.
3. Commit with signed metadata:
   ```bash
   git commit -m "chore(release): prepare v0.2.1-beta.1"
   git tag -a v0.2.1-beta.1 -m "Release v0.2.1-beta.1"
   git push origin fix/v0.2.1-beta-integrity --tags
   ```
