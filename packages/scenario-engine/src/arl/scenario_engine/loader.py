"""
Agent Reliability Lab — Fail-Closed Scenario Loader.

Loading is FAIL-CLOSED: any validation failure raises ScenarioValidationError.
There is no silent fallback, no partial loading, no default substitution for
missing required fields. An invalid scenario NEVER executes.

This principle follows the tdd skill (karthikrshet/aiskills):
tests for this loader assert that invalid scenarios raise, not pass.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, cast

import jsonschema
import yaml

from arl.core.errors import ScenarioValidationError
from arl.scenario_engine.schema import (
    SCENARIO_JSON_SCHEMA_V1,
    SUPPORTED_SCHEMA_VERSIONS,
    BudgetSpec,
    ConversationMessage,
    EffectSpec,
    FaultBehaviourSpec,
    FaultPlanEntrySpec,
    FaultTriggerSpec,
    ForbiddenEffectSpec,
    GradingSpec,
    ParsedScenario,
    ScenarioEnvironmentSpec,
)

logger = logging.getLogger(__name__)


def _get_schema_for_version(version: str) -> dict[str, Any]:
    """Return the JSON Schema for a given schema_version string.

    Raises ScenarioValidationError if the version is unsupported.
    """
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ScenarioValidationError(
            path="<unknown>",
            errors=[
                f"Unsupported schema_version {version!r}. "
                f"Supported versions: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
            ],
        )
    # Currently only v1.0 exists
    return SCENARIO_JSON_SCHEMA_V1


def _load_raw_yaml(path: Path) -> dict[str, Any]:
    """Load and parse YAML from path.

    Raises ScenarioValidationError on YAML parse errors.
    Never allows arbitrary Python object deserialization (yaml.safe_load).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScenarioValidationError(
            path=str(path),
            errors=[f"Cannot read scenario file: {exc}"],
        ) from exc

    try:
        data = yaml.safe_load(text)  # safe_load: no arbitrary Python objects
    except yaml.YAMLError as exc:
        raise ScenarioValidationError(
            path=str(path),
            errors=[f"YAML parse error: {exc}"],
        ) from exc

    if not isinstance(data, dict):
        raise ScenarioValidationError(
            path=str(path),
            errors=["Scenario file must be a YAML mapping (dict), not a list or scalar."],
        )

    return cast(dict[str, Any], data)


def _validate_against_schema(
    data: dict[str, Any],
    path: str,
) -> None:
    """Validate raw YAML data against the JSON Schema.

    Collects ALL validation errors (not just the first) and raises a
    ScenarioValidationError with the full list.
    """
    version = data.get("schema_version", "<missing>")
    schema = _get_schema_for_version(str(version))

    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))

    if errors:
        error_messages = [
            f"[{'/'.join(str(p) for p in e.path) or 'root'}] {e.message}"
            for e in errors
        ]
        raise ScenarioValidationError(path=path, errors=error_messages)


def _parse_scenario(data: dict[str, Any]) -> ParsedScenario:
    """Convert validated raw dict to a typed ParsedScenario.

    At this point the data has already passed JSON Schema validation,
    so Pydantic validation should not fail. If it does, re-raise as
    ScenarioValidationError (defensive).
    """
    from pydantic import ValidationError

    grading_raw = data.get("grading", {})
    grading = GradingSpec(
        deterministic_required=grading_raw.get("deterministic", {}).get("required", True),
        trajectory_required=grading_raw.get("trajectory", {}).get("required", True),
        semantic_enabled=grading_raw.get("semantic", {}).get("enabled", False),
        semantic_rubric=grading_raw.get("semantic", {}).get("rubric"),
    )

    fault_plan_entries = [
        FaultPlanEntrySpec(
            target=entry["target"],
            trigger=FaultTriggerSpec(**entry.get("trigger", {})),
            behaviour=FaultBehaviourSpec(
                type=entry["behaviour"]["type"],
                delay_ms=entry["behaviour"].get("delay_ms", 0),
                http_status=entry["behaviour"].get("http_status"),
                retry_after_seconds=entry["behaviour"].get("retry_after_seconds"),
                side_effect_committed=entry["behaviour"].get("side_effect_committed", False),
                response_body=entry["behaviour"].get("response_body"),
            ),
        )
        for entry in data.get("fault_plan", [])
    ]

    try:
        return ParsedScenario(
            schema_version=data["schema_version"],
            id=data["id"],
            version=data["version"],
            title=data["title"],
            category=data["category"],
            severity=data.get("severity", "medium"),
            tags=data.get("tags", []),
            description=data.get("description", ""),
            environment=ScenarioEnvironmentSpec(**data["environment"]),
            initial_state=data.get("initial_state", {}),
            conversation=[ConversationMessage(**m) for m in data["conversation"]],
            fault_plan=fault_plan_entries,
            budgets=BudgetSpec(**data["budgets"]),
            expected_effects=[EffectSpec(**e) for e in data.get("expected_effects", [])],
            forbidden_effects=[ForbiddenEffectSpec(**e) for e in data.get("forbidden_effects", [])],
            grading=grading,
            metadata=data.get("metadata", {}),
        )
    except ValidationError as exc:
        raise ScenarioValidationError(
            path="<in-memory>",
            errors=[str(e) for e in exc.errors()],
        ) from exc


