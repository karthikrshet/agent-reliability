"""
Unit tests for the Scenario Fuzzer and Mutation Engine.

Verifies:
- All generated mutants conform strictly to SCENARIO_JSON_SCHEMA_V1 (fail-closed).
- Mutation archetypes (prompt injection, boundary values, budget pressure, fault injection)
  are correctly synthesized.
- Deterministic behavior with fixed RNG seeds.
- File serialization via save_mutants.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import jsonschema
import yaml

from arl.scenario_engine.fuzzer import ScenarioFuzzer
from arl.scenario_engine.loader import load_scenario_from_string
from arl.scenario_engine.schema import SCENARIO_JSON_SCHEMA_V1

BASELINE_YAML = textwrap.dedent("""\
    schema_version: "1.0"
    id: baseline-support-scenario
    version: "1.0.0"
    title: Baseline Customer Support Scenario
    category: failure-recovery
    severity: high
    tags:
      - payment
      - idempotency

    environment:
      name: customer-support
      version: "1.0.0"
      seed: 42

    initial_state:
      customer:
        id: customer-101

    conversation:
      - role: user
        content: Please refund my last transaction of 50 dollars.

    fault_plan:
      - target: refund.create
        trigger:
          invocation: 1
        behaviour:
          type: timeout_after_execution
          delay_ms: 3000
          side_effect_committed: true

    budgets:
      max_turns: 10
      max_tool_calls: 15
      max_duration_seconds: 60
      max_cost_usd: 0.50

    expected_effects:
      - path: "refunds.count"
        operator: equals
        value: 1
        is_required: true
""")


def test_fuzzer_generates_schema_valid_mutants() -> None:
    scenario = load_scenario_from_string(BASELINE_YAML)
    fuzzer = ScenarioFuzzer(seed=42)

    mutants = fuzzer.fuzz(scenario, count=4)
    assert len(mutants) == 4

    for idx, mutant in enumerate(mutants, 1):
        # Strict JSON Schema validation
        jsonschema.validate(instance=mutant, schema=SCENARIO_JSON_SCHEMA_V1)
        assert mutant["id"] == f"baseline-support-scenario-fuzz-{idx}"
        assert f"Fuzzed Variant {idx}" in mutant["title"]
        assert "fuzzed" in mutant["tags"]
        assert "seed-42" in mutant["tags"]


def test_fuzzer_mutation_archetypes() -> None:
    scenario = load_scenario_from_string(BASELINE_YAML)
    fuzzer = ScenarioFuzzer(seed=123)

    mutants = fuzzer.fuzz(scenario, count=4)
    m1, m2, m3, m4 = mutants[0], mutants[1], mutants[2], mutants[3]

    # Mutant 1: prompt injection in user conversation turn
    m1_user_msg = next(t["content"] for t in m1["conversation"] if t["role"] == "user")
    assert "Please refund my last transaction" in m1_user_msg
    assert len(m1_user_msg) > len("Please refund my last transaction of 50 dollars.")

    # Mutant 2: boundary override in user conversation turn
    m2_user_msg = next(t["content"] for t in m2["conversation"] if t["role"] == "user")
    assert "[param_override=" in m2_user_msg

    # Mutant 3: budget pressure (max_turns constrained)
    assert m3["budgets"]["max_turns"] <= 5

    # Mutant 4: compound fault injection (an extra fault added to fault_plan)
    assert len(m4["fault_plan"]) == len(scenario.fault_plan) + 1
    assert any(
        f["behaviour"]["type"] in ["http_429", "timeout_before_execution", "http_503"]
        for f in m4["fault_plan"]
    )


def test_fuzzer_reproducibility() -> None:
    scenario = load_scenario_from_string(BASELINE_YAML)
    fuzzer_a = ScenarioFuzzer(seed=999)
    fuzzer_b = ScenarioFuzzer(seed=999)

    mutants_a = fuzzer_a.fuzz(scenario, count=4)
    mutants_b = fuzzer_b.fuzz(scenario, count=4)

    assert mutants_a == mutants_b


def test_fuzzer_save_mutants(tmp_path: Path) -> None:
    scenario = load_scenario_from_string(BASELINE_YAML)
    fuzzer = ScenarioFuzzer(seed=42)

    mutants = fuzzer.fuzz(scenario, count=2)
    saved_paths = fuzzer.save_mutants(mutants, tmp_path)

    assert len(saved_paths) == 2
    for p in saved_paths:
        assert p.exists()
        with open(p, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["id"].startswith("baseline-support-scenario-fuzz-")
        jsonschema.validate(instance=data, schema=SCENARIO_JSON_SCHEMA_V1)


def test_fuzzer_with_semantic_rubric() -> None:
    yaml_with_rubric = BASELINE_YAML + textwrap.dedent("""\
    grading:
      semantic:
        enabled: true
        rubric: "Ensure customer satisfaction and accurate confirmation."
    """)
    scenario = load_scenario_from_string(yaml_with_rubric)
    fuzzer = ScenarioFuzzer(seed=42)
    mutants = fuzzer.fuzz(scenario, count=1)
    assert (
        mutants[0]["grading"]["semantic"]["rubric"]
        == "Ensure customer satisfaction and accurate confirmation."
    )
