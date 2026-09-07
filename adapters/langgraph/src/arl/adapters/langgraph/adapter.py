"""
Agent Reliability Lab — Native LangGraph Agent Adapter.

Enables automated reliability, chaos, and invariant testing for agents built
with LangGraph (CompiledStateGraph, StateGraph, Pregel, or custom state machines).
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import json
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from arl.core.errors import AgentExecutionError
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


class LangGraphAgentAdapter(AgentAdapter):
    """Adapter for LangGraph agents.

    Accepts:
    - A compiled LangGraph graph instance (e.g., ``graph.compile()``).
    - A callable taking a state dict and returning an updated state dict.
    - An import string in the format ``"package.module:graph_variable"``.
    """

    def __init__(
        self,
        graph: Any | str | Callable[..., Any],
        state_key: str = "messages",
        timeout_seconds: float = 60.0,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._raw_graph = graph
        self.state_key = state_key
        self.timeout_seconds = timeout_seconds
        self.base_config = config or {}
        self._resolved_graph = self._resolve_graph(graph)

    @property
    def adapter_id(self) -> str:
        return "langgraph-v1"

    @property
    def framework(self) -> str:
        return "langgraph"

    @property
    def adapter_version(self) -> str:
        return "0.1.0"

    def _resolve_graph(self, target: Any | str | Callable[..., Any]) -> Any:
        """Resolve import string or validate graph object."""
        if isinstance(target, str):
            if ":" not in target:
                raise ValueError(
                    f"Invalid LangGraph import path '{target}'. Format must be 'module.submodule:graph_var'"
                )
            module_name, var_name = target.split(":", 1)
            try:
                mod = importlib.import_module(module_name)
                obj = getattr(mod, var_name)
                return obj
            except Exception as e:
                raise AgentExecutionError(
                    f"Failed to load LangGraph graph from '{target}': {e}"
                ) from e
        return target

    async def init_session(self, context: SessionContext) -> AgentSession:
        return await self.start_session(context)

    async def start_session(self, context: SessionContext) -> AgentSession:
        """Initialize a new agent session for a trial."""
        normalized_messages: list[dict[str, Any]] = []
        for msg in context.initial_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            normalized_messages.append({"role": role, "content": content})

        adapter_state: dict[str, Any] = {
            self.state_key: normalized_messages,
            "available_tools": context.available_tools,
            "session_id": context.session_id,
        }

        return AgentSession(
            session_id=context.session_id,
            trial_id=context.trial_id,
            agent_version_id=context.agent_version_id,
            framework="langgraph",
            adapter_state=adapter_state,
        )

    async def send(self, session: AgentSession, message: AgentInput) -> AgentOutput:
        """Process a turn by appending user messages or tool results, then invoking the graph."""
        adapter_state = session.adapter_state
        messages: list[Any] = list(adapter_state.get(self.state_key, []))

        # 1. Process tool results if returned from previous turn
        if message.tool_results:
            for tr in message.tool_results:
                tool_msg = {
                    "role": "tool",
                    "content": tr.get("content", tr.get("result", "")),
                    "tool_call_id": tr.get("tool_call_id") or tr.get("call_id") or "call_default",
                }
                messages.append(tool_msg)

        # 2. Process incoming user messages
        if message.user_messages:
            messages.extend(
                {"role": um.get("role", "user"), "content": um.get("content", "")}
                for um in message.user_messages
            )

        adapter_state[self.state_key] = messages

        # Build invoke config
        invoke_config = dict(self.base_config)
        invoke_config.setdefault("configurable", {})["thread_id"] = session.session_id

        try:
            output_state = await self._invoke_graph(adapter_state, invoke_config)
        except Exception as exc:
            raise AgentExecutionError(
                f"LangGraph execution error: {exc}",
                execution_id=session.session_id,
            ) from exc

        # Update state in-place
        if isinstance(output_state, dict):
            adapter_state.update(output_state)
            new_messages = output_state.get(self.state_key, messages)
        else:
            new_messages = getattr(output_state, self.state_key, messages)

        return self._extract_output_from_messages(new_messages, message.turn_index)

    async def _invoke_graph(self, state: dict[str, Any], config: dict[str, Any]) -> Any:
        """Invoke graph supporting both ainvoke and sync invoke with timeout."""
        graph = self._resolved_graph
        if hasattr(graph, "ainvoke") and inspect.iscoroutinefunction(graph.ainvoke):
            return await asyncio.wait_for(
                graph.ainvoke(state, config=config),
                timeout=self.timeout_seconds,
            )
        elif hasattr(graph, "invoke"):
            loop = asyncio.get_running_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, lambda: graph.invoke(state, config=config)),
                timeout=self.timeout_seconds,
            )
        elif callable(graph):
            if inspect.iscoroutinefunction(graph):
                return await asyncio.wait_for(
                    graph(state, config=config),
                    timeout=self.timeout_seconds,
                )
            else:
                loop = asyncio.get_running_loop()
                return await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: graph(state, config=config)),
                    timeout=self.timeout_seconds,
                )
        else:
            raise AgentExecutionError(
                f"Provided LangGraph target is neither callable nor implements ainvoke/invoke: {type(graph)}"
            )

    def _extract_output_from_messages(self, messages: Any, turn_index: int) -> AgentOutput:
        """Parse resulting messages into an AgentOutput."""
        if not messages:
            return AgentOutput(
                output_type=AgentOutputType.TEXT,
                turn_index=turn_index,
                raw_text="",
            )

        last_msg = messages[-1] if isinstance(messages, list) else messages

        content = ""
        tool_calls: list[ToolCallRecord] = []

        if isinstance(last_msg, dict):
            content = str(last_msg.get("content", "") or "")
            raw_tool_calls = last_msg.get("tool_calls", [])
            for idx, tc in enumerate(raw_tool_calls):
                tool_calls.append(self._parse_tool_call(tc, idx))
        else:
            content = str(getattr(last_msg, "content", "") or "")
            raw_tool_calls = getattr(last_msg, "tool_calls", []) or []
            for idx, tc in enumerate(raw_tool_calls):
                tool_calls.append(self._parse_tool_call(tc, idx))

        if tool_calls:
            return AgentOutput(
                output_type=AgentOutputType.TOOL_CALLS,
                turn_index=turn_index,
                tool_calls=tool_calls,
                raw_text=content,
            )

        return AgentOutput(
            output_type=AgentOutputType.TEXT,
            turn_index=turn_index,
            raw_text=content,
        )

    def _parse_tool_call(self, tc: Any, fallback_idx: int) -> ToolCallRecord:
        """Parse tool call from dict or object."""
        if isinstance(tc, dict):
            call_id = tc.get("id") or f"call_{fallback_idx}"
            name = tc.get("name") or tc.get("function", {}).get("name", "")
            args = tc.get("args") or tc.get("function", {}).get("arguments", {})
        else:
            call_id = getattr(tc, "id", f"call_{fallback_idx}")
            name = getattr(tc, "name", "")
            args = getattr(tc, "args", {})

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {"raw_arguments": args}

        return ToolCallRecord(
            tool_call_id=call_id,
            tool_name=name,
            arguments=args if isinstance(args, dict) else {},
        )

    async def resume(
        self, session: AgentSession, interruption: InterruptionResolution
    ) -> AgentOutput:
        """Resume an interrupted session."""
        message = AgentInput(
            turn_index=0,
            user_messages=[
                {"role": "user", "content": f"Interruption approved: {interruption.approved}"}
            ],
        )
        return await self.send(session, message)

    async def cancel(self, session: AgentSession) -> None:
        """Cancel an in-progress session."""
        session.adapter_state.clear()

    async def close_session(self, session: AgentSession) -> None:
        """Release session resources."""
        session.adapter_state.clear()

    async def stream(
        self, session: AgentSession, message: AgentInput
    ) -> AsyncIterator[AgentOutput]:
        """Streaming fallback: yield single completed turn output."""
        output = await self.send(session, message)
        yield output