def load_scenario(path: Path | str) -> tuple[ParsedScenario, str, str]:
    """Load, validate, and parse a scenario YAML file.

    Returns (parsed_scenario, source_yaml, source_hash).

    FAIL-CLOSED: any error raises ScenarioValidationError.
    Never returns a partially-valid scenario.

    Args:
        path: Path to the scenario YAML file.

    Returns:
        A 3-tuple:
            - parsed_scenario: Fully typed ParsedScenario
            - source_yaml: Raw YAML text (for storage)
            - source_hash: SHA-256 of source_yaml (for integrity)

    Raises:
        ScenarioValidationError: If the file cannot be read, parsed,
            schema-validated, or Pydantic-validated.
    """
    resolved = Path(path)
    logger.debug("Loading scenario from %s", resolved)

    raw_data = _load_raw_yaml(resolved)
    _validate_against_schema(raw_data, str(resolved))
    parsed = _parse_scenario(raw_data)

    # Re-read the raw YAML for storage (we want the exact bytes)
    source_yaml = resolved.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(source_yaml.encode()).hexdigest()

    logger.info(
        "Loaded scenario id=%s version=%s from %s",
        parsed.id,
        parsed.version,
        resolved,
    )
    return parsed, source_yaml, source_hash


def load_scenario_from_string(yaml_text: str, *, source_label: str = "<string>") -> ParsedScenario:
    """Load and validate a scenario from a YAML string.

    Useful for testing and API ingestion.

    FAIL-CLOSED: raises ScenarioValidationError on any validation failure.
    """
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise ScenarioValidationError(
            path=source_label,
            errors=[f"YAML parse error: {exc}"],
        ) from exc

    if not isinstance(data, dict):
        raise ScenarioValidationError(
            path=source_label,
            errors=["Scenario must be a YAML mapping."],
        )

    _validate_against_schema(data, source_label)
    return _parse_scenario(data)


def validate_scenario_file(path: Path | str) -> list[str]:
    """Validate a scenario file and return a list of error messages.

    Returns an empty list if the scenario is valid.
    Does NOT raise — use this for the `agentlab validate` CLI command.

    Unlike load_scenario(), this collects errors without raising,
    allowing the CLI to display all problems at once.
    """
    resolved = Path(path)
    errors: list[str] = []

    try:
        raw_data = _load_raw_yaml(resolved)
    except ScenarioValidationError as exc:
        return cast(list[str], exc.context.get("errors", [str(exc)]))

    version = raw_data.get("schema_version", "<missing>")
    try:
        schema = _get_schema_for_version(str(version))
    except ScenarioValidationError as exc:
        return cast(list[str], exc.context.get("errors", [str(exc)]))

    validator = jsonschema.Draft202012Validator(schema)
    json_errors = sorted(validator.iter_errors(raw_data), key=lambda e: list(e.path))
    errors.extend(
        f"[{'/'.join(str(p) for p in e.path) or 'root'}] {e.message}"
        for e in json_errors
    )

    if not errors:
        try:
            _parse_scenario(raw_data)
        except ScenarioValidationError as exc:
            errors.extend(exc.context.get("errors", [str(exc)]))

    return errors
