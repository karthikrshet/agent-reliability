"""
Agent Reliability Lab — Trial Execution Engine.

Orchestrates multi-turn conversation between an AgentAdapter and a
sandboxed testing environment with deterministic fault injection,
pre/post trial world state snapshots, and hard budget enforcement.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from arl.core.domain.agent import AgentTurn
from arl.core.domain.faults import FaultEvent
from arl.core.domain.tools import ToolCall, ToolResult
from arl.core.domain.trial import Trial, WorldStateSnapshot
from arl.core.errors import BudgetExceededError
from arl.execution_engine.proxy import ToolProxy
from arl.fault_engine.scheduler import FaultScheduler
from arl.protocol.adapter import (
    AgentAdapter,
    AgentInput,
    AgentOutputType,
    SessionContext,
)
from arl.scenario_engine.schema import ParsedScenario

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TrialExecutionResult:
    """Immutable execution records collected during a trial run."""

    trial_id: str
    turns: list[AgentTurn] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    fault_events: list[FaultEvent] = field(default_factory=list)
    pre_snapshot: WorldStateSnapshot | None = None
    post_snapshot: WorldStateSnapshot | None = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    duration_seconds: float = 0.0
    completed_normally: bool = True
    termination_reason: str = "completed"
    final_response: str = ""


class TrialExecutor:
    """Executes a single trial against an agent adapter and environment."""

    def __init__(
        self,
        trial: Trial,
        scenario: ParsedScenario,
        adapter: AgentAdapter,
        environment: Any,
    ) -> None:
        self.trial = trial
        self.scenario = scenario
        self.adapter = adapter
        self.environment = environment

    async def run(self) -> TrialExecutionResult:
        """Execute the trial to completion or budget exhaustion."""
        start_time = time.perf_counter()
        logger.info("Starting execution of trial %s (seed=%d)", self.trial.id, self.trial.fault_seed)

        # 1. Reset environment with deterministic seed and scenario overrides
        if hasattr(self.environment, "reset"):
            self.environment.reset(
                seed=self.scenario.environment.seed,
                initial_state=self.scenario.initial_state,
            )

        # 2. Capture pre-trial world state snapshot
        pre_snapshot_data = self.environment.export_world_state() if hasattr(self.environment, "export_world_state") else {}
        pre_snapshot = WorldStateSnapshot(
            id=f"snap-pre-{self.trial.id}",
            trial_id=self.trial.id,
            environment_version_id=self.scenario.environment.version,
            snapshot_type="initial",
            state=pre_snapshot_data,
            schema_version=self.scenario.schema_version,
            is_schema_valid=True,
            captured_at=datetime.now(UTC),
        )

        # 3. Setup fault scheduler and tool proxy
        fault_scheduler = FaultScheduler(
            fault_plan_entries=self.scenario.fault_plan,
            trial_fault_seed=self.trial.fault_seed,
            trial_id=self.trial.id,
        )

        available_tools = self.environment.tools if hasattr(self.environment, "tools") else []
        proxy = ToolProxy(
            environment=self.environment,
            tool_definitions=available_tools,
            fault_scheduler=fault_scheduler,
        )

        # 4. Initialize session context
        session_context = SessionContext(
            session_id=f"sess-{self.trial.id}",
            trial_id=self.trial.id,
            run_id=self.trial.run_id,
            agent_version_id=getattr(self.trial, "agent_version_id", "agent-v1"),
            available_tools=available_tools,
            initial_messages=[{"role": m.role, "content": m.content} for m in self.scenario.conversation],
            max_turns=self.scenario.budgets.max_turns,
            max_tool_calls=self.scenario.budgets.max_tool_calls,
            max_duration_seconds=self.scenario.budgets.max_duration_seconds,
            correlation_id=self.trial.id,
        )

        session = await self.adapter.start_session(session_context)

        turns: list[AgentTurn] = []
        recorded_tool_calls: list[ToolCall] = []
        recorded_tool_results: list[ToolResult] = []
        total_tokens = 0
        total_cost_usd = 0.0
        final_response_text = ""
        termination_reason = "completed"
        completed_normally = True

        current_tool_results: list[dict[str, Any]] = []

        try:
            for turn_idx in range(self.scenario.budgets.max_turns):
                elapsed_seconds = time.perf_counter() - start_time

                # Budget check: duration
                if elapsed_seconds >= self.scenario.budgets.max_duration_seconds:
                    termination_reason = "duration_budget_exceeded"
                    completed_normally = False
                    break

                # Budget check: tool call count
                if len(recorded_tool_calls) >= self.scenario.budgets.max_tool_calls:
                    termination_reason = "tool_calls_budget_exceeded"
                    completed_normally = False
                    break

                # Construct agent input for current turn
                agent_input = AgentInput(
                    turn_index=turn_idx,
                    tool_results=current_tool_results,
                    user_messages=[] if turn_idx > 0 else [{"role": m.role, "content": m.content} for m in self.scenario.conversation],
                )

                turn_start_time = datetime.now(UTC)
                turn_start = time.perf_counter()
                output = await self.adapter.send(session, agent_input)
                turn_latency_ms = int((time.perf_counter() - turn_start) * 1000)

                # Accumulate tokens and costs
                p_tokens = output.prompt_tokens or 0
                c_tokens = output.completion_tokens or 0
                t_tokens = output.total_tokens or (p_tokens + c_tokens)
                cost = output.cost_usd or 0.0

                total_tokens += t_tokens
                total_cost_usd += cost

                # Budget check: cost limit
                if self.scenario.budgets.max_cost_usd is not None and total_cost_usd > self.scenario.budgets.max_cost_usd:
                    termination_reason = "cost_budget_exceeded"
                    completed_normally = False
                    break

                # Record turn
                agent_turn = AgentTurn(
                    id=f"turn-{self.trial.id}-{turn_idx}",
                    trial_id=self.trial.id,
                    turn_index=turn_idx,
                    agent_version_id=getattr(self.trial, "agent_version_id", "agent-v1"),
                    raw_response=output.raw_text,
                    finish_reason=output.output_type.value,
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=t_tokens,
                    cost_usd=cost,
                    latency_ms=turn_latency_ms,
                    started_at=turn_start_time,
                    ended_at=datetime.now(UTC),
                )
                turns.append(agent_turn)

                if output.raw_text:
                    final_response_text = output.raw_text

                # Handle output types
                if output.output_type == AgentOutputType.TOOL_CALLS:
                    current_tool_results = []
                    for call_idx, call_rec in enumerate(output.tool_calls):
                        call_id = f"tc-{self.trial.id}-{turn_idx}-{call_idx}"
                        tool_call = ToolCall(
                            id=call_id,
                            trial_id=self.trial.id,
                            agent_turn_id=agent_turn.id,
                            sequence_index=len(recorded_tool_calls),
                            tool_name=call_rec.tool_name,
                            call_arguments=call_rec.arguments,
                        )
                        recorded_tool_calls.append(tool_call)

                        # Execute tool through proxy with fault interception
                        current_elapsed = time.perf_counter() - start_time
                        tool_res, _fault_event = await proxy.execute(
                            tool_call_id=call_id,
                            tool_name=call_rec.tool_name,
                            arguments=call_rec.arguments,
                            trial_id=self.trial.id,
                            elapsed_seconds=current_elapsed,
                        )
                        recorded_tool_results.append(tool_res)

                        current_tool_results.append({
                            "tool_call_id": call_rec.tool_call_id,
                            "output": tool_res.content,
                        })

                elif output.output_type in (AgentOutputType.FINISHED, AgentOutputType.TEXT):
                    # Agent completed turn or conversation
                    if not output.tool_calls:
                        break
                elif output.output_type == AgentOutputType.ERROR:
                    termination_reason = f"agent_error: {output.error_message}"
                    completed_normally = False
                    break

            else:
                # Loop ended without break -> turn budget exceeded
                termination_reason = "turns_budget_exceeded"
                completed_normally = False

        except BudgetExceededError as exc:
            termination_reason = f"budget_exceeded: {exc}"
            completed_normally = False
        except Exception as exc:
            logger.exception("Error executing trial %s", self.trial.id)
            termination_reason = f"unexpected_error: {exc}"
            completed_normally = False
        finally:
            await self.adapter.close_session(session)

        # 5. Capture post-trial world state snapshot
        post_snapshot_data = self.environment.export_world_state() if hasattr(self.environment, "export_world_state") else {}
        post_snapshot = WorldStateSnapshot(
            id=f"snap-post-{self.trial.id}",
            trial_id=self.trial.id,
            environment_version_id=self.scenario.environment.version,
            snapshot_type="final",
            state=post_snapshot_data,
            schema_version=self.scenario.schema_version,
            is_schema_valid=True,
            captured_at=datetime.now(UTC),
        )

        total_duration = time.perf_counter() - start_time

        return TrialExecutionResult(
            trial_id=self.trial.id,
            turns=turns,
            tool_calls=recorded_tool_calls,
            tool_results=recorded_tool_results,
            fault_events=proxy.recorded_fault_events,
            pre_snapshot=pre_snapshot,
            post_snapshot=post_snapshot,
            total_tokens=total_tokens,
            total_cost_usd=total_cost_usd,
            duration_seconds=total_duration,
            completed_normally=completed_normally,
            termination_reason=termination_reason,
            final_response=final_response_text,
        )
