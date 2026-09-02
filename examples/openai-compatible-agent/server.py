"""
Local OpenAI-Compatible Model Endpoint Mock for offline evaluation and testing.

Simulates an OpenAI ChatCompletions API on port 8089 responding to tool definitions.
"""

from __future__ import annotations

import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI, Header
from pydantic import BaseModel, Field

app = FastAPI(
    title="Local OpenAI-Compatible Mock Server",
    description="Local ChatCompletions endpoint simulating OpenAI function calling",
    version="1.0.0",
)


class ChatMessage(BaseModel):
    role: str
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[ChatMessage]
    tools: list[dict[str, Any]] = Field(default_factory=list)
    temperature: float = 0.0


@app.get("/healthz")
@app.get("/v1/models")
async def get_models() -> dict[str, Any]:
    return {"object": "list", "data": [{"id": "gpt-4o-mini", "object": "model"}]}


@app.post("/v1/chat/completions")
async def create_chat_completion(
    req: ChatCompletionRequest,
    _authorization: str | None = Header(default=None, alias="authorization"),
) -> dict[str, Any]:
    """Simulate OpenAI ChatCompletions with tool calling."""
    # Check if returning from tool response
    last_msg = req.messages[-1] if req.messages else None
    if last_msg and last_msg.role == "tool":
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "I have successfully retrieved your order information. Your order status is confirmed!",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 140,
                "completion_tokens": 25,
                "total_tokens": 165,
            },
        }

    # First turn: check user message and return tool call if tools available
    user_text = ""
    for m in req.messages:
        if m.role == "user" and m.content:
            user_text += m.content.lower() + " "

    if req.tools and (
        "order" in user_text or "lookup" in user_text or "status" in user_text
    ):
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": f"call_{uuid.uuid4().hex[:8]}",
                                "type": "function",
                                "function": {
                                    "name": "lookup_order",
                                    "arguments": '{"order_id": "ord-001", "customer_id": "cust-001"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 110,
                "completion_tokens": 30,
                "total_tokens": 140,
            },
        }

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I assist you with your customer account today?",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 15,
            "total_tokens": 65,
        },
    }


if __name__ == "__main__":
    print("Starting Local OpenAI-Compatible Server on http://127.0.0.1:8089 ...")
    uvicorn.run(app, host="127.0.0.1", port=8089, log_level="warning")
