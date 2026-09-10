"""
Agent Reliability Lab — Native CrewAI Agent Adapter.

Enables automated reliability, chaos, and invariant testing for agents built
with CrewAI (Agent, Task, Crew, or custom hierarchical orchestration).
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
    InterruptionType,
    SessionContext,
    ToolCallRecord,
)

logger = logging.getLogger(__name__)


class CrewAIAgentAdapter(AgentAdapter):
    """Adapter for CrewAI agents, tasks, and crews.

    Accepts:
    - A CrewAI Agent or Crew instance (e.g. ``Crew(agents=[...], tasks=[...])``).
    - A callable taking an input dict and returning an output dict or string.
    - An import string in the format ``"package.module:crew_instance"``.
    """

    def __init__(
        self,
        crew: Any | str | Callable[..., Any],
        task_output_key: str = "output",
        timeout_seconds: float = 60.0,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._raw_crew = crew
        self.task_output_key = task_output_key
        self.timeout_seconds = timeout_seconds
        self.base_config = config or {}
        self._resolved_crew = self._resolve_crew(crew)

    @property
    def adapter_id(self) -> str:
        return "crewai-v1"

    @property
    def framework(self) -> str:
        return "crewai"

    @property
    def adapter_version(self) -> str:
        return "0.1.0"

    def _resolve_crew(self, target: Any | str | Callable[..., Any]) -> Any:
        """Resolve import string or validate CrewAI object."""
        if isinstance(target, str):
            if ":" not in target:
                raise ValueError(
                    f"Invalid CrewAI import string '{target}'. Expected 'module.submodule:attribute'"
                )
            mod_name, attr_name = target.split(":", 1)
            try:
                mod = importlib.import_module(mod_name)
                obj = getattr(mod, attr_name)
                return obj
            except (ImportError, AttributeError) as exc:
                raise ImportError(f"Failed to import CrewAI target '{target}': {exc}") from exc
        return target

    async def start_session(self, context: SessionContext) -> AgentSession:
        """Initialize an execution session for a CrewAI agent."""
        adapter_state: dict[str, Any] = {
            "history": [],
            "current_step": 0,
            "crew_config": dict(self.base_config),
            "pending_tool_calls": {},
            "interrupted": False,
            "active_task_id": None,
        }
        return AgentSession(
            session_id=context.session_id,
            trial_id=context.trial_id,
            agent_version_id=context.agent_version_id,
            framework=self.framework,
            adapter_state=adapter_state,
        )

    async def create_session(self, context: SessionContext) -> AgentSession:
        """Alias for start_session."""
        return await self.start_session(context)

    async def send(
        self,
        session: AgentSession,
        message: AgentInput,
    ) -> AgentOutput:
        """Forward scenario input to the CrewAI agent/crew and collect response."""
        state = session.adapter_state
        state["current_step"] = message.turn_index

        for msg in message.user_messages:
            state["history"].append({"role": "user", "content": msg.get("content", "")})

        # Inject tool results if delivered
        for tr in message.tool_results:
            state["history"].append(
                {
                    "role": "tool",
                    "tool_call_id": tr.get("tool_call_id"),
                    "output": tr.get("result"),
                    "error": tr.get("error"),
                }
            )

        crew_obj = self._resolved_crew

        try:
            raw_result = await asyncio.wait_for(
                self._execute_crew_turn(crew_obj, message, state),
                timeout=self.timeout_seconds,
            )
        except TimeoutError as exc:
            raise AgentExecutionError(
                f"CrewAI execution timed out after {self.timeout_seconds}s",
                execution_id=session.session_id,
            ) from exc
        except Exception as exc:
            if isinstance(exc, AgentExecutionError):
                raise
            raise AgentExecutionError(
                f"CrewAI agent failed during turn execution: {exc}",
                execution_id=session.session_id,
            ) from exc

        return self._format_output(raw_result, message.turn_index, state)

    async def send_input(
        self,
        session: AgentSession,
        input_data: AgentInput,
    ) -> AgentOutput:
        """Alias for send."""
        return await self.send(session, input_data)

    async def _execute_crew_turn(
        self,
        crew_obj: Any,
        message: AgentInput,
        state: dict[str, Any],
    ) -> Any:
        """Execute a turn against the CrewAI object or callable."""
        user_text = ""
        if message.user_messages:
            user_text = message.user_messages[-1].get("content", "")

        payload = {
            "input": user_text,
            "tool_results": message.tool_results,
            "history": list(state["history"]),
            "turn_index": message.turn_index,
        }

        # Case A: Async kickoff (CrewAI Crew.kickoff_async)
        if hasattr(crew_obj, "kickoff_async") and inspect.iscoroutinefunction(
            crew_obj.kickoff_async
        ):
            return await crew_obj.kickoff_async(inputs=payload)

        # Case B: Sync kickoff (CrewAI Crew.kickoff)
        if hasattr(crew_obj, "kickoff") and callable(crew_obj.kickoff):
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: crew_obj.kickoff(inputs=payload))

        # Case C: Agent step / execute_task
        if hasattr(crew_obj, "execute_task") and callable(crew_obj.execute_task):
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: crew_obj.execute_task(payload))

        # Case D: Async callable
        if inspect.iscoroutinefunction(crew_obj):
            return await crew_obj(payload)

        # Case E: Sync callable
        if callable(crew_obj):
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: crew_obj(payload))

        raise AgentExecutionError(
            f"Target CrewAI object '{type(crew_obj)}' has no recognized execution method "
            "(expected kickoff, kickoff_async, execute_task, or callable)"
        )

    def _format_output(
        self, raw_result: Any, turn_index: int, state: dict[str, Any]
    ) -> AgentOutput:
        """Parse CrewAI output into standard AgentOutput."""
        # Check for tool call requests
        if isinstance(raw_result, dict) and "tool_calls" in raw_result:
            tool_calls: list[ToolCallRecord] = []
            for tc in raw_result["tool_calls"]:
                tc_id = tc.get("id", f"crew_tc_{turn_index}_{len(tool_calls)}")
                args = tc.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {"raw": args}
                tool_calls.append(
                    ToolCallRecord(
                        tool_call_id=tc_id,
                        tool_name=tc.get("name", "unknown_tool"),
                        arguments=args,
                    )
                )
            state["pending_tool_calls"] = {tc.tool_call_id: tc for tc in tool_calls}
            return AgentOutput(
                output_type=AgentOutputType.TOOL_CALLS,
                turn_index=turn_index,
                tool_calls=tool_calls,
                raw_text=raw_result.get("text"),
            )

        # Check for human-in-the-loop interruption request
        if isinstance(raw_result, dict) and raw_result.get("interrupted"):
            state["interrupted"] = True
            state["active_task_id"] = raw_result.get("task_id", "task_01")
            return AgentOutput(
                output_type=AgentOutputType.INTERRUPTED,
                turn_index=turn_index,
                interruption_type=InterruptionType.APPROVAL_REQUIRED,
                interruption_payload=raw_result,
                raw_text=raw_result.get("prompt", "Human approval required"),
            )

        # Normal text output
        text = ""
        if isinstance(raw_result, str):
            text = raw_result
        elif hasattr(raw_result, "raw"):
            text = str(raw_result.raw)
        elif isinstance(raw_result, dict):
            text = str(
                raw_result.get(self.task_output_key)
                or raw_result.get("result")
                or raw_result.get("output")
                or json.dumps(raw_result)
            )
        else:
            text = str(raw_result)

        state["history"].append({"role": "assistant", "content": text})

        return AgentOutput(
            output_type=AgentOutputType.TEXT,
            turn_index=turn_index,
            raw_text=text,
        )

    async def stream(
        self,
        session: AgentSession,
        message: AgentInput,
    ) -> AsyncIterator[AgentOutput]:
        """Stream chunks from the CrewAI agent."""
        output = await self.send(session, message)
        yield output

    async def stream_output(
        self,
        session: AgentSession,
        input_data: AgentInput,
    ) -> AsyncIterator[AgentOutput]:
        """Alias for stream."""
        async for chunk in self.stream(session, input_data):
            yield chunk

    async def resume(
        self,
        session: AgentSession,
        interruption: InterruptionResolution,
    ) -> AgentOutput:
        """Resume execution of an interrupted CrewAI task."""
        state = session.adapter_state
        state["interrupted"] = False
        state["history"].append(
            {
                "role": "human_feedback",
                "resolution": interruption.resolution_payload,
                "approved": interruption.approved,
                "resolved_by": interruption.resolved_by,
            }
        )
        continuation_input = AgentInput(
            turn_index=state["current_step"] + 1,
            user_messages=[
                {
                    "role": "user",
                    "content": f"Resumed after review: {interruption.resolution_payload.get('notes', 'Approved')}",
                }
            ],
        )
        return await self.send(session, continuation_input)

    async def resume_interrupted(
        self,
        session: AgentSession,
        resolution: InterruptionResolution,
    ) -> AgentOutput:
        """Alias for resume."""
        return await self.resume(session, resolution)

    async def cancel(self, session: AgentSession) -> None:
        """Cancel an active CrewAI execution session."""
        session.adapter_state["cancelled"] = True
        logger.info("CrewAI session '%s' cancelled.", session.session_id)

    async def cancel_session(self, session: AgentSession) -> None:
        """Alias for cancel."""
        await self.cancel(session)

    async def close_session(self, session: AgentSession) -> None:
        """Tear down and finalize the CrewAI session."""
        session.adapter_state.clear()
        logger.info("CrewAI session '%s' terminated.", session.session_id)

    async def end_session(self, session: AgentSession) -> None:
        """Alias for close_session."""
        await self.close_session(session)
