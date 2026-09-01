"""
Agent Reliability Lab — SQLAlchemy 2.0 Declarative Database Models.

PostgreSQL is the single source of truth.
All models use Mapped[T] type annotations (SQLAlchemy 2.0+ standard).
JSONB columns store semi-structured data (arguments, snapshots, evidence).
All primary keys are ULIDs (stored as String(26) or String(36)).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    type_annotation_map: ClassVar[dict[Any, Any]] = {
        dict[str, Any]: JSON_TYPE,
        list[dict[str, Any]]: JSON_TYPE,
        list[str]: JSON_TYPE,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Projects & Agents
# ─────────────────────────────────────────────────────────────────────────────


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    agent_definitions: Mapped[list[AgentDefinitionModel]] = relationship(back_populates="project", cascade="all, delete-orphan")
    evaluation_runs: Mapped[list[EvaluationRunModel]] = relationship(back_populates="project", cascade="all, delete-orphan")
    scenarios: Mapped[list[ScenarioModel]] = relationship(back_populates="project", cascade="all, delete-orphan")


class AgentDefinitionModel(Base):
    __tablename__ = "agent_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    framework: Mapped[str] = mapped_column(String(60), nullable=False)  # http, langgraph, openai-agents
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    project: Mapped[ProjectModel] = relationship(back_populates="agent_definitions")
    versions: Mapped[list[AgentVersionModel]] = relationship(back_populates="agent_definition", cascade="all, delete-orphan")


class AgentVersionModel(Base):
    __tablename__ = "agent_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_definition_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    system_prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    endpoint_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    model_config_data: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_TYPE, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    agent_definition: Mapped[AgentDefinitionModel] = relationship(back_populates="versions")
    trials: Mapped[list[TrialModel]] = relationship(back_populates="agent_version")


# ─────────────────────────────────────────────────────────────────────────────
# Scenarios & Environments
# ─────────────────────────────────────────────────────────────────────────────


class ScenarioModel(Base):
    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    project: Mapped[ProjectModel] = relationship(back_populates="scenarios")
    versions: Mapped[list[ScenarioVersionModel]] = relationship(back_populates="scenario", cascade="all, delete-orphan")


class ScenarioVersionModel(Base):
    __tablename__ = "scenario_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(100), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    version_tag: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False)
    environment_name: Mapped[str] = mapped_column(String(100), nullable=False)
    environment_version: Mapped[str] = mapped_column(String(64), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    source_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    tags: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    scenario: Mapped[ScenarioModel] = relationship(back_populates="versions")
    trials: Mapped[list[TrialModel]] = relationship(back_populates="scenario_version")


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation Runs & Trials
# ─────────────────────────────────────────────────────────────────────────────


class EvaluationRunModel(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="CREATED", index=True)
    state_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    run_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    trial_count_total: Mapped[int] = mapped_column(Integer, default=0)
    trial_count_completed: Mapped[int] = mapped_column(Integer, default=0)
    trial_count_passed: Mapped[int] = mapped_column(Integer, default=0)
    trial_count_failed: Mapped[int] = mapped_column(Integer, default=0)
    verdict: Mapped[str | None] = mapped_column(String(40), nullable=True)
    readiness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)

    # Relationships
    project: Mapped[ProjectModel] = relationship(back_populates="evaluation_runs")
    trials: Mapped[list[TrialModel]] = relationship(back_populates="evaluation_run", cascade="all, delete-orphan")
    reports: Mapped[list[ReportModel]] = relationship(back_populates="evaluation_run", cascade="all, delete-orphan")


class TrialModel(Base):
    __tablename__ = "trials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_versions.id"), nullable=False, index=True)
    scenario_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenario_versions.id"), nullable=False, index=True)
    trial_index: Mapped[int] = mapped_column(Integer, nullable=False)
    trial_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING", index=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    turns_count: Mapped[int] = mapped_column(Integer, default=0)
    tool_calls_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    evaluation_run: Mapped[EvaluationRunModel] = relationship(back_populates="trials")
    agent_version: Mapped[AgentVersionModel] = relationship(back_populates="trials")
    scenario_version: Mapped[ScenarioVersionModel] = relationship(back_populates="trials")
    tool_calls: Mapped[list[ToolCallModel]] = relationship(back_populates="trial", cascade="all, delete-orphan")
    fault_events: Mapped[list[FaultEventModel]] = relationship(back_populates="trial", cascade="all, delete-orphan")
    snapshots: Mapped[list[WorldStateSnapshotModel]] = relationship(back_populates="trial", cascade="all, delete-orphan")
    grader_results: Mapped[list[GraderResultModel]] = relationship(back_populates="trial", cascade="all, delete-orphan")
    security_findings: Mapped[list[SecurityFindingModel]] = relationship(back_populates="trial", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_trials_run_trial_index", "run_id", "trial_index", unique=True),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tool Execution, Faults & State Snapshots
# ─────────────────────────────────────────────────────────────────────────────


class ToolCallModel(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trial_id: Mapped[str] = mapped_column(String(36), ForeignKey("trials.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    call_index_in_turn: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    is_fault_injected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    trial: Mapped[TrialModel] = relationship(back_populates="tool_calls")
    result: Mapped[ToolResultModel | None] = relationship(back_populates="tool_call", uselist=False, cascade="all, delete-orphan")


class ToolResultModel(Base):
    __tablename__ = "tool_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tool_call_id: Mapped[str] = mapped_column(String(36), ForeignKey("tool_calls.id", ondelete="CASCADE"), unique=True, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    is_error: Mapped[bool] = mapped_column(Boolean, default=False)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    tool_call: Mapped[ToolCallModel] = relationship(back_populates="result")


class FaultEventModel(Base):
    __tablename__ = "fault_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trial_id: Mapped[str] = mapped_column(String(36), ForeignKey("trials.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    fault_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_tool: Mapped[str] = mapped_column(String(120), nullable=False)
    trigger_invocation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    behaviour_data: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    fault_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    injected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    trial: Mapped[TrialModel] = relationship(back_populates="fault_events")


class WorldStateSnapshotModel(Base):
    __tablename__ = "world_state_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trial_id: Mapped[str] = mapped_column(String(36), ForeignKey("trials.id", ondelete="CASCADE"), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(40), nullable=False)  # pre_trial, post_trial, post_turn
    state_payload: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    trial: Mapped[TrialModel] = relationship(back_populates="snapshots")


# ─────────────────────────────────────────────────────────────────────────────
# Grading, Evidence, Reports, Security & Audit
# ─────────────────────────────────────────────────────────────────────────────


class GraderResultModel(Base):
    __tablename__ = "grader_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trial_id: Mapped[str] = mapped_column(String(36), ForeignKey("trials.id", ondelete="CASCADE"), nullable=False, index=True)
    grader_version_id: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    grader_type: Mapped[str] = mapped_column(String(40), nullable=False)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_critical_failure: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSON_TYPE, default=list)
    evidence_ids: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list)
    graded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    trial: Mapped[TrialModel] = relationship(back_populates="grader_results")


class SecurityFindingModel(Base):
    __tablename__ = "security_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trial_id: Mapped[str] = mapped_column(String(36), ForeignKey("trials.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    owasp_category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)
    remediation: Mapped[str] = mapped_column(Text, default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    trial: Mapped[TrialModel] = relationship(back_populates="security_findings")


class ReportModel(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    verdict: Mapped[str] = mapped_column(String(40), nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    trials_completed: Mapped[int] = mapped_column(Integer, default=0)
    trials_passed: Mapped[int] = mapped_column(Integer, default=0)
    trials_failed: Mapped[int] = mapped_column(Integer, default=0)
    report_format: Mapped[str] = mapped_column(String(20), default="json")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationships
    evaluation_run: Mapped[EvaluationRunModel] = relationship(back_populates="reports")


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(120), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_data: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
