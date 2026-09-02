"""
Agent Reliability Lab — OpenAI-Compatible Agent Adapter.

Enables automated testing of any agent or model endpoint exposing an
OpenAI-compatible /v1/chat/completions interface (e.g., OpenAI, Azure OpenAI,
vLLM, Ollama, LiteLLM, Groq, Mistral, Together AI).
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from arl.adapters.http.adapter import validate_url_for_ssrf
from arl.core.errors import AgentCommunicationError, AgentExecutionError
from arl.protocol.adapter import (
    AgentAdapter,
    AgentInput,
    AgentOutput,
    AgentOutputType,
    AgentSession,
    InterruptionResolution,
    SessionContext,
    ToolCallRecord,
)

logger = logging.getLogger(__name__)


class OpenAIAgentAdapter(AgentAdapter):
    """Adapter for OpenAI-compatible ChatCompletions endpoints with Tool Calling."""

    def __init__(
        self,
        endpoint_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        timeout_seconds: float = 60.0,
        system_prompt: str | None = None,
        allow_localhost: bool | None = None,
        extra_headers: dict[str, str] | None = None,
        custom_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url.rstrip("/")
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.timeout_seconds = timeout_seconds
        self.system_prompt = (
            system_prompt
            or "You are a customer support agent. Help the user by executing available tools accurately."
        )
        self.allow_localhost = (
            allow_localhost
            if allow_localhost is not None
            else os.getenv("ARL_ALLOW_LOCALHOST_TARGETS", "").lower() in ("true", "1", "yes")
        )
        self.extra_headers = extra_headers or {}
        self._custom_client = custom_client
        self._client: httpx.AsyncClient | None = custom_client

        # Pre-validate endpoint for SSRF
        if not custom_client:
            validate_url_for_ssrf(self.endpoint_url, allow_localhost=self.allow_localhost)

    @property
    def adapter_id(self) -> str:
        return "openai-v1"

    @property
    def framework(self) -> str:
        return "openai"

    @property
    def adapter_version(self) -> str:
        return "1.0.0"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Content-Type": "application/json",
                **self.extra_headers,
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds, headers=headers)
        return self._client

    async def init_session(self, context: SessionContext) -> AgentSession:
        return await self.start_session(context)

    async def start_session(self, context: SessionContext) -> AgentSession:
        """Initialize an OpenAI chat session with system prompt and tool definitions."""
        if not self._client:
            validate_url_for_ssrf(self.endpoint_url, allow_localhost=self.allow_localhost)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            *context.initial_messages,
        ]

        # Build OpenAI tools schema list
        tools_schema: list[dict[str, Any]] = [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": f"Execute tool {tool_name}",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": True,
                    },
                },
            }
            for tool_name in context.available_tools
        ]

        adapter_state: dict[str, Any] = {
            "messages": messages,
            "tools": tools_schema,
            "model": self.model,
        }

        return AgentSession(
            session_id=context.session_id,
            trial_id=context.trial_id,
            agent_version_id=context.agent_version_id,
            framework="openai",
            adapter_state=adapter_state,
        )

    async def send(self, session: AgentSession, message: AgentInput) -> AgentOutput:
        """Process turn by appending user messages or tool results, then calling /chat/completions."""
        if not self._custom_client:
            validate_url_for_ssrf(self.endpoint_url, allow_localhost=self.allow_localhost)
        client = await self._get_client()

        state = session.adapter_state
        messages: list[dict[str, Any]] = list(state.get("messages", []))
        tools: list[dict[str, Any]] = state.get("tools", [])

        # 1. Append tool results if returning from a previous tool call
        if message.tool_results:
            for tr in message.tool_results:
                tc_id = tr.get("tool_call_id", "call_default")
                res_content = tr.get("result", {})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": json.dumps(res_content, default=str),
                    }
                )

        # 2. Append new user messages
        if message.user_messages:
            messages.extend(message.user_messages)

        # 3. Prepare ChatCompletions payload
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        url = (
            self.endpoint_url
            if self.endpoint_url.endswith("/chat/completions")
            else f"{self.endpoint_url}/chat/completions"
        )

        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise AgentExecutionError(
                message=f"OpenAI endpoint returned HTTP {exc.response.status_code}: {exc.response.text}",
                agent_version_id=session.agent_version_id,
            ) from exc
        except Exception as exc:
            raise AgentCommunicationError(
                message=f"Failed to communicate with OpenAI endpoint at {url}: {exc}",
                endpoint_url=url,
            ) from exc

        # 4. Parse response choice
        choices = data.get("choices", [])
        if not choices:
            raise AgentExecutionError(
                message="OpenAI endpoint returned empty choices array",
                agent_version_id=session.agent_version_id,
            )

        choice = choices[0]
        choice_msg = choice.get("message", {})
        tool_calls_raw = choice_msg.get("tool_calls", [])
        text_content = choice_msg.get("content")

        # Record assistant response into conversation history
        messages.append(choice_msg)
        state["messages"] = messages

        # Parse token usage
        usage = data.get("usage", {})
        token_usage = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }

        # 5. Return tool calls or message
        if tool_calls_raw:
            tool_calls = []
            for tc in tool_calls_raw:
                fn = tc.get("function", {})
                raw_args = fn.get("arguments", "{}")
                try:
                    parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    parsed_args = {"raw_arguments": raw_args}

                tool_calls.append(
                    ToolCallRecord(
                        tool_call_id=tc.get("id", "call_default"),
                        tool_name=fn.get("name", "unknown_tool"),
                        arguments=parsed_args if isinstance(parsed_args, dict) else {},
                    )
                )

            return AgentOutput(
                output_type=AgentOutputType.TOOL_CALLS,
                turn_index=message.turn_index,
                tool_calls=tool_calls,
                prompt_tokens=token_usage.get("prompt_tokens"),
                completion_tokens=token_usage.get("completion_tokens"),
                total_tokens=token_usage.get("total_tokens"),
            )

        return AgentOutput(
            output_type=AgentOutputType.TEXT,
            turn_index=message.turn_index,
            raw_text=text_content or "",
            prompt_tokens=token_usage.get("prompt_tokens"),
            completion_tokens=token_usage.get("completion_tokens"),
            total_tokens=token_usage.get("total_tokens"),
        )

    async def stream(
        self, session: AgentSession, message: AgentInput
    ) -> AsyncIterator[AgentOutput]:
        out = await self.send(session, message)
        yield out

    async def interrupt(
        self, session: AgentSession, resolution: InterruptionResolution
    ) -> AgentOutput:
        return AgentOutput(
            output_type=AgentOutputType.TEXT,
            turn_index=0,
            raw_text="Interrupted",
        )

    async def resume(
        self, session: AgentSession, interruption: InterruptionResolution
    ) -> AgentOutput:
        return AgentOutput(
            output_type=AgentOutputType.TEXT,
            turn_index=0,
            raw_text="Resumed following approval",
        )

    async def cancel(self, session: AgentSession) -> None:
        pass

    async def close_session(self, session: AgentSession) -> None:
        await self.end_session(session)

    async def end_session(self, session: AgentSession) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
