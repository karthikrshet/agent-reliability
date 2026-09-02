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
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Canonical Scenario Catalog
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 font-medium">
              {scenarios.length} Scenarios
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            JSON Schema 2020-12 validated test definitions across 5 reliability dimensions.
          </p>
        </div>

        <button
          onClick={loadScenarios}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-sm font-medium text-slate-300 hover:text-white transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Reload Catalog
        </button>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800">
        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-2 md:pb-0">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition ${
                selectedCategory === cat.id
                  ? "bg-indigo-600 text-white shadow-sm"
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
            className="w-full pl-9 pr-4 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
          />
        </div>
      </div>

      {/* Main Grid: Catalog List & Detail Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scenario List */}
        <div className="lg:col-span-2 space-y-3">
          {loading ? (
            <div className="p-12 text-center text-slate-400 bg-slate-900/40 rounded-xl border border-slate-800">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
              Loading scenario catalog from backend...
            </div>
          ) : filteredScenarios.length === 0 ? (
            <div className="p-12 text-center text-slate-400 bg-slate-900/40 rounded-xl border border-slate-800">
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
                      ? "bg-slate-900 border-indigo-500/60 shadow-lg shadow-indigo-500/5"
                      : "bg-slate-900/50 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900/80"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-indigo-400">
                          {scenario.id}
                        </span>
                        <span
                          className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${sevColor}`}
                        >
                          {scenario.severity}
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-white">{scenario.title}</h3>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-400 shrink-0">
                      <span className="flex items-center gap-1 font-mono">
                        <Clock className="w-3.5 h-3.5" />
                        {scenario.max_turns || 5} turns
                      </span>
                      <span className="flex items-center gap-1 font-mono">
                        <Code className="w-3.5 h-3.5" />
                        {scenario.max_tool_calls || 3} calls
                      </span>
                    </div>
                  </div>

                  {scenario.tags && scenario.tags.length > 0 && (
                    <div className="flex items-center gap-1.5 mt-3">
                      {scenario.tags.map((t) => (
                        <span
                          key={t}
                          className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800"
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
            <div className="p-6 rounded-xl bg-slate-900/80 border border-slate-800 space-y-5 sticky top-24">
              <div>
                <span className="text-xs font-mono text-indigo-400 uppercase tracking-wider font-semibold">
                  {selectedScenario.category}
                </span>
                <h2 className="text-lg font-bold text-white mt-1">
                  {selectedScenario.title}
                </h2>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  ID: {selectedScenario.id}
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Severity</span>
                  <span className="font-bold text-white uppercase">
                    {selectedScenario.severity}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Max Turn Budget</span>
                  <span className="font-mono text-white">
                    {selectedScenario.max_turns || 5} turns
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Max Tool Calls</span>
                  <span className="font-mono text-white">
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
                <p className="text-xs font-mono text-slate-500 mb-2">CLI Execution Command:</p>
                <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-[11px] font-mono text-indigo-300 select-all overflow-x-auto">
                  agentlab run -s scenarios/{selectedScenario.category}/{selectedScenario.id}.yaml --agent-url http://127.0.0.1:8088
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-500">
              Select a scenario from the list to view schema details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
