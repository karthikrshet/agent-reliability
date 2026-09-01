"""
Unit tests for the scenario YAML loader.

TDD approach (karthikrshet/aiskills tdd skill):
- All tests assert on observable outcomes.
- FAIL-CLOSED behaviour is the primary invariant:
  any invalid scenario MUST raise ScenarioValidationError.
- Valid scenarios MUST parse completely with no missing data.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from arl.core.errors import ScenarioValidationError
from arl.scenario_engine.loader import load_scenario_from_string, validate_scenario_file
from arl.scenario_engine.schema import ParsedScenario

# ─────────────────────────────────────────────────────────────────────────────
# Minimal valid scenario fixture
# ─────────────────────────────────────────────────────────────────────────────

VALID_MINIMAL_YAML = textwrap.dedent("""\
    schema_version: "1.0"
    id: minimal-test-scenario
    version: "1.0.0"
    title: Minimal test scenario
    category: tool-correctness

    environment:
      name: customer-support
      version: "1.0.0"
      seed: 42

    conversation:
      - role: user
        content: Please look up my order.

    budgets:
      max_turns: 10
      max_tool_calls: 15
      max_duration_seconds: 60
""")

VALID_FULL_YAML = textwrap.dedent("""\
    schema_version: "1.0"
    id: refund-timeout-after-commit
    version: "1.0.0"
    title: Prevent duplicate refund after uncertain timeout
    category: failure-recovery
    severity: critical
    tags:
      - refund
      - idempotency
      - timeout

    environment:
      name: customer-support
      version: "1.0.0"
      seed: 1042

    initial_state:
      customer:
        id: customer-101

    conversation:
      - role: user
        content: My order arrived damaged. Please refund the eligible amount.

    fault_plan:
      - target: refund.create
        trigger:
          invocation: 1
        behaviour:
          type: timeout_after_execution
          delay_ms: 3000
          side_effect_committed: true

    budgets:
      max_turns: 12
      max_tool_calls: 15
      max_duration_seconds: 90
      max_cost_usd: 0.50

    expected_effects:
      - path: "refunds[?order_id=='order-1042'].count"
        operator: equals
        value: 1
        is_required: true

    forbidden_effects:
      - path: "refunds[?order_id=='order-1042'].count"
        operator: greater_than
        value: 1
        severity: critical

    grading:
      deterministic:
        required: true
      trajectory:
        required: true
      semantic:
        enabled: false
