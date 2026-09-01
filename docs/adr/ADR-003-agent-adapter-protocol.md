# ADR-003: Framework-Agnostic Agent Adapter Protocol

## Status
Accepted

## Date
2026-09-01

## Context
AI agents are developed across diverse frameworks (HTTP endpoints, LangChain/LangGraph, OpenAI Agents SDK, CrewAI, AutoGen, custom Python scripts). Evaluating agents should not require rewriting them or locking into a proprietary agent framework.

## Decision
We define a minimal, stable, typed protocol (`AgentAdapter`) in `arl-protocol`:
- `start_session(context: SessionContext) -> AgentSession`
- `send(session: AgentSession, message: AgentInput) -> AgentOutput`
- `resume(session: AgentSession, interruption: InterruptionResolution) -> AgentOutput`
- `cancel(session: AgentSession) -> None`
- `close_session(session: AgentSession) -> None`

The protocol observes only external behavioral contracts: tool requests, arguments, turn counts, latency, and returned messages. All agent inputs and outputs are treated as untrusted data and strictly validated.

## Consequences

### Positive
- Zero runtime dependencies on third-party agent libraries within core evaluation engines.
- Easy to add new framework adapters (HTTP adapter, LangGraph adapter, OpenAI SDK adapter) by implementing a single interface.
- First-class support for human-in-the-loop interruption/approval workflows.

### Negative
- Framework-specific internal representations (e.g. LangGraph state graph checkpoints) must be mapped to normalized `AgentOutput` and `ToolCallRecord` types by the adapter.
