# Agent Adapter Development & Integration Guide

Agent Reliability Lab connects to AI agents through a framework-independent `AgentAdapter` interface.

---

## 🏛 Adapter Protocol Contract

Every adapter implements the `AgentAdapter` abstract base class defined in [`packages/protocol/src/arl/protocol/adapter.py`](file:///d:/ai%20project/agent-reliability-lab/packages/protocol/src/arl/protocol/adapter.py):

```python
class AgentAdapter(ABC):
    @property
    @abstractmethod
    def adapter_id(self) -> str: ...

    @property
    @abstractmethod
    def framework(self) -> str: ...

    @property
    @abstractmethod
    def adapter_version(self) -> str: ...

    @abstractmethod
    async def start_session(self, context: SessionContext) -> AgentSession: ...

    @abstractmethod
    async def send(self, session: AgentSession, message: AgentInput) -> AgentOutput: ...

    @abstractmethod
    async def stream(self, session: AgentSession, message: AgentInput) -> AsyncIterator[str]: ...

    @abstractmethod
    async def interrupt(
        self, session: AgentSession, resolution: InterruptionResolution
    ) -> AgentOutput: ...

    @abstractmethod
    async def end_session(self, session: AgentSession) -> None: ...
```

---

## 🔌 Supported Built-In Adapters

| Adapter | Package | Class | Target Use Case |
| :--- | :--- | :--- | :--- |
| **Generic HTTP** | `arl-adapter-http` | `HttpAgentAdapter` | Any REST/HTTP agent endpoint exposing `/sessions` & turn endpoints |
| **OpenAI-Compatible** | `arl-adapter-openai` | `OpenAIAgentAdapter` | OpenAI, vLLM, Ollama, LiteLLM, Groq, Mistral ChatCompletions APIs |
| **Reference Mock** | `arl-adapter-reference` | `MockAgentAdapter` | Scriptable in-memory deterministic agent for local testing |

---

## 🛡 Mandatory Security Invariants for Custom Adapters

1. **SSRF Protection**: All outbound network URLs must call `validate_url_for_ssrf(url)` before sending requests to prevent access to cloud metadata (`169.254.169.254`) and internal private RFC 1918 subnets.
2. **Secret Redaction**: Do not include raw API keys or Authorization headers in stored session state or error payloads.
3. **Fail-Closed Errors**: Transport timeouts or status code errors must raise typed domain errors (`AgentCommunicationError`, `AgentExecutionError`) rather than silently returning empty messages.
4. **Observable Trajectory Only**: Adapters must yield observable messages and tool calls; private model chain-of-thought tokens must not be recorded into public trace histories.
