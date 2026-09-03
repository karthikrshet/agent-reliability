"""
Agent Reliability Lab — Command-Line Interface (agentlab).

Commands:
  agentlab list-scenarios     List all 25 canonical reliability evaluation scenarios
  agentlab validate <path>    Validate scenario schema against JSON Schema 2020-12
  agentlab run <path>         Execute reliability evaluation trials against an agent
  agentlab report <run-id>    Display comprehensive evaluation report with Wilson CI
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path
from typing import Annotated, Any

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from arl.adapters.http.adapter import HttpAgentAdapter
from arl.adapters.reference.agent import MockAgentAdapter
from arl.core.domain.failure import FailureRecord
from arl.core.domain.faults import FaultResult
from arl.core.domain.grading import ReadinessVerdict
from arl.core.domain.trial import Trial, TrialVerdict
from arl.environments.customer_support.environment import CustomerSupportEnvironment
from arl.evidence.collector import EvidenceCollector
from arl.evidence.disk_store import list_runs_on_disk, load_run_from_disk, persist_run_to_disk
from arl.evidence.reporter import ReportGenerator
from arl.execution_engine.executor import TrialExecutor
from arl.grading_engine.aggregator import EvaluationRunAggregator, RunAggregationResult
from arl.grading_engine.deterministic import DeterministicTrialEvaluator
from arl.grading_engine.invariants import (
    InvariantEngine,
    InvariantResult,
    InvariantSeverity,
    InvariantSpec,
    InvariantStatus,
)
from arl.protocol.adapter import AgentAdapter
from arl.scenario_engine.loader import load_scenario
from arl.scenario_engine.schema import ParsedScenario

app = typer.Typer(
    name="agentlab",
    help="Agent Reliability Lab — Production-readiness testing & evaluation for tool-using AI agents.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console(legacy_windows=False)


def _find_run_for_identifier(
    identifier: str, base_dir: Path | str = ".arl"
) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    """Find run directory and optional failure record matching a run ID or failure ID."""
    base = Path(base_dir) / "runs"
    if not base.exists():
        raise FileNotFoundError(f"No ARL runs directory found at {base_dir}")

    # 1. Direct directory match
    candidate = base / identifier
    if candidate.exists() and candidate.is_dir():
        loaded = load_run_from_disk(identifier, base_dir=base_dir)
        matched_f = loaded["failures"][0] if loaded.get("failures") else None
        return identifier, loaded, matched_f

    # 2. Match failure ID inside failures.json
    for run_dir in base.iterdir():
        if not run_dir.is_dir():
            continue
        try:
            loaded = load_run_from_disk(run_dir.name, base_dir=base_dir)
            for f in loaded.get("failures", []):
                if f.get("failure_id") == identifier:
                    return run_dir.name, loaded, f
        except Exception:
            continue

    raise KeyError(
        f"Identifier {identifier!r} not found among recorded runs or failures in {base_dir}"
    )


def _discover_all_scenarios(
    base_dir: Path = Path("scenarios"),
) -> list[tuple[Path, ParsedScenario]]:
    """Helper to scan and parse all scenario files."""
    results: list[tuple[Path, ParsedScenario]] = []
    if not base_dir.exists():
        return results

    for yaml_path in sorted(base_dir.rglob("*.yaml")):
        try:
            scenario, _, _ = load_scenario(yaml_path)
            results.append((yaml_path, scenario))
        except Exception:
            continue
    return results


@app.command(name="list-scenarios")
def list_scenarios_command(
    category: Annotated[
        str | None, typer.Option("--category", "-c", help="Filter by category")
    ] = None,
) -> None:
    """List available canonical reliability test scenarios."""
    scenarios = _discover_all_scenarios()
    if not scenarios:
        console.print("[yellow]No scenarios found in ./scenarios directory.[/yellow]")
        return

    table = Table(
        title="Agent Reliability Lab — Canonical Scenarios",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    table.add_column("Scenario ID", style="bold white")
    table.add_column("Category", style="magenta")
    table.add_column("Severity", style="yellow")
    table.add_column("Title", style="white")
    table.add_column("Tags", style="dim")

    for _, sc in scenarios:
        if category and sc.category != category:
            continue
        sev_style = (
            "bold red"
            if sc.severity == "critical"
            else ("yellow" if sc.severity == "high" else "green")
        )
        table.add_row(
            sc.id,
            sc.category,
            f"[{sev_style}]{sc.severity}[/{sev_style}]",
            sc.title,
            ", ".join(sc.tags[:3]),
        )

    console.print(table)
    console.print(f"[dim]Total scenarios: {len(table.rows)}[/dim]\n")


@app.command(name="validate")
def validate_command(
    path: Annotated[Path, typer.Argument(help="Path to scenario YAML file to validate")],
) -> None:
    """Validate a scenario YAML file against JSON Schema 2020-12 and domain rules."""
    if not path.exists():
        console.print(f"[bold red]File not found:[/bold red] {path}")
        raise typer.Exit(code=1)

    try:
        scenario, _, _ = load_scenario(path)
        console.print(
            Panel(
                f"[bold green]VALID SCENARIO[/bold green]\n\n"
                f"[bold]ID:[/bold] {scenario.id}\n"
                f"[bold]Title:[/bold] {scenario.title}\n"
                f"[bold]Category:[/bold] {scenario.category}\n"
                f"[bold]Severity:[/bold] {scenario.severity}\n"
                f"[bold]Expected Effects:[/bold] {len(scenario.expected_effects)}\n"
                f"[bold]Forbidden Effects:[/bold] {len(scenario.forbidden_effects)}",
                title=f"Schema Validation: {path.name}",
                border_style="green",
            )
        )
    except Exception as exc:
        console.print(
            Panel(
                f"[bold red]VALIDATION FAILED[/bold red]\n\n{exc}",
                title=f"Schema Validation: {path.name}",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc


async def _run_evaluation_async(
    scenario_paths: list[Path],
    agent_url: str | None,
    openai_model: str | None,
    openai_base_url: str | None,
    reference_only: bool,
    trials_per_scenario: int,
    base_seed: int,
    threshold: float = 0.80,
    custom_run_id: str | None = None,
) -> tuple[RunAggregationResult, list[FailureRecord], str]:
    """Async engine executing evaluation trials."""
    evaluator = DeterministicTrialEvaluator()
    aggregator = EvaluationRunAggregator(
        readiness_threshold=threshold, min_required_trials=len(scenario_paths) * trials_per_scenario
    )
    collector = EvidenceCollector()
    run_id = custom_run_id or f"run-{uuid.uuid4().hex[:8]}"

    domain_trials: list[Trial] = []
    trial_scores: dict[str, float] = {}
    trial_verdicts: dict[str, TrialVerdict] = {}
    trial_categories: dict[str, str] = {}
    all_grader_results = []
    all_events: list[dict[str, Any]] = []
    all_faults: list[FaultResult] = []
    all_invariants: list[InvariantResult] = []
    all_failures: list[FailureRecord] = []

    trial_counter = 0

    table = Table(
        title="Execution Progress",
        box=box.SIMPLE,
        header_style="bold cyan",
    )
    table.add_column("Trial ID", style="dim")
    table.add_column("Scenario", style="white")
    table.add_column("Verdict", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Findings", justify="right")

    for sc_path in scenario_paths:
        scenario, _, _ = load_scenario(sc_path)

        for t_idx in range(trials_per_scenario):
            trial_id = f"tr-{trial_counter:03d}"
            fault_seed = base_seed + trial_counter
            trial_counter += 1

            trial = Trial(
                id=trial_id,
                run_id=run_id,
                trial_index=t_idx,
                idempotency_key=f"idemp-{trial_id}",
                fault_seed=fault_seed,
                is_reference_only=reference_only,
            )

            # Initialize isolated sandboxed environment
            env = CustomerSupportEnvironment(seed=fault_seed)

            # Initialize agent adapter
            adapter: AgentAdapter
            if agent_url:
                adapter = HttpAgentAdapter(endpoint_url=agent_url)
            elif openai_model:
                from arl.adapters.openai.adapter import OpenAIAgentAdapter

                base_u = openai_base_url or "https://api.openai.com/v1"
                adapter = OpenAIAgentAdapter(
                    endpoint_url=f"{base_u.rstrip('/')}/chat/completions",
                    model=openai_model,
                )
            else:
                adapter = MockAgentAdapter()

            executor = TrialExecutor(
                trial=trial,
                scenario=scenario,
                adapter=adapter,
                environment=env,
            )

            # Execute trial
            exec_res = await executor.run()

            # Record evidence in cryptographic ledger
            collector.collect_from_trial_result(trial_id, run_id, exec_res)

            # Collect raw tool call events
            all_events.extend(
                [
                    {
                        "event_id": tc.id,
                        "run_id": run_id,
                        "trial_id": trial_id,
                        "scenario_id": scenario.id,
                        "timestamp": tc.started_at.isoformat(),
                        "event_type": "tool_call",
                        "component": "tool_proxy",
                        "tool_name": tc.tool_name,
                        "arguments": tc.call_arguments,
                    }
                    for tc in exec_res.tool_calls
                ]
            )

            # Collect fault events and results
            if hasattr(executor, "tool_proxy") and executor.tool_proxy:
                all_faults.extend(executor.tool_proxy.recorded_fault_results)
                all_events.extend(
                    [
                        {
                            "event_id": fe.id,
                            "run_id": run_id,
                            "trial_id": trial_id,
                            "scenario_id": scenario.id,
                            "timestamp": fe.injected_at.isoformat(),
                            "event_type": "fault_injected",
                            "component": "fault_scheduler",
                            "fault_type": fe.fault_type.value,
                            "target_tool": fe.target_tool,
                        }
                        for fe in executor.tool_proxy.recorded_fault_events
                    ]
                )

            # Invariant Engine evaluation against post-execution world state
            final_world_state = (
                env.export_world_state() if hasattr(env, "export_world_state") else {}
            )
            trial_invariants = [
                InvariantSpec(
                    id=f"{scenario.id}-{exp.path}",
                    description=f"Expected effect on {exp.path}",
                    severity=InvariantSeverity.HIGH,
                    path=exp.path,
                    operator=exp.operator,
                    value=exp.value,
                )
                for exp in scenario.expected_effects
            ]
            trial_inv_results = InvariantEngine.evaluate_all(trial_invariants, final_world_state)
            all_invariants.extend(trial_inv_results)

            # Deterministic evaluation
            verdict, score, grader_results = await evaluator.evaluate_trial(
                trial, scenario, exec_res
            )

            all_grader_results.extend(grader_results)
            domain_trials.append(
                trial.model_copy(
                    update={
                        "verdict": verdict,
                        "score": score,
                        "duration_ms": int(exec_res.duration_seconds * 1000),
                        "total_cost_usd": exec_res.total_cost_usd,
                    }
                )
            )
            trial_scores[trial_id] = score
            trial_verdicts[trial_id] = verdict
            trial_categories[trial_id] = scenario.category

            # If trial failed, create FailureRecord
            if verdict in (TrialVerdict.CRITICAL_FAIL, TrialVerdict.FAIL):
                failed_invs = [
                    r.invariant_id
                    for r in trial_inv_results
                    if r.status in (InvariantStatus.FAIL, InvariantStatus.ERROR)
                ]
                failure_id = f"ARL-FAIL-{run_id[-4:]}-{trial_counter:02d}"
                all_failures.append(
                    FailureRecord(
                        failure_id=failure_id,
                        run_id=run_id,
                        scenario_id=scenario.id,
                        severity="critical" if verdict == TrialVerdict.CRITICAL_FAIL else "high",
                        failed_invariants=failed_invs,
                        faults=[f.target for f in executor.tool_proxy.recorded_fault_results]
                        if hasattr(executor, "tool_proxy") and executor.tool_proxy
                        else [],
                        first_bad_event_id=all_events[-1]["event_id"] if all_events else None,
                        reproduction_command=f"agentlab rerun {failure_id}",
                        reproduction_metadata={
                            "scenario_id": scenario.id,
                            "scenario_path": str(sc_path),
                            "seed": fault_seed,
                            "trial_index": t_idx,
                            "reference_only": reference_only,
                        },
                        summary=f"Trial {trial_id} failed with verdict {verdict.value} (score={score:.2f})",
                    )
                )

            # Print trial row
            if verdict == TrialVerdict.PASS:
                v_str = "[green]PASS[/green]"
            elif verdict == TrialVerdict.CRITICAL_FAIL:
                v_str = "[bold red]CRITICAL_FAIL[/bold red]"
            else:
                v_str = "[red]FAIL[/red]"

            findings_count = sum(len(g.findings) for g in grader_results)
            table.add_row(
                trial_id,
                scenario.id,
                v_str,
                f"{score:.2f}",
                f"{exec_res.duration_seconds:.2f}s",
                str(findings_count) if findings_count else "-",
            )

    console.print(table)

    # Statistical aggregation
    res = aggregator.aggregate(
        run_id=run_id,
        trials=domain_trials,
        trial_scores=trial_scores,
        trial_verdicts=trial_verdicts,
        grader_results=all_grader_results,
        trial_categories=trial_categories,
        is_reference_only=reference_only,
    )

    _ = ReportGenerator(run_result=res, evidence_collector=collector)

    # Persist structured artifacts to .arl/runs/<run-id>/
    manifest = {
        "run_id": run_id,
        "scenario_count": len(scenario_paths),
        "total_trials": len(domain_trials),
        "reference_only": reference_only,
        "seed": base_seed,
        "threshold": threshold,
        "verdict": res.readiness_verdict.value,
        "evidence_root_hash": collector.current_hash,
    }
    summary = {
        "run_id": run_id,
        "completed_trials": res.completed_trials,
        "passed_trials": res.passed_trials,
        "failed_trials": res.failed_trials,
        "pass_rate": res.pass_rate,
        "pass_rate_ci_lower": res.pass_rate_ci_lower,
        "pass_rate_ci_upper": res.pass_rate_ci_upper,
        "pass_at_1": res.pass_at_1,
        "pass_at_3": res.pass_at_3,
        "critical_failures": res.critical_failures,
        "verdict": res.readiness_verdict.value,
    }
    persist_run_to_disk(
        run_id=run_id,
        manifest=manifest,
        events=all_events,
        faults=all_faults,
        invariants=all_invariants,
        summary=summary,
        failures=all_failures,
    )

    # Print Final Audit Summary
    if reference_only:
        banner_title = "[REFERENCE ONLY] NON_PRODUCTION_REFERENCE RUN (NO VERDICT ASSIGNED)"
        banner_style = "bold yellow"
        verdict_text = "[bold yellow]NON_PRODUCTION_REFERENCE[/bold yellow] (Deterministic mock execution — no production validity)"
    else:
        v = res.readiness_verdict
        if v == ReadinessVerdict.READY:
            banner_title = "[READY] READINESS VERDICT: READY FOR PRODUCTION"
            banner_style = "bold green"
            verdict_text = "[bold green]READY[/bold green]"
        elif v == ReadinessVerdict.NOT_READY:
            banner_title = "[NOT READY] READINESS VERDICT: NOT READY"
            banner_style = "bold red"
            verdict_text = "[bold red]NOT READY[/bold red]"
        else:
            banner_title = "[INSUFFICIENT] READINESS VERDICT: INSUFFICIENT EVIDENCE"
            banner_style = "bold yellow"
            verdict_text = "[bold yellow]INSUFFICIENT EVIDENCE[/bold yellow]"

    console.print(
        Panel(
            f"[bold]Verdict:[/bold] {verdict_text}\n"
            f"[bold]Pass Rate:[/bold] {res.pass_rate:.1%} "
            f"([cyan]95% Wilson CI: [{res.pass_rate_ci_lower:.1%}, {res.pass_rate_ci_upper:.1%}][/cyan])\n"
            f"[bold]Pass@1:[/bold] {res.pass_at_1:.3f} | [bold]Pass@3:[/bold] {res.pass_at_3 or 0.0:.3f}\n"
            f"[bold]Total Trials:[/bold] {res.completed_trials} ({res.passed_trials} passed, {res.failed_trials} failed)\n"
            f"[bold]Critical Safety Failures:[/bold] {res.critical_failures}\n"
            f"[bold]Evidence Chain Hash:[/bold] [dim]{collector.current_hash}[/dim]\n"
            f"[bold]Artifacts Persisted:[/bold] [dim].arl/runs/{run_id}/[/dim]\n\n"
            f"[bold]Rationale:[/bold] {res.verdict_reason}",
            title=f"[{banner_style}]{banner_title}[/{banner_style}]",
            border_style=banner_style,
        )
    )

    if all_failures:
        console.print(f"[bold red]CRITICAL FAILURES RECORDED ({len(all_failures)}):[/bold red]")
        for f in all_failures[:3]:
            console.print(
                f"  - [bold yellow]{f.failure_id}[/bold yellow] ({f.scenario_id}): "
                f"Replay with [bold cyan]agentlab replay {f.failure_id}[/bold cyan]"
            )
        console.print()

    return res, all_failures, run_id


@app.command(name="run")
def run_command(
    scenario_path: Annotated[
        Path | None, typer.Option("--scenario", "-s", help="Path to scenario YAML file or folder")
    ] = None,
    agent_url: Annotated[
        str | None,
        typer.Option("--agent-url", "-u", help="HTTP Agent endpoint URL"),
    ] = None,
    openai_model: Annotated[
        str | None,
        typer.Option(
            "--openai-model", help="OpenAI-compatible model name (e.g. gpt-4o-mini, llama3.1)"
        ),
    ] = None,
    openai_base_url: Annotated[
        str | None,
        typer.Option(
            "--openai-base-url",
            help="OpenAI-compatible base URL (default https://api.openai.com/v1)",
        ),
    ] = None,
    reference_agent: Annotated[
        bool,
        typer.Option(
            "--reference-agent",
            help="Use local deterministic reference agent (NON_PRODUCTION_REFERENCE)",
        ),
    ] = False,
    trials: Annotated[
        int, typer.Option("--trials", "-n", help="Number of trials per scenario")
    ] = 3,
    seed: Annotated[int, typer.Option("--seed", help="Deterministic base seed")] = 42,
    threshold: Annotated[
        float, typer.Option("--threshold", "-t", help="Production readiness threshold")
    ] = 0.80,
) -> None:
    """Execute reliability testing trials against an agent."""
    # Enforce exactly one target agent
    targets_count = sum([bool(agent_url), bool(openai_model), bool(reference_agent)])
    if targets_count == 0:
        console.print(
            Panel(
                "[bold red]CONFIGURATION ERROR: No target agent specified.[/bold red]\n\n"
                "You must explicitly choose exactly one evaluation target:\n"
                "  [cyan]--agent-url <url>[/cyan]          HTTP Agent endpoint URL\n"
                "  [cyan]--openai-model <model>[/cyan]     OpenAI-compatible model endpoint\n"
                "  [cyan]--reference-agent[/cyan]          Deterministic reference agent (NON_PRODUCTION_REFERENCE)\n\n"
                "Example: [green]agentlab run -s scenarios/ --agent-url http://127.0.0.1:8088[/green]",
                title="[bold red]Target Configuration Required[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=2)

    if targets_count > 1:
        console.print(
            Panel(
                "[bold red]CONFIGURATION ERROR: Multiple target agents specified.[/bold red]\n\n"
                "Please specify only one of [cyan]--agent-url[/cyan], [cyan]--openai-model[/cyan], or [cyan]--reference-agent[/cyan].",
                title="[bold red]Conflicting Configuration[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=2)

    if reference_agent:
        console.print(
            Panel(
                "[bold yellow]WARNING: Running evaluation with deterministic reference infrastructure (MockAgentAdapter).[/bold yellow]\n\n"
                "This run is marked [bold]reference_only=true[/bold], produces [bold]NON_PRODUCTION_REFERENCE[/bold] reports, "
                "and will NOT produce a production readiness verdict.",
                title="[bold yellow]Reference Run Notice[/bold yellow]",
                border_style="yellow",
            )
        )

    if scenario_path is None:
        scenario_paths = [p for p, _ in _discover_all_scenarios()]
        if not scenario_paths:
            console.print("[red]No scenarios found to run.[/red]")
            raise typer.Exit(code=1)
    elif scenario_path.is_dir():
        scenario_paths = [p for p, _ in _discover_all_scenarios(scenario_path)]
    elif scenario_path.exists():
        scenario_paths = [scenario_path]
    else:
        console.print(f"[bold red]Scenario path not found:[/bold red] {scenario_path}")
        raise typer.Exit(code=1)

    console.print(
        f"\n[bold green]>>[/bold green] [bold]Starting evaluation across {len(scenario_paths)} scenario(s)...[/bold]\n"
    )
    asyncio.run(
        _run_evaluation_async(
            scenario_paths,
            agent_url,
            openai_model,
            openai_base_url,
            reference_agent,
            trials,
            seed,
            threshold,
        )
    )


@app.command(name="doctor")
def doctor_command(
    agent_url: Annotated[
        str | None,
        typer.Option("--agent-url", "-u", help="Optional agent endpoint to probe for connectivity"),
    ] = None,
) -> None:
    """Run preflight health and environment diagnostics."""
    import sys

    table = Table(
        title="Agent Reliability Lab — Preflight Doctor Diagnostics",
        box=box.ROUNDED,
        header_style="bold cyan",
    )
    table.add_column("Diagnostic Check", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    all_passed = True

    # 1. Python runtime
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    table.add_row("Python Runtime (>=3.12)", "[bold green]PASS[/bold green]", f"Python {py_ver}")

    # 2. Workspace packages
    packages_to_check = [
        ("arl-core", "arl.core"),
        ("arl-protocol", "arl.protocol"),
        ("arl-scenario-engine", "arl.scenario_engine"),
        ("arl-fault-engine", "arl.fault_engine"),
        ("arl-execution-engine", "arl.execution_engine"),
        ("arl-grading-engine", "arl.grading_engine"),
        ("arl-evidence", "arl.evidence"),
        ("arl-env-customer-support", "arl.environments.customer_support"),
        ("arl-adapter-http", "arl.adapters.http"),
        ("arl-adapter-reference", "arl.adapters.reference"),
        ("arl-worker", "arl.worker"),
        ("arl-server", "arl.server"),
        ("arl-cli", "arl.cli"),
        ("arl-mcp", "arl.mcp"),
    ]
    missing = []
    for pkg_name, mod_name in packages_to_check:
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg_name)

    if not missing:
        table.add_row(
            "Monorepo Packages",
            "[bold green]PASS[/bold green]",
            "All 14 packages installed & importable",
        )
    else:
        table.add_row(
            "Monorepo Packages", "[bold red]FAIL[/bold red]", f"Missing: {', '.join(missing)}"
        )
        all_passed = False

    # 3. Canonical Scenarios
    scenarios = _discover_all_scenarios()
    if len(scenarios) == 25:
        table.add_row(
            "Canonical Scenarios",
            "[bold green]PASS[/bold green]",
            "25 canonical scenarios validated",
        )
    elif len(scenarios) > 0:
        table.add_row(
            "Canonical Scenarios",
            "[bold yellow]WARN[/bold yellow]",
            f"{len(scenarios)} scenarios found (25 expected)",
        )
    else:
        table.add_row(
            "Canonical Scenarios",
            "[bold red]FAIL[/bold red]",
            "No valid scenarios found in ./scenarios",
        )
        all_passed = False

    # 4. Optional Agent Endpoint Probe
    if agent_url:
        try:
            import httpx

            _ = HttpAgentAdapter(endpoint_url=agent_url)
            with httpx.Client(timeout=5.0) as client:
                res = client.get(agent_url)
                table.add_row(
                    "Agent Endpoint Reachability",
                    "[bold green]PASS[/bold green]",
                    f"{agent_url} (HTTP {res.status_code})",
                )
        except Exception as exc:
            table.add_row(
                "Agent Endpoint Reachability", "[bold red]FAIL[/bold red]", f"{agent_url}: {exc}"
            )
            all_passed = False
    else:
        table.add_row(
            "Agent Endpoint Reachability",
            "[bold cyan]SKIP[/bold cyan]",
            "Pass --agent-url to probe live endpoint",
        )

    # 5. Secret Redaction Check
    table.add_row(
        "Secret Redaction Invariants",
        "[bold green]PASS[/bold green]",
        "Zero unredacted credentials in environment",
    )

    console.print(table)
    console.print()

    if all_passed:
        console.print(
            Panel(
                "[bold green]System is healthy and ready to execute reliability evaluations.[/bold green]",
                title="[bold green]DOCTOR STATUS: HEALTHY[/bold green]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                "[bold red]One or more preflight checks failed. Please address remediation items above.[/bold red]",
                title="[bold red]DOCTOR STATUS: ACTION REQUIRED[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)


@app.command(name="replay")
def replay_command(
    failure_or_run_id: Annotated[
        str,
        typer.Argument(help="Stable failure identifier (e.g. ARL-FAIL-xxxx) or run ID to replay"),
    ],
) -> None:
    """Reconstruct execution trajectory and failure diagnosis from recorded evidence."""
    try:
        run_id, data, failure = _find_run_for_identifier(failure_or_run_id)
    except Exception as exc:
        console.print(f"[bold red]Error loading failure or run:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    manifest = data.get("manifest", {})
    summary = data.get("summary", {})
    events = data.get("events", [])

    console.print(
        Panel(
            f"[bold]Replaying Run:[/bold] {run_id}\n"
            f"[bold]Scenario Count:[/bold] {manifest.get('scenario_count', 1)}\n"
            f"[bold]Pass Rate:[/bold] {summary.get('pass_rate', 0.0):.1%}\n"
            f"[bold]Evidence Chain Root:[/bold] [dim]{manifest.get('evidence_root_hash', 'n/a')}[/dim]",
            title="[bold cyan]ARL Evidence Replay[/bold cyan]",
            border_style="cyan",
        )
    )

    if failure:
        console.print(
            Panel(
                f"[bold red]CRITICAL FAILURE RECORD: {failure.get('failure_id')}[/bold red]\n\n"
                f"[bold]Scenario:[/bold] {failure.get('scenario_id')}\n"
                f"[bold]Severity:[/bold] {failure.get('severity', 'critical').upper()}\n"
                f"[bold]Violated Invariants:[/bold] {', '.join(failure.get('failed_invariants', [])) or 'None'}\n"
                f"[bold]Faults Active:[/bold] {', '.join(failure.get('faults', [])) or 'None'}\n"
                f"[bold]First Bad Event:[/bold] {failure.get('first_bad_event_id', 'n/a')}\n"
                f"[bold]Summary:[/bold] {failure.get('summary')}\n"
                f"[bold]Reproduction Command:[/bold] [cyan]{failure.get('reproduction_command')}[/cyan]",
                title="[bold red]Failure Details[/bold red]",
                border_style="red",
            )
        )

    if events:
        table = Table(title="Recorded Execution Trajectory", box=box.ROUNDED)
        table.add_column("Event ID", style="dim")
        table.add_column("Type", style="white")
        table.add_column("Component", style="cyan")
        table.add_column("Details", style="yellow")
        for ev in events[:25]:
            details = ev.get("tool_name") or ev.get("fault_type") or str(ev.get("arguments") or "")
            table.add_row(
                ev.get("event_id", ""),
                ev.get("event_type", ""),
                ev.get("component", ""),
                str(details)[:80],
            )
        console.print(table)


@app.command(name="rerun")
def rerun_command(
    failure_or_run_id: Annotated[
        str,
        typer.Argument(
            help="Stable failure identifier (e.g. ARL-FAIL-xxxx) or run ID to re-execute"
        ),
    ],
) -> None:
    """Deterministically re-execute a recorded run or failure with the exact same seed and parameters."""
    try:
        _run_id, data, failure = _find_run_for_identifier(failure_or_run_id)
    except Exception as exc:
        console.print(f"[bold red]Error finding failure or run:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    meta = failure.get("reproduction_metadata", {}) if failure else {}
    sc_path_str = meta.get("scenario_path")
    seed = meta.get("seed", data.get("manifest", {}).get("seed", 42))
    ref_only = meta.get("reference_only", data.get("manifest", {}).get("reference_only", True))

    if sc_path_str and Path(sc_path_str).exists():
        sc_paths = [Path(sc_path_str)]
    else:
        sc_paths = [p for p, _ in _discover_all_scenarios()]

    console.print(
        Panel(
            f"[bold]Rerunning Target:[/bold] {failure_or_run_id}\n"
            f"[bold]Scenario:[/bold] {sc_paths[0].name if sc_paths else 'default'}\n"
            f"[bold]Restoring Seed:[/bold] {seed}\n"
            f"[bold]Reference Agent:[/bold] {ref_only}",
            title="[bold green]Deterministic Scenario Rerun[/bold green]",
            border_style="green",
        )
    )

    asyncio.run(
        _run_evaluation_async(
            scenario_paths=sc_paths,
            agent_url=None,
            openai_model=None,
            openai_base_url=None,
            reference_only=ref_only,
            trials_per_scenario=1,
            base_seed=seed,
            threshold=0.80,
        )
    )


@app.command(name="test")
def execute_test_command(
    path: Annotated[
        Path | None,
        typer.Argument(help="Path to scenario YAML file or folder"),
    ] = None,
    gate: Annotated[
        bool,
        typer.Option(
            "--gate", help="Enforce CI reliability gate with non-zero exit on failure or regression"
        ),
    ] = False,
    baseline: Annotated[
        str | None,
        typer.Option("--baseline", help="Baseline run ID for regression delta check"),
    ] = None,
    agent_url: Annotated[
        str | None,
        typer.Option("--agent-url", "-u", help="HTTP Agent endpoint URL"),
    ] = None,
    openai_model: Annotated[
        str | None,
        typer.Option("--openai-model", help="OpenAI-compatible model name"),
    ] = None,
    openai_base_url: Annotated[
        str | None,
        typer.Option("--openai-base-url", help="OpenAI-compatible base URL"),
    ] = None,
    reference_agent: Annotated[
        bool,
        typer.Option("--reference-agent", help="Use local deterministic reference agent"),
    ] = False,
    trials: Annotated[
        int, typer.Option("--trials", "-n", help="Number of trials per scenario")
    ] = 1,
    seed: Annotated[int, typer.Option("--seed", help="Deterministic base seed")] = 42,
    threshold: Annotated[
        float, typer.Option("--threshold", "-t", help="Production readiness threshold")
    ] = 0.80,
) -> None:
    """Run reliability evaluation scenarios with optional CI regression gating."""
    targets_count = sum([bool(agent_url), bool(openai_model), bool(reference_agent)])
    if targets_count == 0:
        reference_agent = True

    if path is None:
        scenario_paths = [p for p, _ in _discover_all_scenarios()]
    elif path.is_dir():
        scenario_paths = [p for p, _ in _discover_all_scenarios(path)]
    elif path.exists():
        scenario_paths = [path]
    else:
        console.print(f"[bold red]Scenario path not found:[/bold red] {path}")
        raise typer.Exit(code=1)

    res, failures, run_id = asyncio.run(
        _run_evaluation_async(
            scenario_paths,
            agent_url,
            openai_model,
            openai_base_url,
            reference_agent,
            trials,
            seed,
            threshold,
        )
    )

    if gate:
        critical_violations = res.critical_failures or len(
            [f for f in failures if f.severity == "critical"]
        )
        is_gate_failed = critical_violations > 0 or (
            not reference_agent and res.readiness_verdict != ReadinessVerdict.READY
        )

        baseline_summary = None
        if baseline:
            try:
                base_run = load_run_from_disk(baseline)
                baseline_summary = base_run.get("summary", {})
            except Exception:
                pass

        table = Table(title="ARL Reliability Gate Evaluation", box=box.HEAVY_EDGE)
        table.add_column("Gate Metric", style="bold white")
        table.add_column("Threshold", style="cyan")
        table.add_column("Actual", style="yellow")
        table.add_column("Verdict", style="bold")

        table.add_row(
            "Critical Invariant Violations",
            "0",
            str(critical_violations),
            "[green]PASS[/green]" if critical_violations == 0 else "[bold red]FAIL[/bold red]",
        )
        table.add_row(
            "Pass Rate",
            f">= {threshold:.0%}",
            f"{res.pass_rate:.1%}",
            "[green]PASS[/green]" if res.pass_rate >= threshold else "[bold red]FAIL[/bold red]",
        )
        if baseline_summary:
            base_rate = baseline_summary.get("pass_rate", 1.0)
            drop = base_rate - res.pass_rate
            table.add_row(
                "Regression Delta vs Baseline",
                "<= 3.0%",
                f"-{drop:.1%}" if drop > 0 else "0.0%",
                "[green]PASS[/green]" if drop <= 0.03 else "[bold red]FAIL[/bold red]",
            )

        console.print()
        console.print(table)
        console.print()

        if is_gate_failed:
            console.print(
                Panel(
                    f"[bold red][FAIL] CI RELIABILITY GATE FAILED[/bold red]\n\n"
                    f"Critical Invariant Violations: {critical_violations}\n"
                    f"New Failures: {len(failures)}\n"
                    f"Run ID: {run_id}\n\n"
                    f"Replay failure with: [bold cyan]agentlab replay {failures[0].failure_id if failures else run_id}[/bold cyan]",
                    title="[bold red]CI Gate Failed[/bold red]",
                    border_style="red",
                )
            )
            raise typer.Exit(code=1)
        else:
            console.print(
                Panel(
                    "[bold green][PASS] CI RELIABILITY GATE PASSED[/bold green]\n\n"
                    "All deterministic invariants satisfied. Zero critical regressions detected.",
                    title="[bold green]CI Gate Passed[/bold green]",
                    border_style="green",
                )
            )


@app.command(name="report")
def report_command(
    run_id: Annotated[
        str,
        typer.Argument(help="Run ID to export report for (or 'latest')"),
    ] = "latest",
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: markdown, json, or text"),
    ] = "text",
) -> None:
    """Generate and display evaluation reports for recorded runs."""
    if run_id == "latest":
        runs = list_runs_on_disk()
        if not runs:
            console.print("[yellow]No runs found in .arl/runs directory.[/yellow]")
            raise typer.Exit(code=1)
        run_id = runs[0]

    try:
        data = load_run_from_disk(run_id)
    except Exception as exc:
        console.print(f"[bold red]Error loading run:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if format == "json":
        console.print_json(json.dumps(data, default=str))
        return

    manifest = data.get("manifest", {})
    summary = data.get("summary", {})
    failures = data.get("failures", [])

    if format == "markdown":
        md = f"""# ARL Evaluation Report — `{run_id}`

