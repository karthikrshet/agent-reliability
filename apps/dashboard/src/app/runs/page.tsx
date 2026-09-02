"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  ArrowRight,
  RefreshCw,
  Plus,
  ShieldCheck,
} from "lucide-react";

interface EvaluationRunItem {
  id: string;
  agentName: string;
  agentVersion: string;
  state: "COMPLETED" | "RUNNING" | "QUEUED" | "FAILED";
  trialTotal: number;
  trialPassed: number;
  passRate: number;
  wilsonLower: number;
  wilsonUpper: number;
  createdAt: string;
}

const SAMPLE_RUNS: EvaluationRunItem[] = [
  {
    id: "run-e2e-canary-01",
    agentName: "Retail Support Bot",
    agentVersion: "v1.2.0-rc1",
    state: "COMPLETED",
    trialTotal: 75,
    trialPassed: 69,
    passRate: 0.92,
    wilsonLower: 0.836,
    wilsonUpper: 0.963,
    createdAt: "Just now",
  },
  {
    id: "run-eval-baseline-25",
    agentName: "Retail Support Bot",
    agentVersion: "v1.1.4",
    state: "COMPLETED",
    trialTotal: 75,
    trialPassed: 64,
    passRate: 0.853,
    wilsonLower: 0.756,
    wilsonUpper: 0.919,
    createdAt: "2 hours ago",
  },
  {
    id: "run-fault-stress-test",
    agentName: "Retail Support Bot",
    agentVersion: "v1.0.0",
    state: "COMPLETED",
    trialTotal: 50,
    trialPassed: 38,
    passRate: 0.76,
    wilsonLower: 0.626,
    wilsonUpper: 0.857,
    createdAt: "Yesterday",
  },
];

export default function RunsPage() {
  const [runs, setRuns] = useState<EvaluationRunItem[]>(SAMPLE_RUNS);
  const [isTriggering, setIsTriggering] = useState(false);

  const handleLaunchRun = () => {
    setIsTriggering(true);
    setTimeout(() => {
      const newRun: EvaluationRunItem = {
        id: `run-${Date.now().toString().slice(-6)}`,
        agentName: "Retail Support Bot",
        agentVersion: "v1.2.0-canary",
        state: "COMPLETED",
        trialTotal: 25,
        trialPassed: 24,
        passRate: 0.96,
        wilsonLower: 0.805,
        wilsonUpper: 0.993,
        createdAt: "Just now",
      };
      setRuns([newRun, ...runs]);
      setIsTriggering(false);
    }, 1200);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Evaluation Runs</h1>
          <p className="text-sm text-slate-400 mt-1">
            Track multi-trial evaluation runs, statistical confidence bounds, and pass@k reliability.
          </p>
        </div>

        <button
          onClick={handleLaunchRun}
          disabled={isTriggering}
          className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 text-white text-sm font-semibold hover:opacity-95 shadow-lg shadow-indigo-500/25 transition flex items-center gap-2 disabled:opacity-50"
        >
          {isTriggering ? (
            <RefreshCw className="w-4 h-4 animate-spin text-white" />
          ) : (
            <Plus className="w-4 h-4" />
          )}
          {isTriggering ? "Spawning Trials..." : "Trigger New Run (25 Scenarios)"}
        </button>
      </div>

      {/* Runs Table */}
      <div className="rounded-2xl glass-panel overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            All Evaluation Runs ({runs.length})
          </span>
          <span className="text-xs text-indigo-400 font-medium">Auto-refreshed via Worker Leases</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/50 text-slate-400 uppercase font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4">Run Identifier</th>
                <th className="py-3.5 px-4">Agent Target</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Pass Rate</th>
                <th className="py-3.5 px-4">Wilson 95% CI</th>
                <th className="py-3.5 px-4">Trials</th>
                <th className="py-3.5 px-4">Timestamp</th>
                <th className="py-3.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {runs.map((r) => {
                const isPassed = r.wilsonLower >= 0.8;
                return (
                  <tr key={r.id} className="hover:bg-slate-900/40 transition">
                    <td className="py-4 px-4 font-mono font-bold text-white flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-indigo-400" />
                      {r.id}
                    </td>
                    <td className="py-4 px-4">
                      <div className="font-semibold text-slate-200">{r.agentName}</div>
                      <div className="text-[11px] text-slate-400 font-mono">{r.agentVersion}</div>
                    </td>
                    <td className="py-4 px-4">
                      <span className="px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        {r.state}
                      </span>
                    </td>
                    <td className="py-4 px-4 font-mono font-bold text-slate-200">
                      {(r.passRate * 100).toFixed(1)}%
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-slate-300">
                          [{(r.wilsonLower * 100).toFixed(1)}% — {(r.wilsonUpper * 100).toFixed(1)}%]
                        </span>
                        {isPassed && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                            READY
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-4 px-4 text-slate-300 font-mono">
                      {r.trialPassed} / {r.trialTotal}
                    </td>
                    <td className="py-4 px-4 text-slate-400">{r.createdAt}</td>
                    <td className="py-4 px-4 text-right">
                      <Link
                        href={`/runs/${r.id}`}
                        className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
                      >
                        Inspect Trajectory
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
