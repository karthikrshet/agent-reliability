"""
Scenarios catalog and validation router.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from arl.scenario_engine.loader import load_scenario, load_scenario_from_string
from arl.scenario_engine.schema import ParsedScenario

router = APIRouter(prefix="/api/v1/scenarios", tags=["Scenarios"])

SCENARIOS_DIR = Path("scenarios")


class ScenarioSummaryResponse(BaseModel):
    id: str
    version: str
    title: str
    category: str
    severity: str
    tags: list[str]
    description: str


class ValidateScenarioRequest(BaseModel):
    yaml_content: str = Field(..., min_length=1)


class ValidationResponse(BaseModel):
    is_valid: bool
    scenario_id: str | None = None
    title: str | None = None
    errors: list[str] = Field(default_factory=list)


def _discover_scenarios() -> list[ParsedScenario]:
    """Helper to discover all scenario files on disk."""
    scenarios: list[ParsedScenario] = []
    if not SCENARIOS_DIR.exists():
        return scenarios

    for yaml_file in SCENARIOS_DIR.rglob("*.yaml"):
        try:
            scenario, _, _ = load_scenario(yaml_file)
            scenarios.append(scenario)
        except Exception:
            continue
    return scenarios


@router.get("", response_model=list[ScenarioSummaryResponse])
async def list_scenarios(category: str | None = None) -> list[ScenarioSummaryResponse]:
    """List all available canonical test scenarios."""
    all_scenarios = _discover_scenarios()

    if category:
        all_scenarios = [s for s in all_scenarios if s.category == category]

    return [
        ScenarioSummaryResponse(
            id=s.id,
            version=s.version,
            title=s.title,
            category=s.category,
            severity=s.severity,
            tags=s.tags,
            description=s.description,
        )
        for s in all_scenarios
    ]


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str) -> dict[str, Any]:
    """Get full scenario definition by ID."""
    all_scenarios = _discover_scenarios()
    matched = next((s for s in all_scenarios if s.id == scenario_id), None)

    if matched is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario '{scenario_id}' not found",
        )

    return matched.model_dump()


@router.post("/validate", response_model=ValidationResponse)
async def validate_scenario(req: ValidateScenarioRequest) -> ValidationResponse:
    """Validate a scenario YAML string against JSON Schema 2020-12 and domain rules."""
    try:
        scenario = load_scenario_from_string(req.yaml_content)
        return ValidationResponse(
            is_valid=True,
            scenario_id=scenario.id,
            title=scenario.title,
            errors=[],
        )
    except Exception as exc:
        return ValidationResponse(
            is_valid=False,
            scenario_id=None,
            title=None,
            errors=[str(exc)],
        )
