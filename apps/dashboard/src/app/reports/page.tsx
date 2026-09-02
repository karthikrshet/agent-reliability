"use client";

import React, { useEffect, useState } from "react";
import {
  FileCheck,
  ShieldCheck,
  ShieldAlert,
  Download,
  Copy,
  Check,
  Hash,
  FileText,
  Lock,
  ExternalLink,
  RefreshCw,
} from "lucide-react";
import {
  fetchRuns,
  fetchRunReport,
  fetchRunEvidence,
  EvaluationRun,
  EvidenceChain,
} from "@/lib/api";

export default function ReportsPage() {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [reportMarkdown, setReportMarkdown] = useState<string>("");
  const [evidence, setEvidence] = useState<EvidenceChain | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [reportLoading, setReportLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = async () => {
    setLoading(true);
    setError(null);
    try {
      const runsData = await fetchRuns();
      setRuns(runsData);
      if (runsData.length > 0 && !selectedRunId) {
        const first = runsData[0].id;
        setSelectedRunId(first);
        loadReportForRun(first);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load evaluation reports");
    } finally {
      setLoading(false);
    }
  };

  const loadReportForRun = async (runId: string) => {
    setReportLoading(true);
    setError(null);
    try {
      const [md, ev] = await Promise.all([
        fetchRunReport(runId, "markdown"),
        fetchRunEvidence(runId),
      ]);
      setReportMarkdown(md);
      setEvidence(ev);
    } catch (err) {
      setReportMarkdown("");
      setEvidence(null);
      setError(err instanceof Error ? err.message : "Failed to load report for selected run");
    } finally {
      setReportLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const handleSelectRun = (runId: string) => {
    setSelectedRunId(runId);
    loadReportForRun(runId);
  };

  const handleCopy = () => {
    if (!reportMarkdown) return;
    navigator.clipboard.writeText(reportMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!reportMarkdown || !selectedRunId) return;
    const blob = new Blob([reportMarkdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ARL-Report-${selectedRunId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <FileCheck className="w-6 h-6 text-indigo-400" />
            Audit Reports & Cryptographic Evidence
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Tamper-evident evaluation records, SHA-256 hash chains, and compliance exports.
          </p>
        </div>

        {reportMarkdown && (
          <div className="flex items-center gap-3">
            <button
              onClick={handleCopy}
              className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-sm font-medium text-slate-300 hover:text-white transition flex items-center gap-2"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              {copied ? "Copied Markdown!" : "Copy Report"}
            </button>
            <button
              onClick={handleDownload}
              className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-500 shadow-lg shadow-indigo-500/25 transition flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Download Audit (.md)
            </button>
          </div>
        )}
      </div>

      {/* Backend Connection Error Banner */}
      {error && (
        <div className="bg-amber-950/40 border border-amber-800/60 rounded-xl p-5 flex items-start gap-4 text-amber-200">
          <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">
            <p className="font-semibold text-amber-300">Backend Connection Error</p>
            <p className="text-amber-300/80 mt-1">{error}</p>
          </div>
          <button
            onClick={loadRuns}
            className="px-3 py-1.5 bg-amber-900/60 hover:bg-amber-800 text-amber-100 text-xs font-medium rounded-lg transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Run Selection & Evidence Chain Bar */}
      {runs.length > 0 ? (
        <div className="space-y-6">
          <div className="flex items-center gap-2 overflow-x-auto pb-2 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-xs font-semibold text-slate-400 px-2 shrink-0">
              Select Evaluation Run:
            </span>
            {runs.map((r) => (
              <button
                key={r.id}
                onClick={() => handleSelectRun(r.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition shrink-0 ${
                  selectedRunId === r.id
                    ? "bg-indigo-600 text-white font-bold"
                    : "bg-slate-950 text-slate-400 hover:text-white border border-slate-800"
                }`}
              >
                {r.id} ({r.state})
              </button>
            ))}
          </div>

          {/* Cryptographic Ledger Summary Card */}
          {evidence && (
            <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    evidence.integrity_verified
                      ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                      : "bg-rose-500/10 border border-rose-500/30 text-rose-400"
                  }`}
                >
                  {evidence.integrity_verified ? (
                    <ShieldCheck className="w-6 h-6" />
                  ) : (
                    <ShieldAlert className="w-6 h-6" />
                  )}
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">
                    {evidence.integrity_verified
                      ? "Cryptographic SHA-256 Chain Verified"
                      : "Evidence Chain Tampering Detected"}
                  </h3>
                  <p className="text-xs text-slate-400 font-mono">
                    Root Hash: {evidence.root_hash} ({evidence.total_blocks} blocks)
                  </p>
                </div>
              </div>

              <div className="text-xs text-slate-400 font-mono">
                Run ID: <span className="text-indigo-400">{selectedRunId}</span>
              </div>
            </div>
          )}

          {/* Report Viewer */}
          <div className="p-6 rounded-xl bg-slate-950 border border-slate-800">
            {reportLoading ? (
              <div className="p-12 text-center text-slate-400">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
                Fetching real audit report from backend...
              </div>
            ) : reportMarkdown ? (
              <pre className="font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed overflow-x-auto">
                {reportMarkdown}
              </pre>
            ) : (
              <div className="p-12 text-center text-slate-500 text-xs">
                No report generated for this run yet.
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="p-12 rounded-2xl bg-slate-900/40 border border-slate-800 text-center space-y-3">
          <FileText className="w-12 h-12 text-slate-600 mx-auto" />
          <h2 className="text-base font-bold text-white">No Reports Available</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            No evaluation reports found in the backend. Run an evaluation to generate a tamper-evident audit report.
          </p>
        </div>
      )}
    </div>
  );
}
