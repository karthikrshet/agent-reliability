"""
Agent Reliability Lab — Real HTTP Reference Agent Server.

A standalone HTTP reference agent implementing the ARL AgentAdapter contract.
Runs on http://127.0.0.1:8088. Responds to multi-turn conversation inputs and
executes stateful tool calls (lookup_order, issue_refund) for reliability evaluation.
"""

from __future__ import annotations

import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="ARL Real HTTP Reference Agent",
    description="Standalone HTTP Agent Endpoint implementing the ARL AgentAdapter contract",
    version="1.0.0",
)


class ToolCallItem(BaseModel):
    id: str = Field(default_factory=lambda: f"tc-{uuid.uuid4().hex[:8]}")
    name: str
    arguments: dict[str, Any]


class AgentSessionRequest(BaseModel):
    session_id: str
    trial_id: str
    available_tools: list[Any] = Field(default_factory=list)
    initial_messages: list[dict[str, Any]] = Field(default_factory=list)
    max_turns: int = 5


class AgentInputRequest(BaseModel):
    session_id: str
    turn_index: int
    user_messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)


sessions: dict[str, dict[str, Any]] = {}


@app.get("/healthz")
async def health_check() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "agent": "arl-real-http-agent"}


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


@app.post("/turn")
@app.post("/")
@app.post("/agent")
async def handle_turn(req: AgentInputRequest) -> dict[str, Any]:
    """Handle a multi-turn agent conversation step with fault retry support."""
    session_data = sessions.setdefault(
        req.session_id, {"retries": 0, "history": [], "last_tool": None, "last_args": None}
    )

    if req.tool_results:
        has_error = False
        for r in req.tool_results:
            content = r.get("output") or r.get("result") or {}
            if isinstance(content, dict) and ("error" in content or content.get("status_code") == 500):
                has_error = True
            elif isinstance(content, str) and ("error" in content.lower() or "500" in content):
                has_error = True
        
        # Retry once if an error occurred (e.g. HTTP 500 retry scenario)
        if has_error and session_data.get("retries", 0) < 1 and session_data.get("last_tool"):
            session_data["retries"] = session_data.get("retries", 0) + 1
            return {
                "type": "tool_calls",
                "text": None,
                "tool_calls": [
                    {
                        "id": f"tc-{uuid.uuid4().hex[:8]}",
                        "name": session_data["last_tool"],
                        "arguments": session_data["last_args"],
                    }
                ],
                "usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
            }

        if has_error:
            return {
                "type": "text",
                "text": "I apologize for the temporary disruption. I have noted your request and recorded the details.",
                "tool_calls": [],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            }

        return {
            "type": "text",
            "text": "Your request has been successfully processed in our system. Let me know if you need anything else!",
            "tool_calls": [],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    user_text = ""
    for msg in req.user_messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            user_text += content.lower() + " "

    # Dynamic entity extraction
    cust_id = "customer-101"
    if "customer-a" in user_text:
        cust_id = "customer-A"
    elif "customer-b" in user_text:
        cust_id = "customer-B"

    import re
    order_match = re.search(r"(order[-_]\w+|ord[-_]\w+)", user_text)
    order_id = order_match.group(1) if order_match else ("order-A-001" if cust_id == "customer-A" else "order-1001")

    if "refund" in user_text:
        tool_name = "refund.create"
        tool_args = {"order_id": order_id, "amount_usd": 49.99, "reason": "Customer requested full refund"}
        session_data["last_tool"] = tool_name
        session_data["last_args"] = tool_args
        return {
            "type": "tool_calls",
            "text": None,
            "tool_calls": [
                {
                    "id": f"tc-{uuid.uuid4().hex[:8]}",
                    "name": tool_name,
                    "arguments": tool_args,
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
        }

    if "cancel" in user_text:
        tool_name = "order.cancel"
        tool_args = {"order_id": order_id}
        session_data["last_tool"] = tool_name
        session_data["last_args"] = tool_args
        return {
            "type": "tool_calls",
            "text": None,
            "tool_calls": [
                {
                    "id": f"tc-{uuid.uuid4().hex[:8]}",
                    "name": tool_name,
                    "arguments": tool_args,
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
        }

    if "lookup" in user_text or "order" in user_text or "status" in user_text:
        tool_name = "order.lookup"
        tool_args = {"order_id": order_id, "customer_id": cust_id}
        session_data["last_tool"] = tool_name
        session_data["last_args"] = tool_args
        return {
            "type": "tool_calls",
            "text": None,
            "tool_calls": [
                {
                    "id": f"tc-{uuid.uuid4().hex[:8]}",
                    "name": tool_name,
                    "arguments": tool_args,
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40},
        }

    return {
        "type": "text",
        "text": "Hello! I am your customer support reference assistant. How can I assist you with your orders today?",
        "tool_calls": [],
        "usage": {"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
    }


@app.post("/close")
@app.post("/cancel")
async def close_or_cancel(req: dict[str, Any]) -> dict[str, str]:
    return {"status": "closed"}


@app.post("/resume")
async def resume(req: dict[str, Any]) -> dict[str, str]:
    return {"status": "resumed", "text": "Resumed"}


if __name__ == "__main__":
    print("Starting ARL Reference HTTP Agent on http://127.0.0.1:8088 ...")
    uvicorn.run(app, host="127.0.0.1", port=8088, log_level="info")
