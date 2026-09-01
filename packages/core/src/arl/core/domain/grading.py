"""
Agent Reliability Lab — Grading and Reporting Domain Entities.

Entities: Grader, GraderVersion, GraderResult, Evidence, Baseline,
Regression, Report, AuditEvent.

Grading is strictly separated:
- Deterministic graders: world-state, effects, budget, idempotency
  → Always run first; findings CANNOT be overridden by model judges
- Statistical graders: pass@k, confidence intervals, regression detection
- Model-based graders: helpfulness, communication clarity (optional)

Every verdict must link to execution IDs, grader versions, and evidence.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class GraderType(str, enum.Enum):
    """Category of grader."""

    DETERMINISTIC = "deterministic"
    STATISTICAL = "statistical"
    MODEL_BASED = "model_based"


class GraderCategory(str, enum.Enum):
    """Specific grader function."""

    WORLD_STATE = "world_state"
    EXPECTED_EFFECT = "expected_effect"
    FORBIDDEN_EFFECT = "forbidden_effect"
    TOOL_SELECTION = "tool_selection"
    TOOL_ARGUMENT = "tool_argument"
    TOOL_ORDER = "tool_order"
    IDEMPOTENCY = "idempotency"
    BUDGET = "budget"
    AUTHORIZATION = "authorization"
    DATA_ISOLATION = "data_isolation"
    COMPLETION_EVIDENCE = "completion_evidence"
    PASS_AT_K = "pass_at_k"
    CONFIDENCE_INTERVAL = "confidence_interval"
    REGRESSION = "regression"
    HELPFULNESS = "helpfulness"
    COMMUNICATION = "communication"
    SEMANTIC_EQUIVALENCE = "semantic_equivalence"


class FindingSeverity(str, enum.Enum):
    """Severity levels for grader findings."""

    CRITICAL = "critical"  # Triggers NOT_READY; e.g. forbidden effect, isolation violation
    HIGH = "high"  # Strong signal for NOT_READY
    MEDIUM = "medium"  # Informs score but may not block readiness
    LOW = "low"  # Informational
    INFO = "info"  # Trace-level detail


class ReadinessVerdict(str, enum.Enum):
    """Overall readiness verdict for an evaluation run.

    NOT_READY is the default. READY requires passing all deterministic
    checks and meeting the configured readiness threshold.
    INSUFFICIENT_EVIDENCE requires more trials.
    """

    READY = "READY"
    NOT_READY = "NOT_READY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class Grader(BaseModel):
    """Definition of a grader registered in the system."""

    model_config = {"frozen": True}

    id: str
    name: str = Field(..., min_length=1, max_length=120)
    grader_type: GraderType
    category: GraderCategory
    description: str = Field(default="", max_length=2000)
    is_blocking: bool = Field(
        default=False,
        description="If True, a FAIL from this grader triggers NOT_READY regardless of score",
    )


class GraderVersion(BaseModel):
    """A specific versioned snapshot of a grader.

    Model-based graders record their judge model + prompt version here
    so that grading can be reproduced or audited.
    """

    model_config = {"frozen": True}

    id: str
    grader_id: str
    version_tag: str
    grader_type: GraderType
    # For model-based graders
    judge_model: str | None = Field(default=None)
    judge_provider: str | None = Field(default=None)
    judge_temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    prompt_hash: str | None = Field(
        default=None,
        description="SHA-256 of the judge prompt for change detection",
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GraderResult(BaseModel):
    """The output of a single grader for a single trial.

    Security note: Finding descriptions must be HTML-escaped before
    rendering. Grader results may describe agent behaviour that included
    prompt injection attempts.
    """

    model_config = {"frozen": True}

    id: str
    trial_id: str
    grader_version_id: str
    category: GraderCategory
    grader_type: GraderType

    passed: bool | None = Field(
        default=None,
        description="For deterministic graders. None if grader errored.",
    )
    score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Normalised 0-1 score for scored graders",
    )
    severity: FindingSeverity | None = Field(
        default=None,
        description="Severity of the most severe finding in this result",
    )
    is_critical_failure: bool = Field(
        default=False,
        description="True if this result alone triggers NOT_READY verdict",
    )
    is_grader_error: bool = Field(
        default=False,
        description="True if the grader itself failed — not a fake pass",
    )
    # Human-readable findings
    summary: str = Field(
        default="",
        max_length=500,
        description="Brief finding summary. HTML-escape before rendering.",
    )
    findings: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Structured finding records. Schema varies by grader category.",
    )
    # Evidence links
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="IDs of Evidence records supporting this result",
    )
    graded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # Model-judge metadata (model_based graders only)
    judge_reason: str | None = Field(
        default=None,
        description="Model judge's stated reasoning. Informational only.",
    )
    judge_raw_output: str | None = Field(
        default=None,
        description="Raw judge output. SECURITY: treat as untrusted.",
    )


class Evidence(BaseModel):
    """A piece of evidence supporting a grader finding.

    Every verdict must link to evidence records. Evidence links to:
    - Execution ID (run, trial)
    - Scenario and environment versions
    - Agent version
    - Tool calls or state snapshots
    - Timestamps
    - Trace IDs
    """

    model_config = {"frozen": True}

    id: str
    trial_id: str
    run_id: str
    grader_result_id: str | None = Field(default=None)
    evidence_type: str = Field(
        ...,
        description=(
            "Type: tool_call, world_state_snapshot, fault_event, "
            "audit_record, budget_record, isolation_check"
        ),
    )
    # Reference to the source record
    source_entity_type: str = Field(..., description="Entity type: ToolCall, FaultEvent, etc.")
    source_entity_id: str = Field(..., description="ULID of the referenced entity")
    # Human-readable summary
    description: str = Field(default="", max_length=1000)
    # Structured data — schema depends on evidence_type
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    trace_id: str | None = Field(default=None, description="OTEL trace ID")


class Baseline(BaseModel):
    """A stored performance baseline for regression comparison.

    Baselines must be explicitly created — they are not auto-computed.
    This prevents accidental regression baseline updates from poor runs.
    """

    model_config = {"frozen": True}

    id: str
    project_id: str
    agent_version_id: str
    scenario_version_id: str
    environment_version_id: str
    run_id: str = Field(..., description="The run this baseline was derived from")
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    # Stored metrics
    pass_rate: float = Field(..., ge=0.0, le=1.0)
    pass_rate_lower_ci: float = Field(..., ge=0.0, le=1.0)
    pass_rate_upper_ci: float = Field(..., ge=0.0, le=1.0)
    trial_count: int = Field(..., gt=0)
    mean_cost_usd: float | None = Field(default=None, ge=0.0)
    mean_latency_ms: float | None = Field(default=None, ge=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str


class Regression(BaseModel):
    """A detected regression between two evaluation runs.

    A regression is detected when the candidate run's metrics are
    statistically significantly worse than the baseline.
    """

    model_config = {"frozen": True}

    id: str
    project_id: str
    baseline_id: str
    candidate_run_id: str
    is_regression: bool
    # Statistical significance
    p_value: float | None = Field(default=None, ge=0.0, le=1.0)
    significance_level: float = Field(default=0.05)
    # Delta
    baseline_pass_rate: float = Field(..., ge=0.0, le=1.0)
    candidate_pass_rate: float = Field(..., ge=0.0, le=1.0)
    pass_rate_delta: float
    # Human-readable explanation
    summary: str = Field(default="", max_length=1000)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Report(BaseModel):
    """A generated evaluation report.

    Reports are generated from persisted evidence — never from in-memory
    state or hardcoded values.

    Security note: report_html must have all untrusted content HTML-escaped
    before rendering. The Content-Security-Policy header must block inline
    scripts.
    """

    model_config = {"frozen": True}

    id: str
    run_id: str
    project_id: str
    verdict: ReadinessVerdict
    overall_score: float | None = Field(default=None, ge=0.0, le=100.0)
    confidence_level: float | None = Field(default=None, ge=0.0, le=1.0)
    # Category scores — each is 0-100
    task_completion_score: float | None = Field(default=None, ge=0.0, le=100.0)
    tool_selection_score: float | None = Field(default=None, ge=0.0, le=100.0)
    argument_correctness_score: float | None = Field(default=None, ge=0.0, le=100.0)
    failure_recovery_score: float | None = Field(default=None, ge=0.0, le=100.0)
    state_consistency_score: float | None = Field(default=None, ge=0.0, le=100.0)
    security_isolation_score: float | None = Field(default=None, ge=0.0, le=100.0)
    cost_efficiency_score: float | None = Field(default=None, ge=0.0, le=100.0)
    # Critical failures
    critical_failures: list[str] = Field(default_factory=list)
    # Summary
    trials_completed: int = Field(..., ge=0)
    trials_passed: int = Field(..., ge=0)
    trials_failed: int = Field(..., ge=0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    report_format: str = Field(
        ...,
        pattern=r"^(json|html|junit|text)$",
        description="Report format: json, html, junit, or text",
    )


class AuditEvent(BaseModel):
    """An immutable audit log entry.

    Security rationale: Audit events are append-only. They record all
    security-relevant actions: permission changes, run creation, report
    access, cancellations, and administrative corrections.

    Audit events must not contain secrets, PII beyond identifiers, or
    full request/response bodies.
    """

    model_config = {"frozen": True}

    id: str
    event_type: str = Field(
        ..., description="e.g. run.created, permission.changed, report.exported"
    )
    actor_id: str = Field(..., description="User or service that performed the action")
    actor_type: str = Field(..., description="user | service | worker | system")
    resource_type: str = Field(..., description="e.g. EvaluationRun, Report, Project")
    resource_id: str
    project_id: str | None = Field(default=None)
    # SECURITY: no secrets, no PII beyond identifiers, no full bodies
    event_data: dict[str, str] = Field(
        default_factory=dict,
        description="String key-value data. Must not contain secrets or sensitive PII.",
    )
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = Field(default=None)
    trace_id: str | None = Field(default=None)
    ip_address: str | None = Field(
        default=None,
        description="Redacted or hashed IP for audit purposes",
    )
