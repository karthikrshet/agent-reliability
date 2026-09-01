"""
Agent Reliability Lab — Security Domain Entity.

SecurityFinding records a detected security event during a trial.
Every finding maps to an OWASP GenAI LLM Top 10 (2026) category.

Security rationale: Findings are created by deterministic security graders
and cannot be overridden by model judges. They cause NOT_READY verdicts
regardless of other scores.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class OWASPCategory(str, enum.Enum):
    """OWASP GenAI LLM Top 10 (2026) categories.

    Ref: https://genai.owasp.org/
    Findings are mapped to these categories for structured reporting.
    """

    LLM01_PROMPT_INJECTION = "LLM01:PromptInjection"
    LLM02_SENSITIVE_DATA = "LLM02:SensitiveDataExposure"
    LLM03_SUPPLY_CHAIN = "LLM03:SupplyChain"
    LLM04_DATA_POISONING = "LLM04:DataAndModelPoisoning"
    LLM05_INSECURE_OUTPUT = "LLM05:InsecureOutputHandling"
    LLM06_EXCESSIVE_AGENCY = "LLM06:ExcessiveAgency"
    LLM07_SYSTEM_PROMPT_LEAKAGE = "LLM07:SystemPromptLeakage"
    LLM08_VECTOR_EMBEDDING = "LLM08:VectorAndEmbeddingWeakness"
    LLM09_MISINFORMATION = "LLM09:Misinformation"
    LLM10_UNBOUNDED_CONSUMPTION = "LLM10:UnboundedConsumption"
    # ARL-specific additions beyond standard OWASP top 10
    ARL_CROSS_TENANT_ACCESS = "ARL:CrossTenantAccess"
    ARL_IDEMPOTENCY_VIOLATION = "ARL:IdempotencyViolation"
    ARL_FABRICATED_SUCCESS = "ARL:FabricatedSuccess"
    ARL_APPROVAL_BYPASS = "ARL:ApprovalBypass"
    ARL_SSRF = "ARL:SSRF"


class FindingConfidence(str, enum.Enum):
    """Confidence level in the security finding.

    HIGH: Deterministic check — certainty.
    MEDIUM: Pattern-based — likely but not certain.
    LOW: Heuristic — needs human review.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SecurityFinding(BaseModel):
    """A recorded security finding from a trial.

    All critical findings (confidence=HIGH) trigger NOT_READY verdict.
    Medium and low confidence findings are surfaced but require human review.

    SECURITY NOTE: description and evidence fields may contain agent output
    that included prompt injection attempts. Always HTML-escape before rendering.
    """

    model_config = {"frozen": True}

    id: str = Field(..., description="Stable ULID")
    trial_id: str
    run_id: str
    grader_result_id: str | None = Field(default=None)
    owasp_category: OWASPCategory
    severity: str = Field(..., pattern=r"^(critical|high|medium|low|info)$")
    confidence: FindingConfidence
    title: str = Field(..., min_length=1, max_length=200)
    # SECURITY: may contain untrusted content — HTML-escape before rendering
    description: str = Field(
        ...,
        max_length=5000,
        description=(
            "Human-readable finding description. "
            "SECURITY: may contain agent output — HTML-escape before rendering."
        ),
    )
    # Structured evidence — structured, schema-validated data
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured evidence. Values are safe scalars, not raw agent output.",
    )
    # What tool call or agent turn triggered this finding
    source_tool_call_id: str | None = Field(default=None)
    source_agent_turn_id: str | None = Field(default=None)
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # Remediation guidance (for reports)
    remediation: str = Field(default="", max_length=2000)
    is_false_positive: bool = Field(
        default=False,
        description="Set only through an explicit human review process",
    )
    reviewed_by: str | None = Field(default=None)
    reviewed_at: datetime | None = Field(default=None)
