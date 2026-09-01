"""
Agent Reliability Lab — Scenario YAML Schema v1.0.

Defines the JSON Schema used to validate scenario YAML files.
Scenario loading is FAIL-CLOSED: a scenario that fails validation
will never execute. There is no fallback or partial loading.

This module also provides Pydantic models for the parsed scenario
structure, which are used by the loader and graders.

Design (ADR-004):
- JSON Schema is the source of truth for the scenario format.
- Pydantic models are derived from (and consistent with) the JSON Schema.
- Version the schema — breaking changes require a new schema_version.
- Seeds are mandatory — no scenario may produce non-deterministic faults.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ─────────────────────────────────────────────────────────────────────────────
# JSON Schema for scenario YAML (v1.0)
# Used by jsonschema.validate() in the loader for strict structural validation.
# ─────────────────────────────────────────────────────────────────────────────

SCENARIO_JSON_SCHEMA_V1: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://agent-reliability-lab.dev/schemas/scenario/v1.0.json",
    "title": "Agent Reliability Lab Scenario Schema v1.0",
    "description": "Schema for ARL scenario YAML files",
    "type": "object",
    "required": [
        "schema_version",
        "id",
        "version",
        "title",
        "category",
        "environment",
        "conversation",
        "budgets",
    ],
    "additionalProperties": False,
    "properties": {
        "schema_version": {
            "type": "string",
            "const": "1.0",
            "description": "Scenario schema version. Must be '1.0' for this schema.",
        },
        "id": {
            "type": "string",
            "pattern": "^[a-z0-9][a-z0-9-]{0,98}[a-z0-9]$",
            "description": "Stable kebab-case scenario identifier",
        },
        "version": {
            "type": "string",
            "pattern": r"^\d+\.\d+\.\d+$",
            "description": "Semantic version (e.g. 1.0.0)",
        },
        "title": {"type": "string", "minLength": 1, "maxLength": 200},
        "category": {
            "type": "string",
            "enum": [
                "tool-correctness",
                "failure-recovery",
                "state-and-memory",
                "security",
                "resource-control",
            ],
        },
        "severity": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low", "info"],
            "default": "medium",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "uniqueItems": True,
        },
        "description": {"type": "string", "maxLength": 5000},
        "environment": {
            "type": "object",
            "required": ["name", "version", "seed"],
            "additionalProperties": False,
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "version": {"type": "string", "minLength": 1},
                "seed": {"type": "integer", "description": "Deterministic seed for data generation"},
            },
        },
        "initial_state": {
            "type": "object",
            "description": "Overrides to the seeded initial environment state",
            "additionalProperties": True,
        },
        "conversation": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["role", "content"],
                "additionalProperties": False,
                "properties": {
                    "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                    "content": {"type": "string", "minLength": 1},
                },
            },
        },
        "fault_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["target", "trigger", "behaviour"],
                "additionalProperties": False,
                "properties": {
                    "target": {"type": "string", "minLength": 1},
                    "trigger": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "invocation": {"type": "integer", "minimum": 1},
                            "after_seconds": {"type": "number", "minimum": 0},
                            "argument_contains": {"type": "object"},
                        },
                    },
                    "behaviour": {
                        "type": "object",
                        "required": ["type"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": [
                                    "connection_refused",
                                    "dns_failure",
                                    "timeout_before_execution",
                                    "timeout_after_execution",
                                    "http_429",
                                    "http_500",
                                    "http_503",
                                    "malformed_json",
                                    "schema_invalid_result",
                                    "empty_result",
                                    "delayed_result",
                                    "duplicated_result",
                                    "stale_result",
                                    "partial_success",
                                    "dropped_response",
                                    "reordered_concurrent_responses",
                                    "cancellation_during_execution",
                                    "worker_termination",
                                    "database_deadlock",
                                    "redis_unavailability",
                                ],
                            },
                            "delay_ms": {"type": "integer", "minimum": 0},
                            "http_status": {"type": "integer"},
                            "retry_after_seconds": {"type": "integer", "minimum": 0},
                            "side_effect_committed": {"type": "boolean"},
                            "response_body": {"type": "string"},
                        },
                        "additionalProperties": True,
                    },
                },
            },
        },
        "budgets": {
            "type": "object",
            "required": ["max_turns", "max_tool_calls", "max_duration_seconds"],
            "additionalProperties": False,
            "properties": {
                "max_turns": {"type": "integer", "minimum": 1, "maximum": 100},
                "max_tool_calls": {"type": "integer", "minimum": 1, "maximum": 200},
                "max_duration_seconds": {"type": "integer", "minimum": 1, "maximum": 3600},
                "max_cost_usd": {"type": "number", "minimum": 0},
                "max_prompt_tokens": {"type": "integer", "minimum": 1},
                "max_completion_tokens": {"type": "integer", "minimum": 1},
            },
        },
        "expected_effects": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["path", "operator", "value"],
                "additionalProperties": False,
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "operator": {
                        "type": "string",
                        "enum": [
                            "equals",
                            "not_equals",
                            "greater_than",
                            "greater_than_or_equal",
                            "less_than",
                            "less_than_or_equal",
                            "contains",
                            "not_contains",
                            "exists",
                            "not_exists",
                            "matches_regex",
                        ],
                    },
                    "value": {},
                    "description": {"type": "string"},
                    "is_required": {"type": "boolean", "default": True},
                },
            },
        },
        "forbidden_effects": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "path": {"type": "string"},
                    "operator": {"type": "string"},
                    "value": {},
                    "tool_call": {
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": "string"},
                            "argument_match": {"type": "object"},
                        },
                    },
                    "description": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                        "default": "critical",
                    },
                },
            },
        },
        "grading": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "deterministic": {
                    "type": "object",
                    "properties": {"required": {"type": "boolean"}},
                },
                "trajectory": {
                    "type": "object",
                    "properties": {"required": {"type": "boolean"}},
                },
                "semantic": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "rubric": {"type": "string"},
                    },
                },
            },
        },
        "metadata": {
            "type": "object",
            "additionalProperties": {"type": "string"},
        },
    },
}

# Supported schema versions — add new versions here
SUPPORTED_SCHEMA_VERSIONS: frozenset[str] = frozenset({"1.0"})


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models for parsed scenario content
# ─────────────────────────────────────────────────────────────────────────────


class ScenarioEnvironmentSpec(BaseModel):
    model_config = {"frozen": True}
    name: str
    version: str
    seed: int


class ConversationMessage(BaseModel):
    model_config = {"frozen": True}
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)


class FaultTriggerSpec(BaseModel):
    model_config = {"frozen": True}
    invocation: int | None = None
    after_seconds: float | None = None
    argument_contains: dict[str, Any] | None = None


class FaultBehaviourSpec(BaseModel):
    model_config = {"frozen": True}
    type: str
    delay_ms: int = 0
    http_status: int | None = None
    retry_after_seconds: int | None = None
    side_effect_committed: bool = False
    response_body: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class FaultPlanEntrySpec(BaseModel):
    model_config = {"frozen": True}
    target: str
    trigger: FaultTriggerSpec
    behaviour: FaultBehaviourSpec


class BudgetSpec(BaseModel):
    model_config = {"frozen": True}
    max_turns: int
    max_tool_calls: int
    max_duration_seconds: int
    max_cost_usd: float | None = None
    max_prompt_tokens: int | None = None
    max_completion_tokens: int | None = None


class EffectSpec(BaseModel):
    model_config = {"frozen": True}
    path: str
    operator: str
    value: Any
    description: str = ""
    is_required: bool = True


class ForbiddenEffectSpec(BaseModel):
    model_config = {"frozen": True}
    path: str | None = None
    operator: str | None = None
    value: Any = None
    tool_call: dict[str, Any] | None = None
    description: str = ""
    severity: str = "critical"

    @model_validator(mode="after")
    def validate_constraint(self) -> "ForbiddenEffectSpec":
        if self.path is None and self.tool_call is None:
            msg = "ForbiddenEffectSpec must specify either 'path' or 'tool_call'"
            raise ValueError(msg)
        return self


class GradingSpec(BaseModel):
    model_config = {"frozen": True}
    deterministic_required: bool = True
    trajectory_required: bool = True
    semantic_enabled: bool = False
    semantic_rubric: str | None = None


class ParsedScenario(BaseModel):
    """Fully parsed and validated scenario.

    This is the output of the scenario loader — a strongly-typed
    representation of the YAML content after schema validation.
    """

    model_config = {"frozen": True}

    schema_version: str
    id: str
    version: str
    title: str
    category: str
    severity: str = "medium"
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    environment: ScenarioEnvironmentSpec
    initial_state: dict[str, Any] = Field(default_factory=dict)
    conversation: list[ConversationMessage]
    fault_plan: list[FaultPlanEntrySpec] = Field(default_factory=list)
    budgets: BudgetSpec
    expected_effects: list[EffectSpec] = Field(default_factory=list)
    forbidden_effects: list[ForbiddenEffectSpec] = Field(default_factory=list)
    grading: GradingSpec = Field(default_factory=GradingSpec)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v: str) -> str:
        if v not in SUPPORTED_SCHEMA_VERSIONS:
            msg = (
                f"Unsupported schema_version {v!r}. "
                f"Supported: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
            )
            raise ValueError(msg)
        return v
