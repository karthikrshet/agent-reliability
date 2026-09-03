"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  ShieldAlert,
  ShieldCheck,
  Zap,
  Terminal,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertOctagon,
  ArrowUpRight,
  Code2,
  Boxes,
  Activity,
  Layers,
  Sparkles,
  Lock,
  FileCheck,
  ChevronDown,
  Cpu,
  Github,
  BookOpen,
  ExternalLink,
} from "lucide-react";

const LIFECYCLE_STAGES = [
  {
    id: "intercept",
    name: "Intercept",
    tagline: "Universal Tool Call Proxy & Automatic Credential Redaction",
    description:
      "Intercepts outgoing agent tool calls across HTTP, MCP, and custom adapters without modifying your agent's source code. Recursively strips sensitive keys (authorization, api_key, cookie, token) before evidence logging.",
    bullets: [
      { bold: "Universal Interception", text: "Zero custom SDK code required in target agent" },
      { bold: "Automatic Redaction", text: "Masks bearer tokens, credentials, and API secrets" },
      { bold: "Stateful Sandbox", text: "Preserves environment isolation between evaluation trials" },
    ],
    codeSnippet: `// ARL Interception Proxy
const proxy = new ToolProxy({
  redactSecrets: true,
  targetAdapter: "mcp-stdio",
  sandbox: "customer-support:v1"
});`,
    badge: "STAGE 01 — INTERCEPT",
  },
  {
    id: "inject",
    name: "Inject",
    tagline: "8 Deterministic Chaos Faults + Timeout After Effect",
    description:
      "Inject realistic distributed systems failures using a seed-controlled pseudorandom generator. Simulate the nightmare failure: side effect succeeds in the backend database, but network response drops.",
    bullets: [
      { bold: "8 Chaos Fault Types", text: "Timeout, latency, 429 rate limit, 500/503 errors, connection reset, malformed JSON, empty response, duplicate response" },
      { bold: "Timeout After Effect", text: "Commits side effect then drops response to catch duplicate charge / refund loops" },
      { bold: "Seed Controlled", text: "100% deterministic reproduction with identical seed" },
    ],
    codeSnippet: `fault_plan:
  - tool: "refund.create"
    type: "timeout_after_effect"
    trigger:
      invocation_count: 1`,
    badge: "STAGE 02 — INJECT",
  },
  {
    id: "observe",
    name: "Observe",
    tagline: "Trajectory Capture & Turn / Token Budget Fencing",
    description:
      "Continuously monitors the agent's observable actions, state transitions, execution time, and tool call frequency. Automatically terminates infinite recursive loops before token budgets are exhausted.",
    bullets: [
      { bold: "Budget Fencing", text: "Strict ceilings on turns (5), tool calls (3), and token cost" },
      { bold: "Trajectory Tracing", text: "Captures full request/response event stream without private chain-of-thought" },
      { bold: "Cross-Tenant Guard", text: "Detects unauthorized tenant queries before state commit" },
    ],
    codeSnippet: `budgets:
  max_turns: 5
  max_tool_calls: 3
  max_cost_usd: 0.05
  wall_clock_seconds: 30`,
    badge: "STAGE 03 — OBSERVE",
  },
  {
    id: "verify",
    name: "Verify",
    tagline: "Deterministic Invariant Engine (Zero eval(), Zero LLM Hallucinations)",
    description:
      "Critical PASS/FAIL safety decisions must never depend on an LLM-as-a-judge. ARL evaluates state using 13 safe mathematical operators with safe JMESPath traversal.",
    bullets: [
      { bold: "13 Typed Operators", text: "eq, neq, lt, lte, gt, gte, exists, not_exists, count_eq, count_lte, count_gte, contains, not_contains" },
      { bold: "Zero eval()", text: "Safe traversal prevents code injection and arbitrary execution" },
      { bold: "Fail-Closed Semantics", text: "Any syntax or evaluation error results in ERROR, never PASS" },
    ],
    codeSnippet: `invariants:
  - id: single_refund_limit
    description: "Order must never be refunded twice"
    path: "$.refunds"
    operator: "count_lte"
    value: 1
    severity: "critical"`,
    badge: "STAGE 04 — VERIFY",
  },
  {
    id: "replay",
    name: "Replay",
    tagline: "Stable ARL-FAIL Records & One-Command Diagnostic Replay",
    description:
      "Every failure produces a stable identifier (e.g. ARL-FAIL-1042) and persists complete machine-readable evidence to disk (.arl/runs/<run-id>/) with instant replay capability.",
    bullets: [
      { bold: "Stable Failure Identifiers", text: "ARL-FAIL-XXXX provides traceable triage tokens" },
      { bold: "Diagnostic Replay", text: "agentlab replay ARL-FAIL-XXXX renders exact trajectory and first bad event" },
      { bold: "Deterministic Rerun", text: "agentlab rerun ARL-FAIL-XXXX re-executes with the exact same seed" },
    ],
    codeSnippet: `$ agentlab replay ARL-FAIL-1042
[DIAGNOSIS] Invariant Violation: $.refunds count_lte 1
Expected: <= 1
Observed: 2
First Bad Event: evt-04 (refund.create duplicate)
Reproduction: agentlab rerun ARL-FAIL-1042`,
    badge: "STAGE 05 — REPLAY",
  },
  {
    id: "gate",
    name: "Gate",
    tagline: "Fail-Closed CI Reliability Gate with Wilson 95% Confidence Intervals",
    description:
      "Integrate ARL directly into your GitHub Actions workflow. Evaluates critical invariant violations and regression deltas, failing the pull request if reliability regresses.",
    bullets: [
      { bold: "Fail-Closed Gate", text: "Critical invariant violations immediately exit with code 1" },
      { bold: "Wilson 95% CI", text: "Rigorous statistical confidence intervals on all pass rates" },
      { bold: "Regression Prevention", text: "Blocks deployment if agent reliability drops below baseline" },
    ],
    codeSnippet: `# .github/workflows/ci.yml
- name: Run ARL Reliability Gate
  run: agentlab test scenarios/ --gate --threshold 0.85`,
    badge: "STAGE 06 — GATE",
  },
];

