"use client";

import React, { useState } from "react";
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
} from "lucide-react";

export default function OverviewPage() {
  const [activeTab, setActiveTab] = useState<"all" | "critical">("all");

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            Agent Production Readiness
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Live Monitoring
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Statistical confidence intervals, deterministic rule grading, and sandboxed fault injection.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/scenarios"
            className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-sm font-medium text-slate-300 hover:text-white hover:border-slate-700 transition"
          >
            Explore Catalog (25)
          </Link>
          <Link
            href="/runs"
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 text-white text-sm font-semibold hover:opacity-95 shadow-lg shadow-indigo-500/25 transition flex items-center gap-2"
          >
            <Play className="w-4 h-4 fill-white" />
            Launch Evaluation Run
          </Link>
        </div>
      </div>

      {/* Hero Readiness Verdict Banner */}
      <div className="relative overflow-hidden rounded-2xl p-6 bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-indigo-950/40 border border-indigo-500/20 shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
          {/* Main Verdict Status */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
                <ShieldCheck className="w-7 h-7 text-emerald-400" />
              </div>
              <div>
                <span className="text-xs font-semibold tracking-wider text-emerald-400 uppercase">
                  Statistical Readiness Verdict
                </span>
                <h2 className="text-xl font-bold text-white">READY FOR PRODUCTION</h2>
              </div>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed max-w-2xl">
              Target agent passed 25 canonical evaluation scenarios across 75 trials with{" "}
              <strong className="text-white">92.0% empirical pass rate</strong>. Lower bound of the 95% Wilson score confidence interval is{" "}
              <span className="text-emerald-400 font-semibold">83.6%</span> (exceeding production readiness threshold 80.0%). Zero safety vetoes triggered.
            </p>

            {/* Wilson Score Bar */}
            <div className="space-y-1.5 pt-2">
              <div className="flex justify-between text-xs font-medium">
                <span className="text-slate-400">95% Wilson Score Confidence Interval</span>
                <span className="text-slate-200 font-mono">[83.6% — 96.3%]</span>
              </div>
              <div className="w-full h-3 bg-slate-950/80 rounded-full overflow-hidden border border-slate-800 relative">
                {/* Confidence Interval band */}
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 rounded-full"
                  style={{ width: "92%", marginLeft: "0%" }}
                />
                {/* Threshold line at 80% */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-amber-400 z-10"
                  style={{ left: "80%" }}
                  title="Threshold (80%)"
                />
              </div>
              <div className="flex justify-between text-[11px] text-slate-500 font-mono">
                <span>0%</span>
                <span className="text-amber-400">Threshold: 80%</span>
                <span>100%</span>
              </div>
            </div>
          </div>

          {/* Quick Metrics Pillar */}
          <div className="grid grid-cols-2 gap-3 p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <div className="p-3 rounded-lg bg-slate-900/40">
              <p className="text-xs text-slate-400">Pass@1</p>
              <p className="text-xl font-bold text-white font-mono mt-0.5">0.920</p>
              <p className="text-[11px] text-emerald-400 flex items-center gap-0.5 mt-1">
                <TrendingUp className="w-3 h-3" /> +4.2% vs v0.9
              </p>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/40">
              <p className="text-xs text-slate-400">Pass@3 (Unbiased)</p>
              <p className="text-xl font-bold text-white font-mono mt-0.5">0.978</p>
              <p className="text-[11px] text-slate-400 mt-1">k=3 trials</p>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/40">
              <p className="text-xs text-slate-400">Avg Duration</p>
              <p className="text-xl font-bold text-white font-mono mt-0.5">1.42s</p>
              <p className="text-[11px] text-slate-400 mt-1">per trial</p>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/40">
              <p className="text-xs text-slate-400">Safety Vetoes</p>
              <p className="text-xl font-bold text-emerald-400 font-mono mt-0.5">0</p>
              <p className="text-[11px] text-emerald-400 mt-1">Zero critical fails</p>
            </div>
          </div>
        </div>
      </div>

      {/* 5 Core Evaluation Pillars */}
      <div>
        <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4 text-indigo-400" />
          Reliability Dimension Breakdown
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {[
            {
              title: "Tool Correctness",
              scenarios: "5 Scenarios",
              passRate: "100%",
              status: "Passed",
              color: "emerald",
              description: "Argument typing, schema constraints, idempotency keys",
            },
            {
              title: "Error Recovery",
              scenarios: "5 Scenarios",
              passRate: "93.3%",
              status: "Passed",
              color: "emerald",
              description: "500 server errors, timeouts, transient retries with backoff",
            },
            {
              title: "Budget Enforcement",
              scenarios: "5 Scenarios",
              passRate: "86.7%",
              status: "Passed",
              color: "emerald",
              description: "Max turns, token caps, runaway cascade loop termination",
            },
            {
              title: "Multi-Tenant Isolation",
              scenarios: "5 Scenarios",
              passRate: "100%",
              status: "Passed",
              color: "emerald",
              description: "Cross-tenant boundaries, zero unauthorized data access",
            },
            {
              title: "Prompt Injection",
              scenarios: "5 Scenarios",
              passRate: "80.0%",
              status: "Passed",
              color: "amber",
              description: "Indirect instruction overrides in tool outputs",
            },
          ].map((pillar) => (
            <div
              key={pillar.title}
              className="p-4 rounded-xl glass-panel glass-panel-hover flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-slate-400">{pillar.scenarios}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-mono font-semibold ${
                      pillar.color === "emerald"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                        : "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                    }`}
                  >
                    {pillar.passRate}
                  </span>
                </div>
                <h4 className="text-sm font-bold text-white mb-1">{pillar.title}</h4>
                <p className="text-xs text-slate-400 line-clamp-2">{pillar.description}</p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-indigo-400 font-medium">
                <span>View Scenarios</span>
                <ArrowUpRight className="w-3.5 h-3.5" />
              </div>
            </div>
          ))}
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
          <span>agentlab run -s scenarios/ -n 3 --seed 42</span>
        </div>
      </div>
    </div>
  );
}
