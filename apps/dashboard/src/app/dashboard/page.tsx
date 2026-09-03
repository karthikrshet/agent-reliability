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
  Sparkles,
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
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60">
              OPERATIONS CONSOLE
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center gap-2.5">
            Agent Reliability Overview
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium flex items-center gap-1.5">
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
            className="p-2.5 rounded-xl bg-[#080f1e] border border-slate-800 text-slate-400 hover:text-white hover:border-cyan-500/40 transition shadow-sm"
            title="Refresh Data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-cyan-400" : ""}`} />
          </button>
          <Link
            href="/scenarios"
            className="lc-button-secondary text-xs px-4 py-2"
          >
            Catalog ({scenarios.length || 25})
          </Link>
          <Link
            href="/runs"
            className="lc-button-primary text-xs px-4 py-2"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            Evaluation Runs
          </Link>
        </div>
      </div>

      {/* Backend Connection Error Banner */}
      {error && (
        <div className="bg-amber-950/40 border border-amber-800/60 rounded-2xl p-5 flex items-start gap-4 text-amber-200">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">
            <p className="font-semibold text-amber-300">Backend Connection Error</p>
            <p className="text-amber-300/80 mt-1">{error}</p>
            <p className="text-xs text-amber-400/60 mt-2 font-mono">
              Start backend service with: python -m uvicorn arl.server.main:app --port 8000
            </p>
          </div>
          <button
            onClick={loadData}
            className="px-3 py-1.5 bg-amber-900/60 hover:bg-amber-800 text-amber-100 text-xs font-medium rounded-lg transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Main Readiness Verdict Banner */}
      {latestCompletedRun ? (
        <div className="relative overflow-hidden rounded-2xl p-6 bg-[#080f1e]/90 border border-cyan-500/20 shadow-2xl">
          <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

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
                  <span className="text-xs font-mono font-semibold tracking-wider text-slate-400 uppercase">
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
                    <span className="text-cyan-300 font-mono">
                      [{(latestCompletedRun.pass_rate_ci_lower * 100).toFixed(1)}% —{" "}
                      {(latestCompletedRun.pass_rate_ci_upper * 100).toFixed(1)}%]
                    </span>
                  </div>
                  <div className="w-full h-3 bg-slate-950/80 rounded-full overflow-hidden border border-slate-800 relative">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 rounded-full"
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
            <div className="grid grid-cols-2 gap-3 p-4 rounded-xl bg-[#040812] border border-slate-800/80">
              <div className="p-3 rounded-lg bg-[#080f1e]">
                <p className="text-xs text-slate-400 uppercase font-mono">Pass Rate</p>
                <p className="text-xl font-bold text-white font-mono mt-0.5">
                  {(latestCompletedRun.pass_rate * 100).toFixed(1)}%
                </p>
                <p className="text-[11px] text-slate-400 mt-1 font-mono">
                  {latestCompletedRun.passed_trials}/{latestCompletedRun.completed_trials} trials
                </p>
              </div>
              <div className="p-3 rounded-lg bg-[#080f1e]">
                <p className="text-xs text-slate-400 uppercase font-mono">Pass@1</p>
                <p className="text-xl font-bold text-cyan-300 font-mono mt-0.5">
                  {latestCompletedRun.pass_at_1 !== undefined
                    ? latestCompletedRun.pass_at_1.toFixed(3)
                    : "N/A"}
                </p>
                <p className="text-[11px] text-slate-400 mt-1">Single trial</p>
              </div>
              <div className="p-3 rounded-lg bg-[#080f1e]">
                <p className="text-xs text-slate-400 uppercase font-mono">Pass@3 (Unbiased)</p>
                <p className="text-xl font-bold text-cyan-300 font-mono mt-0.5">
                  {latestCompletedRun.pass_at_3 !== undefined
                    ? latestCompletedRun.pass_at_3.toFixed(3)
                    : "N/A"}
                </p>
                <p className="text-[11px] text-slate-400 mt-1 font-mono">k=3 estimator</p>
              </div>
              <div className="p-3 rounded-lg bg-[#080f1e]">
                <p className="text-xs text-slate-400 uppercase font-mono">Failed Trials</p>
                <p className="text-xl font-bold text-rose-400 font-mono mt-0.5">
                  {latestCompletedRun.failed_trials}
                </p>
                <p className="text-[11px] text-slate-400 mt-1 font-mono">Total errors</p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-10 rounded-2xl bg-[#080f1e] border border-cyan-500/20 text-center space-y-4">
          <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center mx-auto">
            <Activity className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold text-white">No Evaluation Data Available</h2>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            No completed evaluation runs exist in the backend. Start the worker and launch a run via the CLI or API to view statistically valid scores.
          </p>
          <div className="pt-2">
            <Link
              href="/runs"
              className="lc-button-primary text-xs px-5 py-2.5 inline-flex"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              Go to Runs Explorer
            </Link>
          </div>
        </div>
      )}

      {/* 5 Core Evaluation Pillars */}
      <div>
        <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
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
                    <span className="text-xs px-2 py-0.5 rounded font-mono font-semibold bg-cyan-950 text-cyan-400 border border-cyan-800/60">
                      Active
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-white mb-1 group-hover:text-cyan-300 transition">
                    {pillar.title}
                  </h4>
                  <p className="text-xs text-slate-400 line-clamp-2">{pillar.description}</p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-cyan-400 font-medium">
                  <span>Explore Dimension</span>
                  <ArrowUpRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* CLI Quickstart Banner */}
      <div className="p-5 rounded-xl bg-[#080f1e] border border-cyan-500/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
            <Terminal className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Automate in CI/CD via CLI</p>
            <p className="text-xs text-slate-400">Run deterministic audits locally or in GitHub Actions</p>
          </div>
        </div>

        <div className="p-2.5 px-4 rounded-lg bg-[#03060f] font-mono text-xs text-cyan-300 border border-slate-800 flex items-center gap-3">
          <code>agentlab test scenarios/ --gate --threshold 0.85</code>
        </div>
      </div>
    </div>
  );
}
