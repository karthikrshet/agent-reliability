"use client";

import React, { useEffect, useState } from "react";
import {
  Search,
  Filter,
  Shield,
  AlertTriangle,
  Play,
  Code,
  Tag,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Terminal,
} from "lucide-react";
import { fetchScenarios, ScenarioSummary } from "@/lib/api";

const CATEGORIES = [
  { id: "all", name: "All Dimensions" },
  { id: "tool-correctness", name: "Tool Correctness" },
  { id: "error-recovery", name: "Error Recovery" },
  { id: "budget-limits", name: "Budget Limits" },
  { id: "multi-tenant", name: "Multi-Tenant" },
  { id: "prompt-injection", name: "Prompt Injection" },
];

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedScenario, setSelectedScenario] = useState<ScenarioSummary | null>(null);

  const loadScenarios = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchScenarios();
      setScenarios(data);
      if (data.length > 0 && !selectedScenario) {
        setSelectedScenario(data[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load scenarios");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadScenarios();
  }, []);

  const filteredScenarios = scenarios.filter((sc) => {
    const matchesCategory =
      selectedCategory === "all" || sc.category === selectedCategory;
    const matchesSearch =
      sc.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      sc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (sc.tags && sc.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase())));
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60">
              BENCHMARK SPECIFICATION
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center gap-2.5">
            Canonical Scenario Catalog
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-medium font-mono">
              {scenarios.length || 25} Scenarios
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            JSON Schema 2020-12 validated test definitions across 5 reliability dimensions.
          </p>
        </div>

        <button
          onClick={loadScenarios}
          disabled={loading}
          className="lc-button-secondary text-xs px-4 py-2"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-cyan-400" : ""}`} />
          Reload Catalog
        </button>
      </div>

      {/* Backend Connection Error Banner */}
      {error && (
        <div className="bg-amber-950/40 border border-amber-800/60 rounded-xl p-5 flex items-start gap-4 text-amber-200">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">
            <p className="font-semibold text-amber-300">Backend Connection Error</p>
            <p className="text-amber-300/80 mt-1">{error}</p>
          </div>
          <button
            onClick={loadScenarios}
            className="px-3 py-1.5 bg-amber-900/60 hover:bg-amber-800 text-amber-100 text-xs font-medium rounded-lg transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Filters & Search */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 p-4 rounded-xl bg-[#080f1e] border border-cyan-500/20">
        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-2 md:pb-0">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                selectedCategory === cat.id
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative min-w-[280px]">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search scenario ID, title, or tag..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-[#040812] border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
          />
        </div>
      </div>

      {/* Main Grid: Catalog List & Detail Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scenario List */}
        <div className="lg:col-span-2 space-y-3">
          {loading ? (
            <div className="p-12 text-center text-slate-400 bg-[#080f1e] rounded-xl border border-cyan-500/20">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-cyan-400" />
              Loading scenario catalog from backend...
            </div>
          ) : filteredScenarios.length === 0 ? (
            <div className="p-12 text-center text-slate-400 bg-[#080f1e] rounded-xl border border-slate-800">
              No scenarios matched your filter criteria.
            </div>
          ) : (
            filteredScenarios.map((scenario) => {
              const isSelected = selectedScenario?.id === scenario.id;
              const sevColor =
                scenario.severity === "critical"
                  ? "text-rose-400 bg-rose-500/10 border-rose-500/30"
                  : scenario.severity === "high"
                  ? "text-amber-400 bg-amber-500/10 border-amber-500/30"
                  : "text-emerald-400 bg-emerald-500/10 border-emerald-500/30";

              return (
                <div
                  key={scenario.id}
                  onClick={() => setSelectedScenario(scenario)}
                  className={`p-4 rounded-xl cursor-pointer transition border ${
                    isSelected
                      ? "bg-[#080f1e] border-cyan-500/60 shadow-lg shadow-cyan-500/5"
                      : "bg-[#080f1e]/60 border-slate-800/80 hover:border-cyan-500/40 hover:bg-[#080f1e]"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-cyan-400">
                          {scenario.id}
                        </span>
                        <span
                          className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border font-mono ${sevColor}`}
                        >
                          {scenario.severity}
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-white">{scenario.title}</h3>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-400 shrink-0 font-mono">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-500" />
                        {scenario.max_turns || 5} turns
                      </span>
                      <span className="flex items-center gap-1">
                        <Code className="w-3.5 h-3.5 text-slate-500" />
                        {scenario.max_tool_calls || 3} calls
                      </span>
                    </div>
                  </div>

                  {scenario.tags && scenario.tags.length > 0 && (
                    <div className="flex items-center gap-1.5 mt-3">
                      {scenario.tags.map((t) => (
                        <span
                          key={t}
                          className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#040812] text-slate-400 border border-slate-800"
                        >
                          #{t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Detail Inspection Drawer */}
        <div className="lg:col-span-1">
          {selectedScenario ? (
            <div className="p-6 rounded-xl bg-[#080f1e] border border-cyan-500/20 space-y-5 sticky top-24 shadow-xl">
              <div>
                <span className="text-xs font-mono text-cyan-400 uppercase tracking-wider font-semibold">
                  {selectedScenario.category}
                </span>
                <h2 className="text-lg font-bold text-white mt-1">
                  {selectedScenario.title}
                </h2>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  ID: {selectedScenario.id}
                </p>
              </div>

              <div className="p-3.5 rounded-lg bg-[#040812] border border-slate-800 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Severity</span>
                  <span className="font-bold text-white uppercase font-mono">
                    {selectedScenario.severity}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Max Turn Budget</span>
                  <span className="font-mono text-cyan-300">
                    {selectedScenario.max_turns || 5} turns
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Max Tool Calls</span>
                  <span className="font-mono text-cyan-300">
                    {selectedScenario.max_tool_calls || 3} calls
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Fault Behaviors</span>
                  <span className="font-mono text-amber-400">
                    {selectedScenario.fault_count || 0} scheduled
                  </span>
                </div>
              </div>

              <div className="pt-2">
                <p className="text-xs font-mono text-slate-400 mb-2 flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                  CLI Execution Command:
                </p>
                <div className="p-3 rounded-lg bg-[#03060f] border border-slate-800 text-[11px] font-mono text-cyan-300 select-all overflow-x-auto">
                  agentlab test scenarios/{selectedScenario.category}/{selectedScenario.id}.yaml --gate
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 rounded-xl bg-[#080f1e]/40 border border-slate-800 text-center text-xs text-slate-500 font-mono">
              Select a scenario from the list to view schema details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
