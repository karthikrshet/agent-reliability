"""
Agent Reliability Lab — Production Incident-to-Scenario Synthesizer.

Ingests production traces, error logs, and post-mortem incident payloads
(e.g., OpenTelemetry, Sentry, Datadog, or native JSON crash dumps), extracts
root-cause fault events and triggers, and deterministically synthesizes schema-valid
ARL evaluation scenarios (SCENARIO_JSON_SCHEMA_V1) for automated regression gating.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, ClassVar

import yaml

from arl.scenario_engine.loader import load_scenario_from_string
from arl.scenario_engine.schema import ParsedScenario


def _slugify(text: str) -> str:
    """Normalize arbitrary string into a valid schema-compliant kebab-case ID."""
    clean = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    clean = re.sub(r"^-+|-+$", "", clean)
    if not clean:
        clean = "synthesized-incident"
    return clean[:90]


class IncidentSynthesizer:
    """Synthesizes deterministic ARL scenario specifications from raw production incident traces."""

    VALID_FAULT_TYPES: ClassVar[set[str]] = {
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
    }

    VALID_CATEGORIES: ClassVar[set[str]] = {
        "tool-correctness",
        "failure-recovery",
        "state-and-memory",
        "security",
        "resource-control",
    }

    def classify_fault_behaviour(self, event: dict[str, Any]) -> dict[str, Any]:
        """Classify raw error details into a schema-valid FaultBehaviourSpec dict."""
        explicit_type = event.get("fault_type") or event.get("behaviour_type")
        if explicit_type and explicit_type in self.VALID_FAULT_TYPES:
            behaviour: dict[str, Any] = {"type": explicit_type}
            if "delay_ms" in event:
                behaviour["delay_ms"] = int(event["delay_ms"])
            if "http_status" in event:
                behaviour["http_status"] = int(event["http_status"])
            if "retry_after_seconds" in event:
                behaviour["retry_after_seconds"] = int(event["retry_after_seconds"])
            return behaviour

        status_code = event.get("http_status") or event.get("status_code")
        error_msg = str(event.get("error_message") or event.get("error") or "").lower()

        if status_code == 429 or "rate limit" in error_msg or "too many requests" in error_msg:
            return {
                "type": "http_429",
                "http_status": 429,
                "retry_after_seconds": int(event.get("retry_after_seconds", 3)),
            }

        if "deadlock" in error_msg or "database locked" in error_msg:
            return {"type": "database_deadlock"}

        if "redis" in error_msg:
            return {"type": "redis_unavailability"}

        if "timeout" in error_msg or "timed out" in error_msg or "deadline exceeded" in error_msg:
            delay = int(event.get("delay_ms", 5000))
            return {"type": "timeout_after_execution", "delay_ms": delay}

        if (
            "connection refused" in error_msg
            or "econnrefused" in error_msg
            or "connection reset" in error_msg
        ):
            return {"type": "connection_refused"}

        if "dns" in error_msg or "getaddrinfo" in error_msg:
            return {"type": "dns_failure"}

        if "json" in error_msg or "decode error" in error_msg or "unexpected token" in error_msg:
            return {"type": "malformed_json"}

        if status_code == 503 or "service unavailable" in error_msg:
            return {"type": "http_503", "http_status": 503}

        if (
            status_code == 500
            or "internal server error" in error_msg
            or "unhandled exception" in error_msg
        ):
            return {"type": "http_500", "http_status": 500}

        # Default fallback for unclassified failure event
        return {"type": "http_500", "http_status": 500}

    def synthesize_from_dict(
        self,
        trace: dict[str, Any],
        *,
        scenario_id: str | None = None,
        category: str | None = None,
        severity: str | None = None,
    ) -> dict[str, Any]:
        """Synthesize a schema-valid scenario dictionary from an incident trace dictionary."""
        # 1. Identifier
        raw_id = (
            scenario_id
            or trace.get("incident_id")
            or trace.get("id")
            or trace.get("summary")
            or "incident-replay"
        )
        final_id = _slugify(str(raw_id))

        # 2. Category & Severity
        chosen_cat = category or trace.get("category") or "failure-recovery"
        if chosen_cat not in self.VALID_CATEGORIES:
            chosen_cat = "failure-recovery"

        chosen_sev = severity or trace.get("severity") or "high"
        if chosen_sev not in ("critical", "high", "medium", "low", "info"):
            chosen_sev = "high"

        # 3. Title & Description
        raw_title = trace.get("title") or trace.get("summary") or f"Incident Replay: {final_id}"
        title = str(raw_title)[:180]
        desc = str(
            trace.get("description")
            or trace.get("summary")
            or f"Synthesized regression scenario derived from incident {final_id}."
        )

        # 4. Environment
        env_spec: dict[str, Any] = {
            "name": trace.get("environment") or trace.get("service") or "customer-support",
            "version": "1.0.0",
            "seed": int(trace.get("seed", 42)),
        }

        # 5. Conversation Extraction
        conv: list[dict[str, str]] = []
        if "conversation" in trace and isinstance(trace["conversation"], list):
            conv.extend(
                {"role": str(msg["role"]), "content": str(msg["content"])}
                for msg in trace["conversation"]
                if isinstance(msg, dict) and "role" in msg and "content" in msg
            )
        elif "prompt" in trace:
            conv.append({"role": "user", "content": str(trace["prompt"])})
        elif "messages" in trace and isinstance(trace["messages"], list):
            conv.extend(
                {
                    "role": str(msg.get("role", "user")),
                    "content": str(msg["content"]),
                }
                for msg in trace["messages"]
                if isinstance(msg, dict) and "content" in msg
            )

        if not conv:
            conv = [
                {
                    "role": "user",
                    "content": f"Please resolve production issue: {desc}",
                }
            ]

        # 6. Fault Plan Extraction
        fault_plan: list[dict[str, Any]] = []
        raw_events = (
            trace.get("trace_events")
            or trace.get("events")
            or trace.get("tool_calls")
            or trace.get("faults")
            or []
        )

        tool_invocation_counts: dict[str, int] = {}
        for event in raw_events:
            if not isinstance(event, dict):
                continue

            tool_name = (
                event.get("tool_name")
                or event.get("target")
                or event.get("name")
                or event.get("component")
                or "api_call"
            )
            count = tool_invocation_counts.get(tool_name, 0) + 1
            tool_invocation_counts[tool_name] = count

            is_fault = (
                event.get("status") in ("error", "failed", "fault")
                or event.get("http_status", 200) >= 400
                or "error" in event
                or "error_message" in event
                or "fault_type" in event
            )

            if is_fault:
                behaviour = self.classify_fault_behaviour(event)
                trigger: dict[str, Any] = {"invocation": count}
                if "after_seconds" in event:
                    trigger["after_seconds"] = float(event["after_seconds"])
                if "arguments" in event and isinstance(event["arguments"], dict):
                    trigger["argument_contains"] = event["arguments"]

                fault_plan.append(
                    {
                        "target": tool_name,
                        "trigger": trigger,
                        "behaviour": behaviour,
                    }
                )

        # 7. Budgets
        budgets = {
            "max_turns": max(6, int(trace.get("max_turns", 10))),
            "max_tool_calls": max(5, len(raw_events) * 2 or 10),
            "max_duration_seconds": max(30, int(trace.get("max_duration_seconds", 60))),
        }

        # 8. Expected and Forbidden Effects
        expected_effects: list[dict[str, Any]] = []
        forbidden_effects: list[dict[str, Any]] = []

        if "forbidden_actions" in trace and isinstance(trace["forbidden_actions"], list):
            for fb in trace["forbidden_actions"]:
                if isinstance(fb, dict) and "tool_name" in fb:
                    fb_item: dict[str, Any] = {
                        "tool_call": {
                            "name": fb["tool_name"],
                        },
                        "description": fb.get("reason", "Action forbidden after fault trigger"),
                        "severity": fb.get("severity", "critical"),
                    }
                    if "arguments" in fb:
                        fb_item["tool_call"]["argument_match"] = fb["arguments"]
                    forbidden_effects.append(fb_item)

        # Build complete scenario specification
        scenario_data: dict[str, Any] = {
            "schema_version": "1.0",
            "id": final_id,
            "version": "1.0.0",
            "title": title,
            "category": chosen_cat,
            "severity": chosen_sev,
            "tags": list({*trace.get("tags", []), "incident-replay", "auto-synthesized"}),
            "description": desc,
            "environment": env_spec,
            "conversation": conv,
            "budgets": budgets,
        }

        if fault_plan:
            scenario_data["fault_plan"] = fault_plan
        if expected_effects:
            scenario_data["expected_effects"] = expected_effects
        if forbidden_effects:
            scenario_data["forbidden_effects"] = forbidden_effects

        scenario_data["grading"] = {
            "deterministic": {"required": True},
            "trajectory": {"required": True},
        }

        return scenario_data

    def synthesize_to_yaml(
        self,
        trace: dict[str, Any],
        *,
        scenario_id: str | None = None,
        category: str | None = None,
        severity: str | None = None,
    ) -> str:
        """Synthesize scenario dictionary and serialize to canonical YAML."""
        data = self.synthesize_from_dict(
            trace, scenario_id=scenario_id, category=category, severity=severity
        )
        return yaml.dump(data, sort_keys=False, allow_unicode=True)

    def synthesize_scenario(
        self,
        trace: dict[str, Any],
        *,
        scenario_id: str | None = None,
        category: str | None = None,
        severity: str | None = None,
    ) -> ParsedScenario:
        """Synthesize and rigorously validate against ARL JSON Schema 2020-12."""
        yaml_content = self.synthesize_to_yaml(
            trace, scenario_id=scenario_id, category=category, severity=severity
        )
        return load_scenario_from_string(yaml_content)

    def synthesize_file(
        self,
        trace_path: Path | str,
        output_path: Path | str | None = None,
        *,
        scenario_id: str | None = None,
        category: str | None = None,
        severity: str | None = None,
    ) -> Path:
        """Read incident trace JSON from disk and output validated scenario YAML."""
        t_path = Path(trace_path)
        with open(t_path, encoding="utf-8") as f:
            trace_data = json.load(f)

        yaml_content = self.synthesize_to_yaml(
            trace_data, scenario_id=scenario_id, category=category, severity=severity
        )

        # Strict validation
        load_scenario_from_string(yaml_content)

        out = t_path.with_suffix(".yaml") if output_path is None else Path(output_path)

        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        return out
