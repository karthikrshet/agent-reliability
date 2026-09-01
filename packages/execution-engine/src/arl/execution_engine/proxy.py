"""
Agent Reliability Lab — Tool Proxy Layer with Deterministic Fault Injection.

The ToolProxy sits between the AgentAdapter and the Sandboxed Environment:
1. Validates tool arguments against the declared ToolDefinition schema.
2. Consults the FaultScheduler to check if a deterministic fault is scheduled.
3. If a fault is scheduled:
   - Records and returns a FaultEvent before the fault executes.
   - Injects the simulated failure (HTTP error, delay, malformed JSON, timeout).
4. If no fault is scheduled:
   - Dispatches execution to the sandboxed environment.
5. Measures tool latency in milliseconds and returns structured ToolResult.

Security note: Tool results and arguments are treated as untrusted data.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Protocol

import jsonschema

from arl.core.domain.faults import FaultEvent
from arl.core.domain.tools import ToolResult
from arl.fault_engine.scheduler import FaultScheduler, ScheduledFault

logger = logging.getLogger(__name__)


class EnvironmentProtocol(Protocol):
    """Protocol satisfied by sandboxed test environments."""

    def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


class ToolProxy:
    """Intercepts and executes tools with fault injection and metrics tracking."""

    def __init__(
        self,
        environment: EnvironmentProtocol,
        tool_definitions: list[dict[str, Any]],
        fault_scheduler: FaultScheduler | None = None,
    ) -> None:
        self.environment = environment
        self.tool_definitions = {
            tool["function"]["name"]: tool["function"]
            for tool in tool_definitions
            if "function" in tool and "name" in tool["function"]
        }
        self.fault_scheduler = fault_scheduler
        self.recorded_fault_events: list[FaultEvent] = []

    async def execute(
        self,
        tool_call_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        trial_id: str = "trial-default",
        elapsed_seconds: float = 0.0,
    ) -> tuple[ToolResult, FaultEvent | None]:
        """Execute a tool call with fault interception.

        Returns (ToolResult, FaultEvent | None).
        """
        start_time = time.perf_counter()
        fault_event: FaultEvent | None = None

        # 1. Check if fault scheduler fires
        scheduled_fault: ScheduledFault | None = None
        if self.fault_scheduler is not None:
            scheduled_fault = self.fault_scheduler.check(
                tool_name=tool_name,
                call_arguments=arguments,
                elapsed_seconds=elapsed_seconds,
            )

        if scheduled_fault is not None and self.fault_scheduler is not None:
            fault_event = self.fault_scheduler.make_fault_event(
                scheduled=scheduled_fault,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
            )
            self.recorded_fault_events.append(fault_event)

            # Apply fault behavior
            result_payload, is_error, error_type = await self._apply_fault_behavior(
                scheduled_fault=scheduled_fault,
                tool_name=tool_name,
                arguments=arguments,
            )
        else:
            # 2. Validate tool schema if tool definition is known
            validation_error = self._validate_arguments(tool_name, arguments)
            if validation_error is not None:
                result_payload = {"error": "ValidationError", "detail": validation_error}
                is_error = True
                error_type = "ValidationError"
            else:
                # 3. Normal execution in environment
                try:
                    result_payload = self.environment.execute_tool(tool_name, arguments)
                    is_error = "error" in result_payload
                    error_type = result_payload.get("error") if is_error else None
                except Exception as exc:
                    logger.exception("Unexpected exception executing tool %s", tool_name)
                    result_payload = {"error": "InternalExecutionError", "detail": str(exc)}
                    is_error = True
                    error_type = "InternalExecutionError"

        _duration_ms = int((time.perf_counter() - start_time) * 1000)

        err_msg = (
            result_payload.get("message") or result_payload.get("detail")
            if isinstance(result_payload, dict)
            else None
        )

        tool_result = ToolResult(
            id=f"res-{tool_call_id}",
            tool_call_id=tool_call_id,
            trial_id=trial_id,
            content=result_payload,
            is_error=is_error,
            error_code=error_type,
            error_message=str(err_msg) if err_msg else None,
        )

        return tool_result, fault_event

    def _validate_arguments(self, tool_name: str, arguments: dict[str, Any]) -> str | None:
        """Validate arguments against tool definition JSON Schema."""
        tool_spec = self.tool_definitions.get(tool_name)
        if tool_spec is None:
            return None  # tool not in local spec, let environment handle unknown tool

        param_schema = tool_spec.get("parameters")
        if param_schema:
            validator = jsonschema.Draft202012Validator(param_schema)
            errors = list(validator.iter_errors(arguments))
            if errors:
                return "; ".join(
                    f"[{'/'.join(str(p) for p in e.path) or 'root'}] {e.message}" for e in errors
                )
        return None

    async def _apply_fault_behavior(
        self,
        scheduled_fault: ScheduledFault,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> tuple[dict[str, Any], bool, str | None]:
        """Simulate the planned fault behavior."""
        behaviour = scheduled_fault.entry.behaviour
        fault_type = behaviour.type

        # Apply delay if specified
        if behaviour.delay_ms > 0:
            await asyncio.sleep(behaviour.delay_ms / 1000.0)

        if fault_type == "http_500":
            return (
                {
                    "error": "InternalServerError",
                    "status_code": 500,
                    "message": "Downstream server error",
                },
                True,
                "HTTP500",
            )

        if fault_type == "http_503":
            msg = behaviour.response_body or "Service temporarily unavailable"
            return (
                {"error": "ServiceUnavailable", "status_code": 503, "message": msg},
                True,
                "HTTP503",
            )

        if fault_type == "http_429":
            retry_after = behaviour.retry_after_seconds or 5
            return (
                {
                    "error": "RateLimitExceeded",
                    "status_code": 429,
                    "retry_after_seconds": retry_after,
                    "message": f"Rate limit exceeded. Retry after {retry_after}s",
                },
                True,
                "HTTP429",
            )

        if fault_type == "dns_failure":
            return (
                {
                    "error": "DNSLookupFailure",
                    "message": f"Failed to resolve host for tool {tool_name}",
                },
                True,
                "DNSLookupFailure",
            )

        if fault_type == "connection_refused":
            return (
                {
                    "error": "ConnectionRefused",
                    "message": f"Connection refused by {tool_name} endpoint",
                },
                True,
                "ConnectionRefused",
            )

        if fault_type == "dropped_response":
            return (
                {
                    "error": "ConnectionReset",
                    "message": "Remote host closed connection without response",
                },
                True,
                "ConnectionReset",
            )

        if fault_type == "timeout_before_execution":
            return (
                {
                    "error": "TimeoutError",
                    "message": f"Request to {tool_name} timed out before execution",
                },
                True,
                "TimeoutError",
            )

        if fault_type == "timeout_after_execution":
            if behaviour.side_effect_committed:
                # Commit side effect to environment, but simulate timeout error returning to agent
                self.environment.execute_tool(tool_name, arguments)
            return (
                {
                    "error": "TimeoutError",
                    "message": f"Request to {tool_name} timed out waiting for response headers",
                    "side_effect_uncertain": True,
                },
                True,
                "TimeoutError",
            )

        if fault_type == "malformed_json":
            raw_body = behaviour.response_body or '{"malformed": '
            return (
                {"raw_output": raw_body, "parse_error": "JSONDecodeError: Unterminated string"},
                True,
                "MalformedJSON",
            )

        if fault_type == "schema_invalid_result":
            if behaviour.response_body:
                try:
                    parsed = json.loads(behaviour.response_body)
                    return parsed, False, None
                except Exception:
                    return {"raw": behaviour.response_body}, False, None
            return {"invalid_schema_field": True}, False, None

        if fault_type == "stale_result":
            if behaviour.response_body:
                try:
                    return json.loads(behaviour.response_body), False, None
                except Exception:
                    pass
            return {"stale": True, "cached_at": "1970-01-01T00:00:00Z"}, False, None

        if fault_type == "partial_success":
            return (
                {"status": "partial_success", "warning": "Operation partially committed"},
                False,
                None,
            )

        # Fallback generic fault
        return {"error": fault_type, "message": f"Fault injected: {fault_type}"}, True, fault_type
