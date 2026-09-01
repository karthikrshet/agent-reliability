"""Initial schema for Agent Reliability Lab

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-09-01 20:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Projects
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"])

    # Agent Definitions
    op.create_table(
        "agent_definitions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("framework", sa.String(60), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_agent_definitions_project_id", "agent_definitions", ["project_id"])

    # Agent Versions
    op.create_table(
        "agent_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_definition_id", sa.String(36), sa.ForeignKey("agent_definitions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_tag", sa.String(64), nullable=False),
        sa.Column("system_prompt_hash", sa.String(64), nullable=True),
        sa.Column("endpoint_url", sa.String(500), nullable=True),
        sa.Column("model_config_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_versions_agent_def_id", "agent_versions", ["agent_definition_id"])

    # Scenarios
    op.create_table(
        "scenarios",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_scenarios_project_id", "scenarios", ["project_id"])
    op.create_index("ix_scenarios_category", "scenarios", ["category"])

    # Scenario Versions
    op.create_table(
        "scenario_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scenario_id", sa.String(100), sa.ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_tag", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.String(16), nullable=False),
        sa.Column("environment_name", sa.String(100), nullable=False),
        sa.Column("environment_version", sa.String(64), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("source_yaml", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scenario_versions_scenario_id", "scenario_versions", ["scenario_id"])

    # Evaluation Runs
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state", sa.String(40), nullable=False, server_default="CREATED"),
        sa.Column("state_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_seed", sa.Integer(), nullable=False),
        sa.Column("trial_count_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trial_count_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trial_count_passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trial_count_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verdict", sa.String(40), nullable=True),
        sa.Column("readiness_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(120), nullable=False),
    )
    op.create_index("ix_evaluation_runs_project_id", "evaluation_runs", ["project_id"])
    op.create_index("ix_evaluation_runs_state", "evaluation_runs", ["state"])

    # Trials
    op.create_table(
        "trials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_version_id", sa.String(36), sa.ForeignKey("agent_versions.id"), nullable=False),
        sa.Column("scenario_version_id", sa.String(36), sa.ForeignKey("scenario_versions.id"), nullable=False),
        sa.Column("trial_index", sa.Integer(), nullable=False),
        sa.Column("trial_seed", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(40), nullable=False, server_default="PENDING"),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("worker_id", sa.String(100), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("turns_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tool_calls_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_trials_run_id", "trials", ["run_id"])
    op.create_index("ix_trials_agent_version_id", "trials", ["agent_version_id"])
    op.create_index("ix_trials_scenario_version_id", "trials", ["scenario_version_id"])
    op.create_index("ix_trials_run_trial_index", "trials", ["run_id", "trial_index"], unique=True)

    # Tool Calls
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trial_id", sa.String(36), sa.ForeignKey("trials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_name", sa.String(120), nullable=False),
        sa.Column("arguments", JSONB, nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=True),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("call_index_in_turn", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_fault_injected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tool_calls_trial_id", "tool_calls", ["trial_id"])
    op.create_index("ix_tool_calls_tool_name", "tool_calls", ["tool_name"])

    # Tool Results
    op.create_table(
        "tool_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tool_call_id", sa.String(36), sa.ForeignKey("tool_calls.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("is_error", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("error_type", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Fault Events
    op.create_table(
        "fault_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trial_id", sa.String(36), sa.ForeignKey("trials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_call_id", sa.String(36), nullable=True),
        sa.Column("fault_type", sa.String(80), nullable=False),
        sa.Column("target_tool", sa.String(120), nullable=False),
        sa.Column("trigger_invocation", sa.Integer(), nullable=True),
        sa.Column("behaviour_data", JSONB, nullable=False),
        sa.Column("fault_seed", sa.Integer(), nullable=False),
        sa.Column("injected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_fault_events_trial_id", "fault_events", ["trial_id"])

    # World State Snapshots
    op.create_table(
        "world_state_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trial_id", sa.String(36), sa.ForeignKey("trials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase", sa.String(40), nullable=False),
        sa.Column("state_payload", JSONB, nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_world_state_snapshots_trial_id", "world_state_snapshots", ["trial_id"])

    # Grader Results
    op.create_table(
        "grader_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trial_id", sa.String(36), sa.ForeignKey("trials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("grader_version_id", sa.String(64), nullable=False),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("grader_type", sa.String(40), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("is_critical_failure", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("findings", JSONB, nullable=False, server_default="[]"),
        sa.Column("evidence_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_grader_results_trial_id", "grader_results", ["trial_id"])

    # Security Findings
    op.create_table(
        "security_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trial_id", sa.String(36), sa.ForeignKey("trials.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owasp_category", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence", JSONB, nullable=False, server_default="{}"),
        sa.Column("remediation", sa.Text(), nullable=False, server_default=""),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_security_findings_trial_id", "security_findings", ["trial_id"])
    op.create_index("ix_security_findings_run_id", "security_findings", ["run_id"])
    op.create_index("ix_security_findings_owasp_category", "security_findings", ["owasp_category"])

    # Reports
    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("verdict", sa.String(40), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("confidence_level", sa.Float(), nullable=True),
        sa.Column("trials_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trials_passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trials_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("report_format", sa.String(20), nullable=False, server_default="json"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reports_run_id", "reports", ["run_id"])
    op.create_index("ix_reports_project_id", "reports", ["project_id"])

    # Audit Events
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("actor_id", sa.String(120), nullable=False),
        sa.Column("actor_type", sa.String(40), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=True),
        sa.Column("event_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("reports")
    op.drop_table("security_findings")
    op.drop_table("grader_results")
    op.drop_table("world_state_snapshots")
    op.drop_table("fault_events")
    op.drop_table("tool_results")
    op.drop_table("tool_calls")
    op.drop_table("trials")
    op.drop_table("evaluation_runs")
    op.drop_table("scenario_versions")
    op.drop_table("scenarios")
    op.drop_table("agent_versions")
    op.drop_table("agent_definitions")
    op.drop_table("projects")
