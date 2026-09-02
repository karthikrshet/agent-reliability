"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  AlertTriangle,
  Play,
  ArrowUpRight,
  Terminal,
  Activity,
  Layers,
  Lock,
  RefreshCw,
} from "lucide-react";
import {
  fetchRuns,
  fetchScenarios,
  EvaluationRun,
  ScenarioSummary,
} from "@/lib/api";

export default function OverviewPage() {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [runsData, scenariosData] = await Promise.all([
        fetchRuns(),
        fetchScenarios(),
      ]);
      setRuns(runsData);
      setScenarios(scenariosData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const latestCompletedRun = runs.find(
    (r) => r.state === "COMPLETED" || r.completed_trials > 0
  );

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            Agent Reliability Overview
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Connected Backend
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Statistical confidence intervals, deterministic rule grading, and sandboxed fault injection.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition"
            title="Refresh Data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
          <Link
            href="/scenarios"
            className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-sm font-medium text-slate-300 hover:text-white hover:border-slate-700 transition"
          >
            Catalog ({scenarios.length || 25})
          </Link>
          <Link
            href="/runs"
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 text-white text-sm font-semibold hover:opacity-95 shadow-lg shadow-indigo-500/25 transition flex items-center gap-2"
          >
            <Play className="w-4 h-4 fill-white" />
            Evaluation Runs
          </Link>
        </div>
      </div>

      {/* Main Readiness Verdict Banner */}
      {latestCompletedRun ? (
        <div className="relative overflow-hidden rounded-2xl p-6 bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-indigo-950/40 border border-indigo-500/20 shadow-2xl">
          <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
            {/* Main Verdict Status */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center gap-3">
                <div
                  className={`w-12 h-12 rounded-2xl flex items-center justify-center ${
                    latestCompletedRun.readiness_verdict === "READY"
                      ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                      : latestCompletedRun.readiness_verdict === "NOT_READY"
                      ? "bg-rose-500/10 border border-rose-500/30 text-rose-400"
                      : "bg-amber-500/10 border border-amber-500/30 text-amber-400"
                  }`}
                >
                  {latestCompletedRun.readiness_verdict === "READY" ? (
                    <ShieldCheck className="w-7 h-7" />
                  ) : (
                    <ShieldAlert className="w-7 h-7" />
                  )}
                </div>
                <div>
                  <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">
                    Evaluation Run: {latestCompletedRun.id}
                  </span>
                  <h2 className="text-xl font-bold text-white">
                    {latestCompletedRun.readiness_verdict || "EVALUATION COMPLETED"}
                  </h2>
                </div>
              </div>

              <p className="text-sm text-slate-300 leading-relaxed max-w-2xl">
                {latestCompletedRun.verdict_reason ||
                  `Completed ${latestCompletedRun.completed_trials} trials with ${(
                    latestCompletedRun.pass_rate * 100
                  ).toFixed(1)}% empirical pass rate.`}
              </p>

              {/* Wilson Score Bar */}
              {latestCompletedRun.pass_rate_ci_lower !== undefined &&
              latestCompletedRun.pass_rate_ci_upper !== undefined ? (
                <div className="space-y-1.5 pt-2">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-slate-400">
                      95% Wilson Score Confidence Interval (N={latestCompletedRun.completed_trials})
                    </span>
                    <span className="text-slate-200 font-mono">
                      [{(latestCompletedRun.pass_rate_ci_lower * 100).toFixed(1)}% —{" "}
                      {(latestCompletedRun.pass_rate_ci_upper * 100).toFixed(1)}%]
                    </span>
                  </div>
                  <div className="w-full h-3 bg-slate-950/80 rounded-full overflow-hidden border border-slate-800 relative">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 rounded-full"
                      style={{
                        width: `${Math.min(100, Math.max(0, latestCompletedRun.pass_rate * 100))}%`,
                      }}
                    />
                    <div
                      className="absolute top-0 bottom-0 w-0.5 bg-amber-400 z-10"
                      style={{ left: "80%" }}
                      title="Readiness Threshold (80%)"
                    />
                  </div>
                  <div className="flex justify-between text-[11px] text-slate-500 font-mono">
                    <span>0%</span>
                    <span className="text-amber-400">Threshold: 80%</span>
                    <span>100%</span>
                  </div>
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-slate-950/50 border border-slate-800 text-xs text-amber-300">
                  ⚠️ Sample size too small to compute valid Wilson confidence intervals.
                </div>
              )}
            </div>

            {/* Quick Metrics Pillar */}
            <div className="grid grid-cols-2 gap-3 p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
              <div className="p-3 rounded-lg bg-slate-900/40">
                <p className="text-xs text-slate-400">Pass Rate</p>
                <p className="text-xl font-bold text-white font-mono mt-0.5">
                  {(latestCompletedRun.pass_rate * 100).toFixed(1)}%
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  {latestCompletedRun.passed_trials}/{latestCompletedRun.completed_trials} trials
                </p>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/40">
                <p className="text-xs text-slate-400">Pass@1</p>
                <p className="text-xl font-bold text-white font-mono mt-0.5">
                  {latestCompletedRun.pass_at_1 !== undefined
                    ? latestCompletedRun.pass_at_1.toFixed(3)
                    : "N/A"}
                </p>
                <p className="text-[11px] text-slate-400 mt-1">Single trial</p>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/40">
                <p className="text-xs text-slate-400">Pass@3 (Unbiased)</p>
                <p className="text-xl font-bold text-white font-mono mt-0.5">
                  {latestCompletedRun.pass_at_3 !== undefined
                    ? latestCompletedRun.pass_at_3.toFixed(3)
                    : "N/A"}
                </p>
                <p className="text-[11px] text-slate-400 mt-1">k=3 estimator</p>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/40">
                <p className="text-xs text-slate-400">Failed Trials</p>
                <p className="text-xl font-bold text-rose-400 font-mono mt-0.5">
                  {latestCompletedRun.failed_trials}
                </p>
                <p className="text-[11px] text-slate-400 mt-1">Total errors</p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800 text-center space-y-4">
          <Activity className="w-12 h-12 text-slate-500 mx-auto" />
          <h2 className="text-lg font-bold text-white">No Evaluation Data Available</h2>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            No completed evaluation runs exist in the backend. Start the worker and launch a run via the CLI or API to view statistically valid scores.
          </p>
          <div className="pt-2">
            <Link
              href="/runs"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-500 transition"
            >
              <Play className="w-4 h-4 fill-white" />
              Go to Runs Explorer
            </Link>
          </div>
        </div>
      )}

      {/* 5 Core Evaluation Pillars */}
      <div>
        <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4 text-indigo-400" />
          Reliability Dimension Catalog
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {[
            {
              title: "Tool Correctness",
              category: "tool-correctness",
              description: "Argument typing, schema constraints, idempotency keys",
            },
            {
              title: "Error Recovery",
              category: "error-recovery",
              description: "500 server errors, timeouts, transient retries with backoff",
            },
            {
              title: "Budget Limits",
              category: "budget-limits",
              description: "Max turns, token caps, runaway cascade loop termination",
            },
            {
              title: "Multi-Tenant Isolation",
              category: "multi-tenant",
              description: "Cross-tenant boundaries, zero unauthorized data access",
            },
            {
              title: "Prompt Injection",
              category: "prompt-injection",
              description: "Indirect instruction overrides in tool outputs",
            },
          ].map((pillar) => {
            const count = scenarios.filter((s) => s.category === pillar.category).length;
            return (
              <Link
                key={pillar.title}
                href={`/scenarios?category=${pillar.category}`}
                className="p-4 rounded-xl glass-panel glass-panel-hover flex flex-col justify-between group"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-slate-400">
                      {count > 0 ? `${count} Scenarios` : "5 Scenarios"}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded font-mono font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
                      Active
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-white mb-1 group-hover:text-indigo-300 transition">
                    {pillar.title}
                  </h4>
                  <p className="text-xs text-slate-400 line-clamp-2">{pillar.description}</p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-indigo-400 font-medium">
                  <span>Explore Dimension</span>
                  <ArrowUpRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* CLI Quickstart Banner */}
      <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center">
            <Terminal className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Automate in CI/CD via CLI</p>
            <p className="text-xs text-slate-400">Run deterministic audits locally or in GitHub Actions</p>
          </div>
        </div>

        <div className="p-2.5 px-4 rounded-lg bg-slate-950 font-mono text-xs text-indigo-300 border border-slate-800 flex items-center gap-3">
          <span>agentlab run -s scenarios/ --agent-url http://127.0.0.1:8088 -n 3 --seed 42</span>
        </div>
      </div>
    </div>
  );
}
