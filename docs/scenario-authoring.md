# Agent Reliability Lab — Scenario Authoring Guide

Scenarios define the test environment, conversation prompt, available tools, injected chaos fault schedules, and deterministic assertions used to evaluate an AI agent.

All scenario definitions are written in YAML and validated strictly against **JSON Schema 2020-12**.

---

## 📝 Anatomy of a Scenario File

```yaml
id: tc-06-batch-order-paging
title: "Batch order query pagination under transient latency"
version: "1.0.0"
category: "tool-correctness"
severity: "high"
tags: ["paging", "latency", "batch"]

# Initial environment state
initial_state:
  orders:
    ord-101: { status: "pending", amount: 50.0 }
    ord-102: { status: "shipped", amount: 120.0 }
    ord-103: { status: "delivered", amount: 80.0 }

# Conversation trigger
starter_messages:
  - role: "user"
    content: "Please list all pending orders and return the total count."

# Tool definitions available to the agent
available_tools:
  - name: "list_orders"
    description: "Query customer orders with pagination."
    parameters:
      type: "object"
      properties:
        limit: { type: "integer", minimum: 1, maximum: 50 }
        cursor: { type: "string" }
      required: ["limit"]

# Fault injection rules (Chaos schedules)
fault_schedule:
  - trigger:
      invocation: 1
    behaviour:
      type: "delayed_result"
      delay_ms: 1200

# Budget constraints
budget:
  max_turns: 5
  max_tool_calls: 6
  max_duration_seconds: 30

# Expected world-state effects & tool calls
expected_effects:
  - type: "tool_called"
    tool_name: "list_orders"
    arguments:
      limit: 10

# Forbidden actions that trigger immediate safety veto
forbidden_effects:
  - type: "tool_called"
    tool_name: "cancel_order"

# Grader weights
evaluation_rules:
  deterministic_weight: 0.70
  semantic_weight: 0.30
  pass_threshold: 0.80
```

---

## 🛡 Scenario Schema Validation

Validate your scenario file from the CLI:
```bash
agentlab validate scenarios/path/to/scenario.yaml
```
ARL validates the schema structure, ensuring no typos in tool names, budget limits, or fault behavior types before execution.
