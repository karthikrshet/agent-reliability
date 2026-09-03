"use client";

import React, { useEffect, useState } from "react";
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
  AlertCircle,
  Terminal,
  ArrowUpRight,
} from "lucide-react";
import { fetchRuns, EvaluationRun } from "@/lib/api";

export default function RunsPage() {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRuns();
      setRuns(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load evaluation runs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60">
              EVALUATION LOGS
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">Evaluation Runs</h1>
          <p className="text-sm text-slate-400 mt-1">
            Track multi-trial evaluation runs, statistical confidence bounds, and pass@k reliability.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadRuns}
            disabled={loading}
            className="lc-button-secondary text-xs px-4 py-2"
            title="Refresh Runs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-cyan-400" : ""}`} />
            Refresh Runs
          </button>
        </div>
      </div>

      {/* Runs Table / List */}
      <div className="rounded-2xl bg-[#080f1e] border border-cyan-500/20 overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-12 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-cyan-400" />
            Loading evaluation runs from backend...
          </div>
        ) : error ? (
          <div className="p-8 text-center text-rose-400 space-y-2">
            <AlertCircle className="w-8 h-8 mx-auto" />
            <p className="font-semibold">{error}</p>
            <button
              onClick={loadRuns}
              className="px-4 py-1.5 rounded-lg bg-slate-800 text-white text-xs hover:bg-slate-700"
            >
              Retry
            </button>
          </div>
        ) : runs.length === 0 ? (
          <div className="p-12 text-center text-slate-400 space-y-4">
            <Clock className="w-10 h-10 mx-auto text-slate-600" />
            <h3 className="text-base font-semibold text-white">No Evaluation Runs Found</h3>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Execute evaluation runs using the ARL CLI:
            </p>
            <div className="inline-block p-3 px-5 rounded-lg bg-[#03060f] border border-slate-800 font-mono text-xs text-cyan-300 shadow-inner">
              agentlab test scenarios/ --gate --threshold 0.85
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#040812] border-b border-slate-800 text-slate-400 uppercase font-semibold font-mono">
                <tr>
                  <th className="p-4 pl-6">Run ID</th>
                  <th className="p-4">State</th>
                  <th className="p-4">Trials</th>
                  <th className="p-4">Pass Rate</th>
                  <th className="p-4">95% Wilson CI</th>
                  <th className="p-4">Verdict</th>
                  <th className="p-4">Created At</th>
                  <th className="p-4 pr-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {runs.map((run) => (
                  <tr
                    key={run.id}
                    className="hover:bg-slate-800/40 transition group"
                  >
                    <td className="p-4 pl-6 font-mono font-bold text-white">
                      <Link
                        href={`/runs/${run.id}`}
                        className="hover:text-cyan-400 transition"
                      >
                        {run.id}
                      </Link>
                    </td>
                    <td className="p-4">
                      <span
                        className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                          run.state === "COMPLETED"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                            : run.state === "RUNNING"
                            ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 animate-pulse"
                            : run.state === "FAILED"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {run.state}
                      </span>
                    </td>
                    <td className="p-4 font-mono text-slate-300">
                      {run.completed_trials}/{run.total_trials || run.completed_trials}
                    </td>
                    <td className="p-4 font-mono font-semibold text-white">
                      {run.pass_rate !== undefined
                        ? `${(run.pass_rate * 100).toFixed(1)}%`
                        : "-"}
                    </td>
                    <td className="p-4 font-mono text-cyan-300">
                      {run.pass_rate_ci_lower !== undefined &&
                      run.pass_rate_ci_upper !== undefined
                        ? `[${(run.pass_rate_ci_lower * 100).toFixed(1)}%, ${(
                            run.pass_rate_ci_upper * 100
                          ).toFixed(1)}%]`
                        : "N/A"}
                    </td>
                    <td className="p-4">
                      <span
                        className={`text-xs font-semibold ${
                          run.readiness_verdict === "READY"
                            ? "text-emerald-400"
                            : run.readiness_verdict === "NOT_READY"
                            ? "text-rose-400"
                            : "text-amber-400"
                        }`}
                      >
                        {run.readiness_verdict || "PENDING"}
                      </span>
                    </td>
                    <td className="p-4 text-slate-400 font-mono text-[11px]">
                      {new Date(run.created_at).toLocaleString()}
                    </td>
                    <td className="p-4 pr-6 text-right">
                      <Link
                        href={`/runs/${run.id}`}
                        className="inline-flex items-center gap-1 text-cyan-400 hover:text-cyan-300 font-medium"
                      >
                        Inspect
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