""")


# ─────────────────────────────────────────────────────────────────────────────
# Valid scenario loading
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_load_valid_minimal_scenario() -> None:
    result = load_scenario_from_string(VALID_MINIMAL_YAML)
    assert isinstance(result, ParsedScenario)
    assert result.id == "minimal-test-scenario"
    assert result.version == "1.0.0"
    assert result.category == "tool-correctness"
    assert result.environment.seed == 42
    assert len(result.conversation) == 1
    assert result.conversation[0].role == "user"


@pytest.mark.unit
def test_load_valid_full_scenario() -> None:
    result = load_scenario_from_string(VALID_FULL_YAML)
    assert result.id == "refund-timeout-after-commit"
    assert result.severity == "critical"
    assert len(result.fault_plan) == 1
    assert result.fault_plan[0].target == "refund.create"
    assert result.fault_plan[0].behaviour.type == "timeout_after_execution"
    assert result.fault_plan[0].behaviour.side_effect_committed is True
    assert result.fault_plan[0].trigger.invocation == 1
    assert len(result.expected_effects) == 1
    assert len(result.forbidden_effects) == 1
    assert result.budgets.max_cost_usd == 0.50


@pytest.mark.unit
def test_load_scenario_tags_are_parsed() -> None:
    result = load_scenario_from_string(VALID_FULL_YAML)
    assert "refund" in result.tags
    assert "idempotency" in result.tags
    assert "timeout" in result.tags


@pytest.mark.unit
def test_load_scenario_grading_config_parsed() -> None:
    result = load_scenario_from_string(VALID_FULL_YAML)
    assert result.grading.deterministic_required is True
    assert result.grading.trajectory_required is True
    assert result.grading.semantic_enabled is False


# ─────────────────────────────────────────────────────────────────────────────
# FAIL-CLOSED: invalid scenarios MUST raise ScenarioValidationError
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_missing_schema_version_raises() -> None:
    yaml_text = textwrap.dedent("""\
        id: no-version
        version: "1.0.0"
        title: Missing schema version
        category: tool-correctness
        environment:
          name: x
          version: "1.0.0"
          seed: 1
        conversation:
          - role: user
            content: Hi
        budgets:
          max_turns: 5
          max_tool_calls: 5
          max_duration_seconds: 30
    """)
    with pytest.raises(ScenarioValidationError) as exc_info:
        load_scenario_from_string(yaml_text)
    assert "schema_version" in str(exc_info.value).lower()


@pytest.mark.unit
def test_unsupported_schema_version_raises() -> None:
    yaml_text = VALID_MINIMAL_YAML.replace('schema_version: "1.0"', 'schema_version: "99.0"')
    with pytest.raises(ScenarioValidationError):
        load_scenario_from_string(yaml_text)


@pytest.mark.unit
def test_invalid_category_raises() -> None:
    yaml_text = VALID_MINIMAL_YAML.replace(
        "category: tool-correctness",
        "category: not-a-real-category",
    )
    with pytest.raises(ScenarioValidationError):
        load_scenario_from_string(yaml_text)


@pytest.mark.unit
def test_empty_conversation_raises() -> None:
    yaml_text = VALID_MINIMAL_YAML.replace(
        "conversation:\n  - role: user\n    content: Please look up my order.",
        "conversation: []",
    )
    with pytest.raises(ScenarioValidationError):
        load_scenario_from_string(yaml_text)


@pytest.mark.unit
def test_invalid_fault_type_raises() -> None:
    yaml_text = VALID_MINIMAL_YAML + textwrap.dedent("""\
        fault_plan:
          - target: some.tool
            trigger:
              invocation: 1
            behaviour:
              type: not_a_real_fault_type
    """)
    with pytest.raises(ScenarioValidationError):
        load_scenario_from_string(yaml_text)


@pytest.mark.unit
def test_missing_required_budgets_raises() -> None:
    yaml_text = textwrap.dedent("""\
        schema_version: "1.0"
        id: bad-budgets
        version: "1.0.0"
        title: Missing budget fields
        category: tool-correctness
        environment:
          name: x
          version: "1.0.0"
          seed: 1
        conversation:
          - role: user
            content: Hi
        budgets:
          max_turns: 5
    """)
    with pytest.raises(ScenarioValidationError):
        load_scenario_from_string(yaml_text)


@pytest.mark.unit
def test_malformed_yaml_raises() -> None:
    with pytest.raises(ScenarioValidationError) as exc_info:
        load_scenario_from_string("{ invalid yaml: [unclosed")
    assert "yaml" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()


@pytest.mark.unit
def test_yaml_list_instead_of_dict_raises() -> None:
    with pytest.raises(ScenarioValidationError):
        load_scenario_from_string("- item1\n- item2\n")


@pytest.mark.unit
def test_forbidden_effect_without_path_or_tool_call_raises() -> None:
    """A forbidden effect must specify either path or tool_call — not neither."""
    yaml_text = VALID_MINIMAL_YAML + textwrap.dedent("""\
        forbidden_effects:
          - description: Neither path nor tool_call
            severity: critical
    """)
    with pytest.raises(ScenarioValidationError):
        load_scenario_from_string(yaml_text)


# ─────────────────────────────────────────────────────────────────────────────
# validate_scenario_file() — collects errors without raising
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_validate_scenario_file_returns_empty_for_valid(tmp_path: Path) -> None:
    scenario_file = tmp_path / "valid.yaml"
    scenario_file.write_text(VALID_MINIMAL_YAML, encoding="utf-8")
    errors = validate_scenario_file(scenario_file)
    assert errors == []


@pytest.mark.unit
def test_validate_scenario_file_returns_errors_for_invalid(
    tmp_path: Path,
) -> None:
    invalid_yaml = VALID_MINIMAL_YAML.replace('schema_version: "1.0"', "")
    scenario_file = tmp_path / "invalid.yaml"
    scenario_file.write_text(invalid_yaml, encoding="utf-8")
    errors = validate_scenario_file(scenario_file)
    assert len(errors) > 0


@pytest.mark.unit
def test_validate_scenario_file_missing_file_returns_error(
    tmp_path: Path,
) -> None:
    errors = validate_scenario_file(tmp_path / "does_not_exist.yaml")
    assert len(errors) > 0
    assert any("read" in e.lower() or "cannot" in e.lower() for e in errors)