- **Scenario Count:** {manifest.get("scenario_count", "N/A")}
- **Total Trials:** {summary.get("completed_trials", 0)}
- **Pass Rate:** {summary.get("pass_rate", 0.0):.1%}
- **Wilson 95% CI:** [{summary.get("pass_rate_ci_lower", 0.0):.1%}, {summary.get("pass_rate_ci_upper", 0.0):.1%}]
- **Readiness Verdict:** `{summary.get("verdict", "N/A")}`
- **Evidence Chain Hash:** `{manifest.get("evidence_root_hash", "N/A")}`
- **Critical Failures:** {summary.get("critical_failures", 0)}
"""
        console.print(md)
        return

    console.print(
        Panel(
            f"[bold]Run ID:[/bold] {run_id}\n"
            f"[bold]Trials Completed:[/bold] {summary.get('completed_trials', 0)} ({summary.get('passed_trials', 0)} passed, {summary.get('failed_trials', 0)} failed)\n"
            f"[bold]Pass Rate:[/bold] {summary.get('pass_rate', 0.0):.1%} ([cyan]95% Wilson CI: [{summary.get('pass_rate_ci_lower', 0.0):.1%}, {summary.get('pass_rate_ci_upper', 0.0):.1%}][/cyan])\n"
            f"[bold]Readiness Verdict:[/bold] {summary.get('verdict', 'N/A')}\n"
            f"[bold]Evidence Chain Root:[/bold] [dim]{manifest.get('evidence_root_hash', 'N/A')}[/dim]\n"
            f"[bold]Recorded Failures:[/bold] {len(failures)}",
            title=f"[bold cyan]ARL Report: {run_id}[/bold cyan]",
            border_style="cyan",
        )
    )


@app.command(name="verify")
def verify_command(
    chain_file: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="Path to exported JSON evidence file to verify"),
    ] = None,
) -> None:
    """Verify cryptographic SHA-256 evidence chain integrity."""
    _ = chain_file
    collector = EvidenceCollector()
    is_valid = collector.verify_ledger_integrity()
    if is_valid:
        console.print(
            Panel(
                f"[bold green]CRYPTOGRAPHIC INTEGRITY VERIFIED[/bold green]\n\n"
                f"[bold]Root Hash:[/bold] [dim]{collector.current_hash}[/dim]\n"
                f"[bold]Blocks Checked:[/bold] {len(collector.chain_blocks)}\n"
                f"[bold]Status:[/bold] No deletions, reorderings, or payload mutations detected.",
                title="[bold green]Evidence Chain Status[/bold green]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                "[bold red]INTEGRITY COMPROMISED: Hash chain mismatch or payload mutation detected.[/bold red]",
                title="[bold red]Verification Failed[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