const LOGO_PARTNERS = [
  { name: "LangGraph", desc: "Graph Agent Framework" },
  { name: "OpenAI Agents SDK", desc: "Tool Calling Agent" },
  { name: "Ollama", desc: "Local LLM Inference" },
  { name: "Career-Agents", desc: "167 Agent Benchmark" },
  { name: "Model Context Protocol", desc: "Anthropic MCP Server" },
  { name: "Claude Desktop", desc: "Native MCP Client" },
  { name: "Cursor IDE", desc: "MCP Tool Calling" },
  { name: "FastAPI", desc: "HTTP Agent Adapter" },
  { name: "PostgreSQL 16", desc: "Distributed Worker Leases" },
];

export default function LandingPage() {
  const [activeStageIndex, setActiveStageIndex] = useState(1); // Default to Inject
  const [simStep, setSimStep] = useState(0);
  const [simLogs, setSimLogs] = useState<string[]>([
    "[READY] ARL Chaos Simulator initialized on scenario '03-idempotent-refund-keys'.",
    "Click 'Simulate Timeout-After-Effect' to trigger the distributed failure test.",
  ]);

  const activeStage = LIFECYCLE_STAGES[activeStageIndex];

  const handleSimulate = () => {
    if (simStep === 0) {
      setSimStep(1);
      setSimLogs((prev) => [
        ...prev,
        "[AGENT] User asks: 'Refund Order #1042 for $49.99'",
        "[TOOL CALL] refund.create(order_id='1042', amount=49.99, idempotency_key='null')",
        "[BACKEND] Environment commits refund #ref-001 in ledger database.",
        "[CHAOS INJECTOR] Injected 'timeout_after_effect' -> Network response dropped!",
        "[AGENT EXCEPTION] ConnectionResetError: Server disconnected before response header.",
      ]);
    } else if (simStep === 1) {
      setSimStep(2);
      setSimLogs((prev) => [
        ...prev,
        "[AGENT RETRY] Agent assumes failure and issues un-idempotent retry #2...",
        "[TOOL CALL] refund.create(order_id='1042', amount=49.99)",
        "[BACKEND] Duplicate refund #ref-002 COMMITTED! World state has 2 refunds.",
        "[INVARIANT ENGINE] Evaluating Invariant 'single_refund_limit' on path '$.refunds'...",
        "[VIOLATION] Invariant 'single_refund_limit' FAILED (Expected count_lte 1, Observed 2). Severity: CRITICAL",
        "[FAILURE RECORD] Generated: ARL-FAIL-1042. Persisted evidence to .arl/runs/run-95ee-01/",
      ]);
    } else {
      setSimStep(0);
      setSimLogs([
        "[RESET] Sandbox state restored to clean initial snapshot.",
        "[READY] Ready for next chaos trial run.",
      ]);
    }
  };

  return (
    <div className="w-full min-h-screen bg-[#030710] text-slate-100 flex flex-col items-center">
      {/* ── Top Announcement Banner ── */}
      <div className="w-full bg-[#080f1e] border-b border-slate-800/80 py-2.5 px-4 text-center text-xs text-slate-300 flex items-center justify-center gap-2">
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
          v0.3 Live
        </span>
        <span>
          ARL Core Engine released with Typed Fault Models, Deterministic Invariants &amp; CI Gate!
        </span>
        <Link
          href="/dashboard"
          className="font-medium text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1 ml-1 underline decoration-cyan-500/40"
        >
          Explore Dashboard <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* ── Navbar ── */}
      <header className="w-full max-w-7xl mx-auto px-6 py-4 flex items-center justify-between sticky top-0 z-50 bg-[#030710]/85 backdrop-blur-xl border-b border-slate-900/80">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="relative w-9 h-9 rounded-xl overflow-hidden shadow-lg shadow-cyan-500/20 border border-cyan-500/40 group-hover:scale-105 transition-transform bg-[#080f1e] flex items-center justify-center">
              <Image
                src="/logo.png"
                alt="ARL Logo"
                width={36}
                height={36}
                className="object-cover"
                priority
              />
            </div>
            <span className="font-bold text-lg tracking-tight text-white flex items-center gap-2">
              Agent Reliability Lab
              <span className="text-[10px] font-mono tracking-widest px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60 uppercase">
                ARL
              </span>
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-sm text-slate-300 font-medium">
            <Link
              href="#lifecycle"
              className="hover:text-cyan-400 transition-colors"
            >
              Lifecycle
            </Link>
            <Link
              href="#faults"
              className="hover:text-cyan-400 transition-colors"
            >
              Chaos Faults
            </Link>
            <Link
              href="#invariants"
              className="hover:text-cyan-400 transition-colors"
            >
              Invariants
            </Link>
            <Link
              href="#playground"
              className="hover:text-cyan-400 transition-colors"
            >
              Live Demo
            </Link>
            <Link
              href="/scenarios"
              className="hover:text-cyan-400 transition-colors"
            >
              25 Scenarios
            </Link>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="https://github.com/karthikrshet/agent-reliability"
            target="_blank"
            className="lc-button-secondary text-xs px-3.5 py-2 hidden sm:inline-flex"
          >
            <Github className="w-3.5 h-3.5" />
            GitHub
          </Link>
          <Link href="/dashboard" className="lc-button-primary text-xs px-4 py-2">
            Launch Dashboard
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </header>

      {/* ── Hero Section ── */}
      <section className="w-full max-w-7xl mx-auto px-6 pt-20 pb-16 flex flex-col items-center text-center relative">
        {/* Subtle radial lighting */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-cyan-500/10 blur-[130px] rounded-full pointer-events-none" />

        {/* Rolling Header Link */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/90 border border-cyan-500/30 text-xs text-slate-300 mb-8 backdrop-blur-md">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="font-mono text-cyan-300">ARL Core Engine</span>
          <span className="text-slate-500">•</span>
          <span>Reliability Engineering for Autonomous AI</span>
        </div>

        <h1 className="text-4xl sm:text-6xl md:text-7xl font-bold tracking-tight text-white max-w-4xl leading-[1.08] mb-6">
          Meet Agent Reliability Lab.{" "}
          <span className="text-cyan-malibu glow-text block mt-2">
            Break your AI agent before production does.
          </span>
        </h1>

        <p className="text-base sm:text-xl text-slate-400 max-w-2xl mb-10 leading-relaxed">
          The open-source chaos engineering harness for tool-using AI agents.
          Intercept tool calls, inject deterministic faults, evaluate stateful
          invariants (zero eval, zero hallucinations), and enforce fail-closed CI gates.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4 mb-16">
          <Link
            href="/dashboard"
            className="lc-button-primary text-sm px-6 py-3 font-semibold shadow-lg shadow-white/10"
          >
            Start Testing
            <ArrowUpRight className="w-4 h-4" />
          </Link>
          <Link
            href="#playground"
            className="lc-button-secondary text-sm px-6 py-3 font-semibold"
          >
            <Play className="w-4 h-4 text-cyan-400" />
            Watch Failure Simulation
          </Link>
          <Link
            href="https://github.com/karthikrshet/agent-reliability"
            target="_blank"
            className="lc-button-secondary text-sm px-5 py-3 text-slate-300"
          >
            <BookOpen className="w-4 h-4" />
            Specification
          </Link>
        </div>

        {/* Real Verified Metrics Badge Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-4xl w-full border-t border-b border-slate-900/90 py-6 my-4">
          <div className="flex flex-col items-center">
            <span className="font-mono text-2xl sm:text-3xl font-bold text-white">
              185
            </span>
            <span className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-mono">
              Passed Tests
            </span>
          </div>
          <div className="flex flex-col items-center">
            <span className="font-mono text-2xl sm:text-3xl font-bold text-cyan-400">
              85.3%
            </span>
            <span className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-mono">
              Code Coverage
            </span>
          </div>
          <div className="flex flex-col items-center">
            <span className="font-mono text-2xl sm:text-3xl font-bold text-emerald-400">
              13
            </span>
            <span className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-mono">
              Safe Invariant Operators
            </span>
          </div>
          <div className="flex flex-col items-center">
            <span className="font-mono text-2xl sm:text-3xl font-bold text-indigo-400">
              0
            </span>
            <span className="text-xs text-slate-400 mt-1 uppercase tracking-wider font-mono">
              eval() Calls Allowed
            </span>
          </div>
        </div>
      </section>

      {/* ── Partner & Framework Logos Bar ── */}
      <section className="w-full bg-[#02050b] border-y border-slate-900 py-10 px-6">
        <div className="max-w-7xl mx-auto">
          <p className="text-center text-xs font-mono uppercase tracking-widest text-slate-500 mb-8">
            Engineered for Autonomous Agent Frameworks &amp; Protocols
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-4 items-center justify-center">
            {LOGO_PARTNERS.map((partner) => (
              <div
                key={partner.name}
                className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/40 hover:border-cyan-500/40 transition-all text-center group cursor-default"
              >
                <div className="text-xs font-semibold text-slate-300 group-hover:text-cyan-300 transition-colors truncate">
                  {partner.name}
                </div>
                <div className="text-[10px] text-slate-500 truncate mt-0.5">
                  {partner.desc}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Interactive Lifecycle Section ── */}
      <section id="lifecycle" className="w-full max-w-7xl mx-auto px-6 py-24">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="font-mono text-xs text-cyan-400 uppercase tracking-widest bg-cyan-950/80 px-3 py-1 rounded-full border border-cyan-800/60">
            End-to-End Reliability Loop
          </span>
          <h2 className="text-3xl sm:text-5xl font-bold text-white tracking-tight mt-4 mb-4">
            Accelerating the Agent Reliability Lifecycle
          </h2>
          <p className="text-slate-400 text-sm sm:text-base">
            Six synchronized phases designed to guarantee that when the systems around your agent break, your business doesn&apos;t.
          </p>
        </div>

        {/* Lifecycle Tabs */}
        <div className="flex flex-wrap items-center justify-center gap-2 mb-12">
          {LIFECYCLE_STAGES.map((stage, idx) => (
            <button
              key={stage.id}
              onClick={() => setActiveStageIndex(idx)}
              className={`px-4 py-2 rounded-full text-xs font-mono tracking-wide transition-all border ${
                activeStageIndex === idx
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-md shadow-cyan-500/20"
                  : "bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-200 hover:border-slate-700"
              }`}
            >
              0{idx + 1}. {stage.name}
            </button>
          ))}
        </div>

        {/* Active Stage Detail Panel */}
        <div className="glass-panel rounded-2xl p-8 lg:p-12 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center border border-cyan-500/20 shadow-2xl shadow-cyan-950/20">
          <div className="lg:col-span-6 space-y-6">
            <span className="inline-block px-2.5 py-1 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/80 text-xs font-mono font-bold">
              {activeStage.badge}
            </span>
            <h3 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              {activeStage.tagline}
            </h3>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
              {activeStage.description}
            </p>

            <div className="space-y-3 pt-2">
              {activeStage.bullets.map((b, i) => (
                <div key={i} className="flex items-start gap-3 text-sm">
                  <div className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0 mt-0.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <strong className="text-white">{b.bold}</strong>:{" "}
                    <span className="text-slate-400">{b.text}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-4 flex items-center gap-4">
              <Link
                href="/dashboard"
                className="lc-button-primary text-xs px-5 py-2.5"
              >
                Inspect in Dashboard
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
              <Link
                href="/scenarios"
                className="lc-button-secondary text-xs px-4 py-2.5"
              >
                View Scenarios
              </Link>
            </div>
          </div>

          <div className="lg:col-span-6">
            <div className="rounded-xl bg-[#040812] border border-slate-800/80 p-5 font-mono text-xs overflow-x-auto shadow-inner">
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800 text-slate-500 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                  <span className="ml-2 text-slate-400 font-sans">arl-engine.yaml</span>
                </div>
                <span>YAML / Contract</span>
              </div>
              <pre className="text-cyan-200/90 leading-relaxed">
                <code>{activeStage.codeSnippet}</code>
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* ── Interactive Live Chaos Playground ── */}
      <section id="playground" className="w-full bg-[#02050b] border-y border-slate-900 py-24 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <span className="font-mono text-xs text-amber-400 uppercase tracking-widest bg-amber-950/60 px-3 py-1 rounded-full border border-amber-800/60">
              Interactive Chaos Simulator
            </span>
            <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mt-4 mb-3">
              The &ldquo;Timeout-After-Effect&rdquo; Attack
            </h2>
            <p className="text-slate-400 text-sm">
              Watch how an agent mistakenly double-refunds an order when a network connection drops after backend commit.
            </p>
          </div>

          <div className="glass-panel rounded-2xl p-6 sm:p-8 max-w-4xl mx-auto border border-slate-800/80">
            {/* Terminal Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 mb-4 border-b border-slate-800">
              <div className="flex items-center gap-2 font-mono text-xs text-slate-400">
                <Terminal className="w-4 h-4 text-cyan-400" />
                <span>agentlab simulation --scenario refund-timeout --seed 42</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSimulate}
                  className={`text-xs font-medium px-4 py-2 rounded-lg flex items-center gap-2 transition-all ${
                    simStep === 0
                      ? "bg-amber-500 text-slate-950 hover:bg-amber-400 font-semibold"
                      : simStep === 1
                      ? "bg-red-600 text-white hover:bg-red-500 font-semibold animate-pulse"
                      : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                  }`}
                >
                  {simStep === 0 ? (
                    <>
                      <Zap className="w-3.5 h-3.5" />
                      1. Inject Timeout-After-Effect
                    </>
                  ) : simStep === 1 ? (
                    <>
                      <ShieldAlert className="w-3.5 h-3.5" />
                      2. Simulate Retrying Agent
                    </>
                  ) : (
                    <>
                      <RotateCcw className="w-3.5 h-3.5" />
                      Reset Sandbox
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Terminal Output Body */}
            <div className="bg-[#03060f] rounded-xl p-5 font-mono text-xs space-y-2.5 min-h-[220px] max-h-[340px] overflow-y-auto border border-slate-900">
              {simLogs.map((log, index) => {
                const isViolation = log.includes("[VIOLATION]") || log.includes("[FAILURE RECORD]");
                const isChaos = log.includes("[CHAOS INJECTOR]") || log.includes("[AGENT EXCEPTION]");
                const isAgent = log.includes("[AGENT]") || log.includes("[TOOL CALL]");
                return (
                  <div
                    key={index}
                    className={`leading-relaxed ${
                      isViolation
                        ? "text-red-400 font-semibold bg-red-950/30 p-1.5 rounded border border-red-900/50"
                        : isChaos
                        ? "text-amber-300 bg-amber-950/20 p-1 rounded"
                        : isAgent
                        ? "text-cyan-300"
                        : "text-slate-400"
                    }`}
                  >
                    {log}
                  </div>
                );
              })}
            </div>

            {/* Replay Command Bar */}
            {simStep === 2 && (
              <div className="mt-4 p-3 rounded-lg bg-red-950/40 border border-red-800/60 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-red-200">
                <div className="flex items-center gap-2">
                  <AlertOctagon className="w-4 h-4 text-red-400 shrink-0" />
                  <span>
                    Deterministic Invariant violated: <strong>single_refund_limit</strong> (count_lte: 1).
                  </span>
                </div>
                <div className="font-mono bg-black/60 px-3 py-1.5 rounded text-cyan-300 border border-slate-800">
                  agentlab replay ARL-FAIL-1042
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Three Pillars Modular Architecture ── */}
      <section id="architecture" className="w-full max-w-7xl mx-auto px-6 py-24">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="font-mono text-xs text-indigo-400 uppercase tracking-widest bg-indigo-950/80 px-3 py-1 rounded-full border border-indigo-800/60">
            Composable Core Modules
          </span>
          <h2 className="text-3xl sm:text-5xl font-bold text-white tracking-tight mt-4 mb-4">
            Built as Infrastructure, Not a Wrapper
          </h2>
          <p className="text-slate-400 text-sm sm:text-base">
            Every layer of ARL is a typed, standalone package built for distributed systems rigor.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="glass-panel rounded-2xl p-8 border border-slate-800/80 glass-panel-hover flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 flex items-center justify-center mb-6">
                <Zap className="w-5 h-5" />
              </div>
              <span className="text-xs font-mono text-cyan-400 uppercase tracking-wider">
                packages/fault-engine
              </span>
              <h3 className="text-xl font-bold text-white mt-2 mb-3">
                Deterministic Chaos Engine
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Seeded PRNG fault scheduling guarantees identical fault injection paths across repeated trials. Injects network drops, rate limits, corrupt JSON, and unhandled 500s.
              </p>
            </div>
            <div className="pt-4 border-t border-slate-800/60 font-mono text-xs text-slate-400">
              <code>8 Core Faults + Seed Control</code>
            </div>
          </div>

          {/* Card 2 */}
          <div className="glass-panel rounded-2xl p-8 border border-slate-800/80 glass-panel-hover flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mb-6">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <span className="text-xs font-mono text-emerald-400 uppercase tracking-wider">
                packages/grading-engine
              </span>
              <h3 className="text-xl font-bold text-white mt-2 mb-3">
                13 Safe Invariant Operators
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Zero arbitrary string eval(). Safe JMESPath navigation with typed relational predicates. Eliminates flaky LLM-as-a-judge hallucinations on factual invariants.
              </p>
            </div>
            <div className="pt-4 border-t border-slate-800/60 font-mono text-xs text-slate-400">
              <code>Zero eval() • Fail-Closed Rules</code>
            </div>
          </div>

          {/* Card 3 */}
          <div className="glass-panel rounded-2xl p-8 border border-slate-800/80 glass-panel-hover flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center mb-6">
                <Lock className="w-5 h-5" />
              </div>
              <span className="text-xs font-mono text-indigo-400 uppercase tracking-wider">
                packages/evidence
              </span>
              <h3 className="text-xl font-bold text-white mt-2 mb-3">
                Tamper-Evident SHA-256 Chain
              </h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Every event, state transition, and tool call is recorded into an append-only cryptographic hash chain. Persists machine-readable artifacts for instant failure replay.
              </p>
            </div>
            <div className="pt-4 border-t border-slate-800/60 font-mono text-xs text-slate-400">
              <code>SHA-256 Ledger • Stable Replay IDs</code>
            </div>
          </div>
        </div>
      </section>

      {/* ── Career-Agents Benchmark Highlight ── */}
      <section className="w-full bg-[#040814] border-y border-slate-900 py-20 px-6">
        <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-center justify-between gap-12">
          <div className="max-w-2xl space-y-6">
            <span className="px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 text-xs font-mono">
              REAL BENCHMARK TARGET
            </span>
            <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
              Tested on Career-Agents (167 Autonomous Agents)
            </h2>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
              ARL validates real-world multi-agent systems. The Career-Agents verification suite tests 167 registered agents, Model Context Protocol handshakes, tool call routing, and malformed input fallback resilience.
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-2 font-mono text-xs">
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                <div className="text-cyan-400 font-bold text-lg">167</div>
                <div className="text-slate-400">Registered Agents</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                <div className="text-emerald-400 font-bold text-lg">5 / 5</div>
                <div className="text-slate-400">MCP Tests Passed</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                <div className="text-indigo-400 font-bold text-lg">-32601</div>
                <div className="text-slate-400">JSON-RPC Veto Bound</div>
              </div>
            </div>
          </div>

          <div className="w-full lg:w-auto bg-[#03060e] border border-slate-800 p-6 rounded-2xl shadow-xl font-mono text-xs text-slate-300 max-w-md">
            <div className="text-slate-500 pb-3 border-b border-slate-800 flex items-center justify-between">
              <span>pytest output</span>
              <span className="text-emerald-400">PASSED</span>
            </div>
            <pre className="py-3 text-[11px] leading-relaxed text-slate-400">
              <code>{`tests/test_career_agents_reliability.py::
  test_01_workspace_integrity ... PASSED
  test_02_agent_registry_count ... PASSED
  test_03_mcp_tools_list_spec ... PASSED
  test_04_mcp_tool_execution ... PASSED
  test_05_malformed_input_resilience ... PASSED

5 passed in 3.89s (ARL_CAREER_AGENTS_ROOT)`}</code>
            </pre>
            <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-500">
              Supports graceful skip when external workspace is absent.
            </div>
          </div>
        </div>
      </section>

      {/* ── CLI Quickstart Section ── */}
      <section className="w-full max-w-7xl mx-auto px-6 py-20">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl font-bold text-white tracking-tight mb-3">
            Developer-First CLI Experience
          </h2>
          <p className="text-slate-400 text-sm">
            Everything in ARL runs from a clean terminal command. Zero bloat, instant feedback.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto font-mono text-xs">
          <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800">
            <span className="text-slate-500 block mb-2 font-sans text-xs">
              1. Run chaos evaluation with fail-closed CI gate
            </span>
            <code className="text-cyan-300 block bg-[#03060f] p-3 rounded border border-slate-800/80">
              agentlab test scenarios/ --gate --threshold 0.85
            </code>
          </div>

          <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800">
            <span className="text-slate-500 block mb-2 font-sans text-xs">
              2. Replay failure from persisted evidence
            </span>
            <code className="text-cyan-300 block bg-[#03060f] p-3 rounded border border-slate-800/80">
              agentlab replay ARL-FAIL-1042
            </code>
          </div>

          <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800">
            <span className="text-slate-500 block mb-2 font-sans text-xs">
              3. Deterministically rerun with identical seed
            </span>
            <code className="text-cyan-300 block bg-[#03060f] p-3 rounded border border-slate-800/80">
              agentlab rerun ARL-FAIL-1042
            </code>
          </div>

          <div className="p-5 rounded-xl bg-slate-900/40 border border-slate-800">
            <span className="text-slate-500 block mb-2 font-sans text-xs">
              4. Export auditor-ready Markdown report
            </span>
            <code className="text-cyan-300 block bg-[#03060f] p-3 rounded border border-slate-800/80">
              agentlab report latest --format markdown
            </code>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="w-full bg-[#020409] border-t border-slate-900/90 py-16 px-6 text-sm text-slate-500">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg overflow-hidden border border-slate-800 bg-[#080f1e] flex items-center justify-center">
              <Image src="/logo.png" alt="ARL" width={28} height={28} />
            </div>
            <span className="font-semibold text-slate-300">
              Agent Reliability Lab
            </span>
            <span className="text-xs text-slate-600">
              © 2026 Karthik Rajesh Shet. Released under MIT License.
            </span>
          </div>

          <div className="flex items-center gap-6 text-xs text-slate-400">
            <Link href="/dashboard" className="hover:text-cyan-400 transition-colors">
              Dashboard
            </Link>
            <Link href="/scenarios" className="hover:text-cyan-400 transition-colors">
              Scenarios
            </Link>
            <Link href="/runs" className="hover:text-cyan-400 transition-colors">
              Runs
            </Link>
            <Link href="/reports" className="hover:text-cyan-400 transition-colors">
              Audit Reports
            </Link>
            <Link
              href="https://github.com/karthikrshet/agent-reliability"
              target="_blank"
              className="hover:text-cyan-400 transition-colors inline-flex items-center gap-1"
            >
              GitHub <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
