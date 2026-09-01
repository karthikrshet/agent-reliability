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
console = Console()


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
) -> None:
    """Async engine executing evaluation trials."""
    evaluator = DeterministicTrialEvaluator()
    aggregator = EvaluationRunAggregator(
        readiness_threshold=0.85, min_required_trials=len(scenario_paths) * trials_per_scenario
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
        banner_title = "🟢 READINESS VERDICT: READY FOR PRODUCTION"
        banner_style = "bold green"
    elif v == ReadinessVerdict.NOT_READY:
        banner_title = "🔴 READINESS VERDICT: NOT READY"
        banner_style = "bold red"
    else:
        banner_title = "🟡 READINESS VERDICT: INSUFFICIENT EVIDENCE"
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
        f"\n🚀 [bold]Starting evaluation across {len(scenario_paths)} scenario(s)...[/bold]\n"
    )
    asyncio.run(_run_evaluation_async(scenario_paths, agent_url, trials, seed))


if __name__ == "__main__":
    app()
