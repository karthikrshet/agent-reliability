# ARL Adapter — CrewAI

Native adapter for testing CrewAI agents, tasks, and crews within the Agent Reliability Lab (ARL) framework.

## Capabilities
- Turn-by-turn input injection into CrewAI task execution
- Tool execution interception and structured tool call record capture
- Human-in-the-loop interruption resolution and continuation
- Streaming execution token and step events
- Strict fail-closed exception handling conforming to `ARL-Protocol-01`
