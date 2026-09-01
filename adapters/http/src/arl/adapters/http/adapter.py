"""
Agent Reliability Lab — HTTP/REST Agent Adapter with SSRF Protection.

Implements the AgentAdapter protocol for testing any agent exposed via
HTTP/REST endpoints.

SSRF DEFENSE:
Target URLs are validated before requests are dispatched. Requests to private
IP ranges, loopback addresses, link-local addresses, or cloud metadata endpoints
(169.254.169.254) are rejected with SecurityViolationError unless
ARL_ALLOW_LOCALHOST_TARGETS=true is explicitly configured for local testing.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
import contextlib
import ipaddress
import logging
import os
import socket
from urllib.parse import urlparse

import httpx

from arl.core.errors import InfrastructureError, SecurityViolationError
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

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / Cloud metadata
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("::1/128"),          # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),        # IPv6 link-local
]


def validate_url_for_ssrf(url: str, allow_localhost: bool = False) -> None:
    """Validate that the target URL does not resolve to private or cloud metadata IPs.

    Raises SecurityViolationError if target resolves to a forbidden range.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SecurityViolationError(
            violation_type="INVALID_SCHEME",
            detail=f"Invalid URL scheme '{parsed.scheme}'. Only http and https are permitted.",
            resource=url,
        )

    hostname = parsed.hostname
    if not hostname:
        raise SecurityViolationError(
            violation_type="MISSING_HOSTNAME",
            detail="Missing hostname in endpoint URL.",
            resource=url,
        )

    # Allow localhost only when explicitly enabled
    if allow_localhost and hostname in ("localhost", "127.0.0.1", "::1"):
        return

    try:
        # Resolve hostname to all IPs
        addr_infos = socket.getaddrinfo(hostname, None)
        ips = {info[4][0] for info in addr_infos}
    except socket.gaierror as exc:
        raise InfrastructureError(
            message=f"Failed to resolve target hostname '{hostname}': {exc}",
            component="HttpAgentAdapter",
        ) from exc

    for ip_str in ips:
        ip = ipaddress.ip_address(ip_str)
        for net in BLOCKED_NETWORKS:
            if ip in net:
                # If localhost is explicitly allowed and this is a loopback address, pass
                if allow_localhost and (ip.is_loopback or ip_str in ("127.0.0.1", "::1")):
                    continue
                raise SecurityViolationError(
                    violation_type="SSRF_PROTECTION",
                    detail=f"SSRF protection: Target IP {ip_str} falls within blocked network {net}",
                    resource=f"{url} ({ip_str})",
                )


class HttpAgentAdapter(AgentAdapter):
    """HTTP Agent Adapter communicating with remote agent REST endpoints."""

    def __init__(
        self,
        endpoint_url: str,
        timeout_seconds: float = 30.0,
        allow_localhost: bool | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds
        self.allow_localhost = (
            allow_localhost
            if allow_localhost is not None
            else os.getenv("ARL_ALLOW_LOCALHOST_TARGETS", "").lower() in ("true", "1", "yes")
        )
        self.headers = headers or {}
        self._client: httpx.AsyncClient | None = None

        # Pre-validate endpoint for SSRF
        validate_url_for_ssrf(self.endpoint_url, allow_localhost=self.allow_localhost)

    @property
    def adapter_id(self) -> str:
        return "http-v1"

    @property
    def framework(self) -> str:
        return "http"

    @property
    def adapter_version(self) -> str:
        return "1.0.0"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout_seconds, headers=self.headers)
        return self._client

    async def start_session(self, context: SessionContext) -> AgentSession:
        validate_url_for_ssrf(self.endpoint_url, allow_localhost=self.allow_localhost)
        client = await self._get_client()

        payload = {
            "session_id": context.session_id,
            "trial_id": context.trial_id,
            "available_tools": context.available_tools,
            "initial_messages": context.initial_messages,
            "max_turns": context.max_turns,
        }

        try:
            resp = await client.post(f"{self.endpoint_url}/sessions", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Failed to start HTTP agent session at %s: %s", self.endpoint_url, exc)
            # Default session initialization if /sessions is not an explicit endpoint
            data = {}

        return AgentSession(
            session_id=context.session_id,
            trial_id=context.trial_id,
            agent_version_id=context.agent_version_id,
            framework="http",
            adapter_state=data.get("adapter_state", {}),
        )

    async def send(self, session: AgentSession, message: AgentInput) -> AgentOutput:
        validate_url_for_ssrf(self.endpoint_url, allow_localhost=self.allow_localhost)
        client = await self._get_client()

        payload = {
            "session_id": session.session_id,
            "turn_index": message.turn_index,
            "tool_results": message.tool_results,
            "user_messages": message.user_messages,
        }

        try:
            resp = await client.post(f"{self.endpoint_url}/turn", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            return AgentOutput(
                output_type=AgentOutputType.ERROR,
                turn_index=message.turn_index,
                error_code=f"HTTP_{exc.response.status_code}",
                error_message=f"Agent endpoint returned error status {exc.response.status_code}",
            )
        except Exception as exc:
            return AgentOutput(
                output_type=AgentOutputType.ERROR,
                turn_index=message.turn_index,
                error_code="CONNECTION_ERROR",
                error_message=f"Failed to communicate with agent endpoint: {exc}",
            )

        # Parse tool calls if returned
        tool_calls: list[ToolCallRecord] = []
        for tc in data.get("tool_calls", []):
            tool_calls.append(
                ToolCallRecord(
                    tool_call_id=tc.get("id", f"tc-{len(tool_calls)}"),
                    tool_name=tc.get("name", tc.get("function", {}).get("name", "")),
                    arguments=tc.get("arguments", tc.get("function", {}).get("arguments", {})),
                )
            )

        raw_type = data.get("type", "tool_calls" if tool_calls else "text")
        output_type = AgentOutputType(raw_type) if raw_type in AgentOutputType._value2member_map_ else AgentOutputType.TEXT

        return AgentOutput(
            output_type=output_type,
            turn_index=message.turn_index,
            raw_text=data.get("text") or data.get("message"),
            tool_calls=tool_calls,
            prompt_tokens=data.get("usage", {}).get("prompt_tokens"),
            completion_tokens=data.get("usage", {}).get("completion_tokens"),
            total_tokens=data.get("usage", {}).get("total_tokens"),
            cost_usd=data.get("usage", {}).get("cost_usd"),
            model_name=data.get("model"),
        )

    async def resume(self, session: AgentSession, interruption: InterruptionResolution) -> AgentOutput:
        client = await self._get_client()
        payload = {
            "session_id": session.session_id,
            "approved": interruption.approved,
            "resolution": interruption.resolution_payload,
        }
        resp = await client.post(f"{self.endpoint_url}/resume", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return AgentOutput(
            output_type=AgentOutputType.FINISHED,
            turn_index=0,
            raw_text=data.get("text", "Resumed"),
        )

    async def cancel(self, session: AgentSession) -> None:
        client = await self._get_client()
        with contextlib.suppress(Exception):
            await client.post(f"{self.endpoint_url}/cancel", json={"session_id": session.session_id})

    async def stream(self, session: AgentSession, message: AgentInput) -> AsyncIterator[AgentOutput]:
        output = await self.send(session, message)
        yield output

    async def close_session(self, session: AgentSession) -> None:
        if self._client and not self._client.is_closed:
            with contextlib.suppress(Exception):
                await self._client.post(f"{self.endpoint_url}/close", json={"session_id": session.session_id})
            await self._client.aclose()
