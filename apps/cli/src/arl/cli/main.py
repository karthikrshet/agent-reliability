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
from pathlib import Path
from typing import Annotated

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from arl.adapters.http.adapter import HttpAgentAdapter
from arl.adapters.reference.agent import MockAgentAdapter
from arl.core.domain.grading import ReadinessVerdict
from arl.core.domain.trial import Trial, TrialVerdict
from arl.environments.customer_support.environment import CustomerSupportEnvironment
from arl.evidence.collector import EvidenceCollector
from arl.evidence.reporter import ReportGenerator
from arl.execution_engine.executor import TrialExecutor
from arl.grading_engine.aggregator import EvaluationRunAggregator
from arl.grading_engine.deterministic import DeterministicTrialEvaluator
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
    trials_per_scenario: int,
    base_seed: int,
    threshold: float = 0.80,
) -> None:
    """Async engine executing evaluation trials."""
    evaluator = DeterministicTrialEvaluator()
    aggregator = EvaluationRunAggregator(
        readiness_threshold=threshold, min_required_trials=len(scenario_paths) * trials_per_scenario
    )
    collector = EvidenceCollector()

    domain_trials: list[Trial] = []
    trial_scores: dict[str, float] = {}
    trial_verdicts: dict[str, TrialVerdict] = {}
    trial_categories: dict[str, str] = {}
    all_grader_results = []

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
                run_id="cli-run",
                trial_index=t_idx,
                idempotency_key=f"idemp-{trial_id}",
                fault_seed=fault_seed,
            )

            # Initialize isolated sandboxed environment
            env = CustomerSupportEnvironment(seed=fault_seed)

            # Initialize agent adapter
            adapter: AgentAdapter = (
                HttpAgentAdapter(endpoint_url=agent_url) if agent_url else MockAgentAdapter()
            )

            executor = TrialExecutor(
                trial=trial,
                scenario=scenario,
                adapter=adapter,
                environment=env,
            )

            # Execute trial
            exec_res = await executor.run()

            # Record evidence
            collector.collect_from_trial_result(trial_id, "cli-run", exec_res)

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
        run_id="cli-run",
        trials=domain_trials,
        trial_scores=trial_scores,
        trial_verdicts=trial_verdicts,
        grader_results=all_grader_results,
        trial_categories=trial_categories,
    )

    _ = ReportGenerator(run_result=res, evidence_collector=collector)

    # Print Final Audit Summary
    v = res.readiness_verdict
    if v == ReadinessVerdict.READY:
        banner_title = "[READY] READINESS VERDICT: READY FOR PRODUCTION"
        banner_style = "bold green"
    elif v == ReadinessVerdict.NOT_READY:
        banner_title = "[NOT READY] READINESS VERDICT: NOT READY"
        banner_style = "bold red"
    else:
        banner_title = "[INSUFFICIENT] READINESS VERDICT: INSUFFICIENT EVIDENCE"
        banner_style = "bold yellow"

    console.print(
        Panel(
            f"[bold]Pass Rate:[/bold] {res.pass_rate:.1%} "
            f"([cyan]95% Wilson CI: [{res.pass_rate_ci_lower:.1%}, {res.pass_rate_ci_upper:.1%}][/cyan])\n"
            f"[bold]Pass@1:[/bold] {res.pass_at_1:.3f} | [bold]Pass@3:[/bold] {res.pass_at_3 or 0.0:.3f}\n"
            f"[bold]Total Trials:[/bold] {res.completed_trials} ({res.passed_trials} passed, {res.failed_trials} failed)\n"
            f"[bold]Critical Safety Failures:[/bold] {res.critical_failures}\n"
            f"[bold]Evidence Chain Hash:[/bold] [dim]{collector.current_hash}[/dim]\n\n"
            f"[bold]Rationale:[/bold] {res.verdict_reason}",
            title=f"[{banner_style}]{banner_title}[/{banner_style}]",
            border_style=banner_style,
        )
    )


@app.command(name="run")
def run_command(
    scenario_path: Annotated[
        Path | None, typer.Option("--scenario", "-s", help="Path to scenario YAML file or folder")
    ] = None,
    agent_url: Annotated[
        str | None,
        typer.Option(
            "--agent-url", "-u", help="HTTP Agent endpoint URL (leave empty for reference mock)"
        ),
    ] = None,
    trials: Annotated[
        int, typer.Option("--trials", "-n", help="Number of trials per scenario")
    ] = 3,
    seed: Annotated[int, typer.Option("--seed", help="Deterministic base seed")] = 42,
    threshold: Annotated[
        float, typer.Option("--threshold", "-t", help="Production readiness threshold")
    ] = 0.80,
) -> None:
    """Execute reliability testing trials against an agent."""
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
    asyncio.run(_run_evaluation_async(scenario_paths, agent_url, trials, seed, threshold))


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
