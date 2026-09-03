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
    <div className="p-4 sm:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60">
              TAMPER-EVIDENT EVIDENCE
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <FileCheck className="w-6 h-6 text-cyan-400" />
            Audit Reports &amp; Cryptographic Evidence
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Tamper-evident evaluation records, SHA-256 hash chains, and compliance exports.
          </p>
        </div>

        {reportMarkdown && (
          <div className="flex items-center gap-3">
            <button
              onClick={handleCopy}
              className="lc-button-secondary text-xs px-4 py-2"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              {copied ? "Copied Markdown!" : "Copy Report"}
            </button>
            <button
              onClick={handleDownload}
              className="lc-button-primary text-xs px-4 py-2"
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
          <div className="flex items-center gap-2 overflow-x-auto pb-2 p-3.5 rounded-xl bg-[#080f1e] border border-cyan-500/20 shadow-sm">
            <span className="text-xs font-semibold text-slate-400 px-2 shrink-0 font-mono">
              Select Evaluation Run:
            </span>
            {runs.map((r) => (
              <button
                key={r.id}
                onClick={() => handleSelectRun(r.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono transition shrink-0 ${
                  selectedRunId === r.id
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/50 font-bold shadow-sm"
                    : "bg-[#040812] text-slate-400 hover:text-white border border-slate-800"
                }`}
              >
                {r.id} ({r.state})
              </button>
            ))}
          </div>

          {/* Cryptographic Ledger Summary Card */}
          {evidence && (
            <div className="p-5 rounded-xl bg-[#080f1e] border border-cyan-500/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-sm">
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
                    Root Hash: <span className="text-cyan-300">{evidence.root_hash}</span> ({evidence.total_blocks} blocks)
                  </p>
                </div>
              </div>

              <div className="text-xs text-slate-400 font-mono">
                Run ID: <span className="text-cyan-400">{selectedRunId}</span>
              </div>
            </div>
          )}

          {/* Report Viewer */}
          <div className="p-6 rounded-xl bg-[#040812] border border-slate-800/80 shadow-inner">
            {reportLoading ? (
              <div className="p-12 text-center text-slate-400">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-cyan-400" />
                Fetching real audit report from backend...
              </div>
            ) : reportMarkdown ? (
              <pre className="font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed overflow-x-auto">
                {reportMarkdown}
              </pre>
            ) : (
              <div className="p-12 text-center text-slate-500 text-xs font-mono">
                No report generated for this run yet.
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="p-12 rounded-2xl bg-[#080f1e] border border-cyan-500/20 text-center space-y-3">
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
