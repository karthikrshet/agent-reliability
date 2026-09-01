"""
Agent Reliability Lab — Immutable Cryptographic Evidence Collector.

Records immutable evidence items linked to concrete execution entities (tool calls,
state snapshots, fault events, transcripts) and maintains a tamper-evident SHA-256
hash chain for non-repudiation and audits.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from arl.core.domain.grading import Evidence
from arl.execution_engine.executor import TrialExecutionResult


class EvidenceLedgerBlock(BaseModel):
    """A single link in the cryptographic evidence hash chain."""

    index: int
    evidence_id: str
    trial_id: str
    run_id: str
    payload_sha256: str
    prev_chain_hash: str
    chain_hash: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EvidenceCollector:
    """Collects, indexes, and cryptographically chains evidence across trials and runs."""

    def __init__(self, genesis_salt: str = "arl-evidence-genesis-v1") -> None:
        self.evidence_records: dict[str, Evidence] = {}
        self.chain_blocks: list[EvidenceLedgerBlock] = []
        self._current_chain_hash: str = hashlib.sha256(genesis_salt.encode("utf-8")).hexdigest()

    @property
    def current_hash(self) -> str:
        """The latest SHA-256 hash of the evidence ledger chain."""
        return self._current_chain_hash

    def collect_from_trial_result(
        self,
        trial_id: str,
        run_id: str,
        result: TrialExecutionResult,
    ) -> list[Evidence]:
        """Extract and ledger all primary evidence artifacts from a trial execution."""
        collected: list[Evidence] = []

        # 1. Pre-trial snapshot evidence
        if result.pre_snapshot:
            ev_pre = self.record_evidence(
                trial_id=trial_id,
                run_id=run_id,
                evidence_type="world_state_snapshot",
                source_entity_type="WorldStateSnapshot",
                source_entity_id=result.pre_snapshot.id,
                description="Pre-trial initial world state snapshot",
                data=result.pre_snapshot.state,
            )
            collected.append(ev_pre)

        # 2. Post-trial snapshot evidence
        if result.post_snapshot:
            ev_post = self.record_evidence(
                trial_id=trial_id,
                run_id=run_id,
                evidence_type="world_state_snapshot",
                source_entity_type="WorldStateSnapshot",
                source_entity_id=result.post_snapshot.id,
                description="Post-trial final world state snapshot",
                data=result.post_snapshot.state,
            )
            collected.append(ev_post)

        # 3. Tool call execution evidence
        for tc in result.tool_calls:
            # Match with result if available
            matched_res = next((r for r in result.tool_results if r.tool_call_id == tc.id), None)
            res_content = matched_res.content if matched_res else None

            ev_tc = self.record_evidence(
                trial_id=trial_id,
                run_id=run_id,
                evidence_type="tool_call",
                source_entity_type="ToolCall",
                source_entity_id=tc.id,
                description=f"Execution of tool '{tc.tool_name}'",
                data={
                    "tool_name": tc.tool_name,
                    "arguments": tc.call_arguments,
                    "result": res_content,
                    "is_error": matched_res.is_error if matched_res else False,
                },
            )
            collected.append(ev_tc)

        # 4. Fault injection events
        for fe in result.fault_events:
            ev_fe = self.record_evidence(
                trial_id=trial_id,
                run_id=run_id,
                evidence_type="fault_event",
                source_entity_type="FaultEvent",
                source_entity_id=fe.id,
                description=f"Fault injection '{fe.fault_type.value}' intercepted tool '{fe.target_tool}'",
                data={
                    "fault_type": fe.fault_type.value,
                    "target_tool": fe.target_tool,
                    "behaviour": fe.behaviour.model_dump(),
                    "seed": fe.fault_seed,
                },
            )
            collected.append(ev_fe)

        return collected

    def record_evidence(
        self,
        trial_id: str,
        run_id: str,
        evidence_type: str,
        source_entity_type: str,
        source_entity_id: str,
        description: str,
        data: dict[str, Any],
        grader_result_id: str | None = None,
    ) -> Evidence:
        """Create an evidence record and append it to the cryptographic ledger chain."""
        ev_id = f"ev-{uuid.uuid4().hex[:12]}"
        evidence = Evidence(
            id=ev_id,
            trial_id=trial_id,
            run_id=run_id,
            grader_result_id=grader_result_id,
            evidence_type=evidence_type,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            description=description,
            data=data,
            created_at=datetime.now(UTC),
        )

        self.evidence_records[ev_id] = evidence

        # Compute payload hash using canonical deterministic JSON
        payload_bytes = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        payload_sha = hashlib.sha256(payload_bytes).hexdigest()

        # Update chain hash: H(prev_chain_hash || payload_sha || evidence_id)
        hasher = hashlib.sha256()
        hasher.update(self._current_chain_hash.encode("utf-8"))
        hasher.update(payload_sha.encode("utf-8"))
        hasher.update(ev_id.encode("utf-8"))
        new_chain_hash = hasher.hexdigest()

        block = EvidenceLedgerBlock(
            index=len(self.chain_blocks),
            evidence_id=ev_id,
            trial_id=trial_id,
            run_id=run_id,
            payload_sha256=payload_sha,
            prev_chain_hash=self._current_chain_hash,
            chain_hash=new_chain_hash,
            timestamp=evidence.created_at,
        )

        self.chain_blocks.append(block)
        self._current_chain_hash = new_chain_hash

        return evidence

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        """Lookup an evidence record by ID."""
        return self.evidence_records.get(evidence_id)

    def get_trial_evidence(self, trial_id: str) -> list[Evidence]:
        """Retrieve all evidence items for a given trial."""
        return [e for e in self.evidence_records.values() if e.trial_id == trial_id]

    def verify_ledger_integrity(self, genesis_salt: str = "arl-evidence-genesis-v1") -> bool:
        """Verify the cryptographic hash chain of the entire evidence ledger.

        Returns True if all block hashes match and have not been tampered with.
        """
        expected_prev = hashlib.sha256(genesis_salt.encode("utf-8")).hexdigest()

        for block in self.chain_blocks:
            if block.prev_chain_hash != expected_prev:
                return False

            evidence = self.evidence_records.get(block.evidence_id)
            if evidence is None:
                return False

            payload_bytes = json.dumps(evidence.data, sort_keys=True, default=str).encode("utf-8")
            expected_payload_sha = hashlib.sha256(payload_bytes).hexdigest()

            if block.payload_sha256 != expected_payload_sha:
                return False

            hasher = hashlib.sha256()
            hasher.update(block.prev_chain_hash.encode("utf-8"))
            hasher.update(block.payload_sha256.encode("utf-8"))
            hasher.update(block.evidence_id.encode("utf-8"))
            expected_chain = hasher.hexdigest()

            if block.chain_hash != expected_chain:
                return False

            expected_prev = block.chain_hash

        return True
