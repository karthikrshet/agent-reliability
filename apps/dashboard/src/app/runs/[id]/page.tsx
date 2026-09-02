"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Bug,
  Database,
  CheckCircle2,
  XCircle,
  Hash,
  Terminal,
  ChevronRight,
  Layers,
  RefreshCw,
} from "lucide-react";
import {
  fetchRun,
  fetchRunTrials,
  EvaluationRun,
  TrialDetail,
} from "@/lib/api";

export default function RunDetailPage() {
  const params = useParams();
  const runId = Array.isArray(params?.id) ? params.id[0] : (params?.id as string);

  const [run, setRun] = useState<EvaluationRun | null>(null);
  const [trials, setTrials] = useState<TrialDetail[]>([]);
  const [selectedTrialId, setSelectedTrialId] = useState<string | null>(null);
  const [selectedTurn, setSelectedTurn] = useState<number>(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRunData = async () => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    try {
      const [runData, trialsData] = await Promise.all([
        fetchRun(runId),
        fetchRunTrials(runId),
      ]);
      setRun(runData);
      setTrials(trialsData);
      if (trialsData.length > 0 && !selectedTrialId) {
        setSelectedTrialId(trialsData[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load run details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRunData();
  }, [runId]);

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-indigo-400" />
        Loading evaluation run details for <span className="font-mono text-white">{runId}</span>...
      </div>
    );
  }

  if (!run) {
    return (
      <div className="p-8 max-w-4xl mx-auto text-center space-y-4">
        <h1 className="text-xl font-bold text-white">Evaluation Run Not Found</h1>
        <p className="text-sm text-slate-400">
          No persisted evaluation run with ID <span className="font-mono text-indigo-400">{runId}</span> was found.
        </p>
        <Link
          href="/runs"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-sm text-slate-300 hover:text-white"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Evaluation Runs
        </Link>
      </div>
    );
  }

  const selectedTrial = trials.find((t) => t.id === selectedTrialId) || trials[0];
  const observableTurns = selectedTrial?.observable_turns || [];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            href="/runs"
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-indigo-400">
                RUN: {run.id}
              </span>
              <span
                className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                  run.state === "COMPLETED"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                    : run.state === "RUNNING"
                    ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 animate-pulse"
                    : "bg-slate-800 text-slate-400"
                }`}
              >
                {run.state}
              </span>
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight mt-0.5">
              Observable Trajectory & Fault Inspector
            </h1>
          </div>
        </div>

        <button
          onClick={loadRunData}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300 hover:text-white transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Run
        </button>
      </div>

      {/* Trial Selector Strip */}
      {trials.length > 0 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-2 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-xs font-semibold text-slate-400 px-2 shrink-0">
            Trials ({trials.length}):
          </span>
          {trials.map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setSelectedTrialId(t.id);
                setSelectedTurn(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono transition shrink-0 flex items-center gap-1.5 ${
                selectedTrialId === t.id
                  ? "bg-indigo-600 text-white font-bold"
                  : "bg-slate-950 text-slate-400 hover:text-white border border-slate-800"
              }`}
            >
              {t.verdict === "PASS" ? (
                <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              ) : t.verdict === "CRITICAL_FAIL" ? (
                <XCircle className="w-3 h-3 text-rose-400" />
              ) : (
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
              )}
              {t.id}
            </button>
          ))}
        </div>
      )}

      {/* Trajectory Turns & Inspector Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Turns Column */}
        <div className="lg:col-span-1 space-y-3">
          <h3 className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
            Execution Turns ({observableTurns.length})
          </h3>

          {observableTurns.length === 0 ? (
            <div className="p-8 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-500">
              No turn records captured for this trial.
            </div>
          ) : (
            observableTurns.map((turn) => {
              const isSelected = selectedTurn === turn.turn_index;
              return (
                <div
                  key={turn.turn_index}
                  onClick={() => setSelectedTurn(turn.turn_index)}
                  className={`p-4 rounded-xl cursor-pointer transition border ${
                    isSelected
                      ? "bg-slate-900 border-indigo-500/60"
                      : "bg-slate-900/40 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-white font-mono">
                      Turn #{turn.turn_index}
                    </span>
                    {turn.fault_injected && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30 font-bold">
                        FAULT INJECTED
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 line-clamp-2">
                    {turn.raw_text ||
                      (turn.tool_calls && turn.tool_calls.length > 0
                        ? `Tool: ${turn.tool_calls[0].tool_name}`
                        : "Turn completed")}
                  </p>
                </div>
              );
            })
          )}
        </div>

        {/* Turn Inspector Column */}
        <div className="lg:col-span-2 space-y-4">
          {observableTurns.length > 0 ? (
            (() => {
              const activeTurn =
                observableTurns.find((t) => t.turn_index === selectedTurn) ||
                observableTurns[0];

              return (
                <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 space-y-5">
                  <div className="flex items-center justify-between">
                    <h2 className="text-base font-bold text-white flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-indigo-400" />
                      Turn #{activeTurn.turn_index} Observable Events
                    </h2>
                    <span className="text-xs font-mono text-slate-400">
                      Output Type: {activeTurn.agent_output_type}
                    </span>
                  </div>

                  {/* User Input Prompt */}
                  {activeTurn.user_input && (
                    <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                      <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                        Conversation Input
                      </span>
                      <p className="text-xs text-slate-200 font-mono">
                        {activeTurn.user_input}
                      </p>
                    </div>
                  )}

                  {/* Injected Fault Details */}
                  {activeTurn.fault_injected && (
                    <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 space-y-1">
                      <div className="flex items-center gap-2 text-amber-400 font-bold text-xs">
                        <Bug className="w-3.5 h-3.5" />
                        Injected Chaos Fault: {activeTurn.fault_injected.fault_type}
                      </div>
                      <p className="text-xs text-amber-200/90">
                        {activeTurn.fault_injected.description}
                      </p>
                    </div>
                  )}

                  {/* Tool Invocations */}
                  {activeTurn.tool_calls && activeTurn.tool_calls.length > 0 && (
                    <div className="space-y-2">
                      <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider flex items-center gap-1.5">
                        <Database className="w-3 h-3 text-indigo-400" />
                        Observable Tool Calls ({activeTurn.tool_calls.length})
                      </span>
                      {activeTurn.tool_calls.map((tc, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5 font-mono text-xs"
                        >
                          <div className="flex items-center justify-between text-indigo-400">
                            <span className="font-bold">{tc.tool_name}</span>
                            <span className="text-[10px] text-slate-500">
                              {tc.tool_call_id || tc.id || `call_${idx}`}
                            </span>
                          </div>
                          <pre className="text-slate-300 text-[11px] overflow-x-auto">
                            {JSON.stringify(tc.arguments, null, 2)}
                          </pre>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Agent Output Message */}
                  {activeTurn.raw_text && (
                    <div className="p-3.5 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1">
                      <span className="text-[10px] uppercase font-bold text-emerald-400 tracking-wider">
                        Agent Final Output
                      </span>
                      <p className="text-xs text-slate-200">{activeTurn.raw_text}</p>
                    </div>
                  )}
                </div>
              );
            })()
          ) : (
            <div className="p-12 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-500">
              No turn data to inspect.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
