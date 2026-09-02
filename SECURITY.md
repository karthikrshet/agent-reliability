# Security Policy

## Supported Versions

Security updates and patches are actively maintained for the following versions:

| Version | Supported          |
| :--- | :--- |
| **0.1.x** | :white_check_mark: |
| < 0.1.0 | :x: |

---

## 🛡 Security Architecture & Safety Invariants

Agent Reliability Lab is designed with a **fail-closed** security architecture to prevent unauthorized effects and protect against agent compromise:

1. **Multi-Tenant Isolation**: Tool proxies enforce strict cryptographic tenant boundary checks (`tenant_id`). Any cross-tenant data access or modifications result in immediate trial veto (`CRITICAL_FAIL`).
2. **SSRF Mitigation**: The `HttpAgentAdapter` and sandboxed environments validate all outbound endpoints against private IP blocks (RFC 1918, link-local, loopback) and enforce domain allowlists.
3. **Prompt & Indirect Injection Defenses**: The scenario engine contains canonical benchmark test cases (`pi-01` through `pi-05`) specifically measuring agent susceptibility to hidden instruction overrides and jailbreaks in tool outputs.
4. **Deterministic Budget Enforcement**: Hard token limits, execution duration timeouts, and turn ceilings terminate runaway cascade loops before financial or resource exhaustion occurs.
5. **Immutable Evidence Cryptographic Hash Chains**: Every state transition, tool payload, and evaluation verdict is indexed into an append-only SHA-256 cryptographic chain, preventing post-facto tampering.

---

## 🚨 Reporting a Vulnerability

If you discover a security vulnerability within Agent Reliability Lab or any of its subpackages, please do **NOT** disclose it publicly via GitHub issues.

Please send a detailed vulnerability report privately to:
**Karthik Rajesh Shet**  
📧 **Email**: [kartikrshet@gmail.com](mailto:kartikrshet@gmail.com)

### What to Include:
- A clear description of the vulnerability and its potential security impact.
- Steps to reproduce the issue, including proof-of-concept code, scenario YAML, or adapter configuration.
- Any relevant logs, stack traces, or environment details.

We will acknowledge receipt of your vulnerability report within **48 hours** and provide regular status updates regarding the fix and disclosure timeline.
