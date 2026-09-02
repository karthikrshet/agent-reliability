"""
Agent Reliability Lab — Deterministic HTTP Reference Agent Server.

A standalone HTTP reference endpoint demonstrating the Agent Reliability Lab
protocol contract using deterministic keyword dispatching (not an LLM). Responds
to multi-turn conversation inputs and executes stateful tool calls.

Run with:
    python examples/deterministic-http-reference-agent/server.py
"""

from __future__ import annotations

import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="ARL Deterministic HTTP Reference Agent",
    description="Deterministic HTTP Reference Endpoint implementing the ARL AgentAdapter contract",
    version="1.0.0",
)


class ToolCallItem(BaseModel):
    id: str = Field(default_factory=lambda: f"tc-{uuid.uuid4().hex[:8]}")
    tool_name: str
    arguments: dict[str, Any]


class AgentSessionRequest(BaseModel):
    session_id: str
    trial_id: str
    available_tools: list[str] = Field(default_factory=list)
    initial_messages: list[dict[str, Any]] = Field(default_factory=list)
    max_turns: int = 5


class AgentInputRequest(BaseModel):
    session_id: str
    turn_index: int
    user_messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)


class AgentOutputResponse(BaseModel):
    output_type: str = "tool_calls"  # "tool_calls", "message", or "interrupted"
    message_content: str | None = None
    tool_calls: list[ToolCallItem] = Field(default_factory=list)
    token_usage: dict[str, int] | None = None


# Active in-memory session store
sessions: dict[str, dict[str, Any]] = {}


@app.get("/healthz")
async def health_check() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "agent": "arl-deterministic-http-reference-agent"}


@app.post("/sessions")
async def create_session(req: AgentSessionRequest) -> dict[str, Any]:
    """Initialize a multi-turn evaluation session."""
    sessions[req.session_id] = {
        "trial_id": req.trial_id,
        "available_tools": req.available_tools,
        "history": [],
    }
    return {
        "session_id": req.session_id,
        "status": "ready",
        "adapter_state": {"initialized": True},
    }


@app.post("/")
@app.post("/agent")
async def handle_turn(req: AgentInputRequest) -> AgentOutputResponse:
    """Handle a multi-turn agent conversation step."""
    # 1. Check if tool results from previous turn were provided
    if req.tool_results:
        # Check if any error occurred in tool execution
        has_error = any("error" in r.get("result", {}) for r in req.tool_results)
        if has_error:
            # Demonstrate resilient recovery: apologize and return fallback message
            return AgentOutputResponse(
                output_type="message",
                message_content="I apologize for the temporary disruption. I have noted your request and recorded the details.",
                tool_calls=[],
                token_usage=None,
            )

        # Successful tool result -> generate final resolution message
        return AgentOutputResponse(
            output_type="message",
            message_content="Your request has been successfully processed in our system. Let me know if you need anything else!",
            tool_calls=[],
            token_usage=None,
        )

    # 2. Extract latest user query text
    user_text = ""
    for msg in req.user_messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            user_text += content.lower() + " "

    # 3. Decision logic: select appropriate tool call based on query
    if "lookup" in user_text or "order" in user_text or "status" in user_text:
        return AgentOutputResponse(
            output_type="tool_calls",
            message_content=None,
            tool_calls=[
                ToolCallItem(
                    tool_name="lookup_order",
                    arguments={"order_id": "ord-001", "customer_id": "cust-001"},
                )
            ],
            token_usage=None,
        )

    if "refund" in user_text or "cancel" in user_text:
        return AgentOutputResponse(
            output_type="tool_calls",
            message_content=None,
            tool_calls=[
                ToolCallItem(
                    tool_name="issue_refund",
                    arguments={
                        "order_id": "ord-001",
                        "amount": 25.0,
                        "idempotency_key": f"ref-{uuid.uuid4().hex[:6]}",
                    },
                )
            ],
            token_usage=None,
        )

    # Default fallback message
    return AgentOutputResponse(
        output_type="message",
        message_content="Hello! I am your customer support reference assistant. How can I assist you with your orders today?",
        tool_calls=[],
        token_usage=None,
    )


if __name__ == "__main__":
    print("Starting ARL Deterministic Reference HTTP Agent on http://127.0.0.1:8088 ...")
    uvicorn.run(app, host="127.0.0.1", port=8088, log_level="warning")
