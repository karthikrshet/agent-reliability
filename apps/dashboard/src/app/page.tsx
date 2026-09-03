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
  Linkedin,
  Twitter,
  Youtube,
  Send,
} from "lucide-react";

const LIFECYCLE_STAGES = [
  {
    id: "intercept",
    name: "Intercept",
    phaseTitle: "Intercept",
    tagline: "Universal Tool Call Proxy & Secret Redaction",
    highlightDesc: "Intercept all outgoing tool requests without modifying a single line of agent code. Recursively strip credentials before logging.",
    bullets: [
      "Zero custom SDK required in target agent",
      "Automatic redaction of Authorization, API keys, and session cookies",
      "Sandbox state isolation between successive trials",
    ],
    primaryBtn: "Tool Proxy Spec",
    secondaryBtn: "Redaction Rules",
  },
  {
    id: "inject",
    name: "Inject",
    phaseTitle: "Inject",
    tagline: "8 Deterministic Chaos Faults + Timeout-After-Effect",
    highlightDesc: "Break your autonomous agents before production does. Inject realistic distributed failures with 100% seeded determinism.",
    bullets: [
      "Simulate the nightmare timeout-after-effect (side effect succeeds, response drops)",
      "Network latency, 429 rate limits, 500/503 crashes, and malformed JSON",
      "Seeded PRNG guarantees bit-for-bit identical failure paths",
    ],
    primaryBtn: "Chaos Engine",
    secondaryBtn: "Fault Matrix",
  },
  {
    id: "observe",
    name: "Observe",
    phaseTitle: "Observe",
    tagline: "Stateful Trajectory Capture & Strict Budget Fencing",
    highlightDesc: "Track state transitions, tool call count, and token budgets in real time. Automatically kill infinite runaway loops.",
    bullets: [
      "Strict enforcement on turn count, tool calls, and execution timeouts",
      "Captures full tool request/response stream without private chain-of-thought",
      "Cross-tenant boundary fence prevents unauthorized data exfiltration",
    ],
    primaryBtn: "Observability",
    secondaryBtn: "Budget Specs",
  },
  {
    id: "verify",
    name: "Verify",
    phaseTitle: "Verify",
    tagline: "13 Deterministic Invariant Operators (Zero eval, Zero Hallucinations)",
    highlightDesc: "Validate behavior before you ship. Turn traces into deterministic invariants and verify every step without LLM-as-a-judge.",
    bullets: [
      "13 safe relational operators (eq, count_lte, exists, contains, etc.)",
      "Safe JMESPath AST traversal prevents arbitrary string eval() execution",
      "Fail-closed evaluation semantics: errors result in ERROR, never PASS",
    ],
    primaryBtn: "Invariants AST",
    secondaryBtn: "Rule Catalog",
  },
  {
    id: "replay",
    name: "Replay",
    phaseTitle: "Replay",
    tagline: "Stable ARL-FAIL-XXXX Records & One-Command Replay",
    highlightDesc: "Turn flaky production bugs into reproducible local tests. Replay exact failure events with a single CLI command.",
    bullets: [
      "Stable failure identifier (e.g. ARL-FAIL-1042) for immediate triage",
      "agentlab replay ARL-FAIL-1042 renders step-by-step diagnostic diff",
      "agentlab rerun ARL-FAIL-1042 executes with the identical seed",
    ],
    primaryBtn: "CLI Replay Docs",
    secondaryBtn: "Evidence Ledger",
  },
  {
    id: "gate",
    name: "Gate",
    phaseTitle: "Gate",
    tagline: "Fail-Closed CI Reliability Gate with Wilson 95% CI",
    highlightDesc: "Block agent regressions in pull requests before they reach production. Statistical confidence bounds on all pass rates.",
    bullets: [
      "Fail-closed exit code 1 on any critical invariant violation",
      "Wilson score 95% confidence intervals on empirical pass rates",
      "Native GitHub Actions workflow integration via single CLI command",
    ],
    primaryBtn: "CI Gate Guide",
    secondaryBtn: "GitHub Action",
  },
];

const ROW1_LOGOS = [
  { name: "LangGraph", desc: "Graph Agent Framework" },
  { name: "OpenAI SDK", desc: "Tool Calling Agent" },
  { name: "Model Context Protocol", desc: "Anthropic MCP Stdio" },
  { name: "Career-Agents", desc: "167 Agent Benchmark" },
  { name: "Claude Desktop", desc: "Native MCP Client" },
  { name: "Cursor IDE", desc: "MCP Tool Calling" },
  { name: "Ollama", desc: "Local LLM Inference" },
  { name: "FastAPI", desc: "HTTP Agent Adapter" },
];

const ROW2_LOGOS = [
  { name: "PostgreSQL 16", desc: "Distributed Leases" },
  { name: "vLLM", desc: "High-Throughput Serving" },
  { name: "CrewAI", desc: "Multi-Agent System" },
  { name: "AutoGen", desc: "Conversational Agents" },
  { name: "DSPy", desc: "Algorithmic Prompts" },
  { name: "LlamaIndex", desc: "RAG & Workflows" },
  { name: "Docker", desc: "Isolated Sandbox" },
  { name: "GitHub Actions", desc: "Fail-Closed CI Gate" },
];

export default function LandingPage() {
  const [activeStageIndex, setActiveStageIndex] = useState(1); // Default to Inject / Test
  const [simStep, setSimStep] = useState(0);
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);
  const [simLogs, setSimLogs] = useState<string[]>([
    "[READY] ARL Chaos Simulator initialized on scenario '03-idempotent-refund-keys'.",
    "Click 'Simulate Timeout-After-Effect' to trigger the distributed failure test.",
  ]);

  const [isPaused, setIsPaused] = useState(false);

  React.useEffect(() => {
    if (isPaused) return;
    const timer = setInterval(() => {
      setActiveStageIndex((prev) => (prev + 1) % LIFECYCLE_STAGES.length);
    }, 4500);
    return () => clearInterval(timer);
  }, [isPaused]);

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

  const handleSubscribe = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      setSubscribed(true);
      setTimeout(() => setSubscribed(false), 4000);
      setEmail("");
    }
  };

  return (
    <div className="w-full min-h-screen bg-[#030710] text-slate-100 flex flex-col items-center selection:bg-cyan-500/20 selection:text-cyan-200">
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
            <Link href="#lifecycle" className="hover:text-cyan-400 transition-colors">
              Lifecycle
            </Link>
            <Link href="#modules" className="hover:text-cyan-400 transition-colors">
              Engines
            </Link>
            <Link href="#playground" className="hover:text-cyan-400 transition-colors">
              Live Demo
            </Link>
            <Link href="/scenarios" className="hover:text-cyan-400 transition-colors">
              25 Scenarios
            </Link>
            <Link href="/reports" className="hover:text-cyan-400 transition-colors">
              Evidence
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

      {/* ── Hero Section with Cyber Core Background Artwork ── */}
      <section className="w-full relative min-h-[680px] flex flex-col items-center justify-center text-center px-6 overflow-hidden border-b border-slate-900">
        {/* Cyber Core Fault Stress Backdrop */}
        <div className="absolute inset-0 z-0 opacity-40 pointer-events-none">
          <Image
            src="/images/hero-cyber-core.jpg"
            alt="ARL Cybernetic Neural Core and Holographic Shield Forcefield"
            fill
            className="object-cover object-center"
            priority
          />
          {/* Dark Gradients to ensure text readability */}
          <div className="absolute inset-0 bg-gradient-to-t from-[#030710] via-[#030710]/40 to-[#030710]/90" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_70%_at_50%_45%,rgba(3,7,16,0.3),rgba(3,7,16,0.95))]" />
        </div>

        {/* Hero Foreground Content */}
        <div className="relative z-10 max-w-4xl mx-auto pt-16 pb-12 flex flex-col items-center">
          {/* Rolling Header Link */}
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#080f1e]/90 border border-cyan-500/30 text-xs text-slate-300 mb-8 backdrop-blur-md hover:border-cyan-400 transition-colors shadow-lg shadow-cyan-950/40"
          >
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="font-mono text-cyan-300">Meet ARL Engine</span>
            <span className="text-slate-600">•</span>
            <span className="text-slate-300">Reliability Engineering for Autonomous AI</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-cyan-400 ml-0.5" />
          </Link>

          <h1 className="text-4xl sm:text-6xl md:text-7xl font-bold tracking-tight text-white max-w-4xl leading-[1.08] mb-6">
            Meet Agent Reliability Lab.{" "}
            <span className="text-cyan-malibu glow-text block mt-2">
              Break your AI agent before production does.
            </span>
          </h1>

          <p className="text-base sm:text-xl text-slate-300 max-w-2xl mb-10 leading-relaxed drop-shadow-md">
            The open-source chaos engineering harness for tool-using AI agents.
            Intercept tool calls, inject deterministic faults, evaluate stateful
            invariants (zero eval, zero hallucinations), and enforce fail-closed CI gates.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 mb-14">
            <Link
              href="/dashboard"
              className="lc-button-primary text-sm px-6 py-3 font-semibold shadow-xl shadow-white/10"
            >
              Start building
              <ArrowUpRight className="w-4 h-4" />
            </Link>
            <Link
              href="#playground"
              className="lc-button-secondary text-sm px-6 py-3 font-semibold backdrop-blur-md"
            >
              <Play className="w-4 h-4 text-cyan-400" />
              Watch Failure Simulation
            </Link>
          </div>

          {/* Real Verified Proof Metrics Row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-3xl w-full border-t border-b border-slate-800/80 py-5 backdrop-blur-sm bg-[#030710]/40 rounded-xl">
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
        </div>
      </section>

      {/* ── Continuous Marquee Logo Scroller ── */}
      <section className="w-full bg-[#02050b] border-b border-slate-900 py-10 overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 mb-4">
          <p className="text-center text-xs font-mono uppercase tracking-widest text-slate-500">
            Supported Agent Frameworks, Runtimes &amp; Infrastructure
          </p>
        </div>

        {/* Row 1: Forward Marquee */}
        <div className="w-full overflow-hidden flex py-2">
          <div className="animate-marquee flex gap-4">
            {[...ROW1_LOGOS, ...ROW1_LOGOS].map((partner, i) => (
              <div
                key={i}
                className="px-5 py-3 rounded-xl bg-[#080f1e]/80 border border-slate-800/80 hover:border-cyan-500/50 hover:bg-[#0c152a] transition-all flex items-center gap-3 shrink-0 shadow-sm group cursor-default"
              >
                <div className="w-2 h-2 rounded-full bg-cyan-400/80 group-hover:scale-125 transition-transform shadow-sm shadow-cyan-400/50" />
                <span className="text-xs font-semibold text-slate-200 group-hover:text-cyan-300 transition-colors">{partner.name}</span>
                <span className="text-[10px] text-slate-500 font-mono">({partner.desc})</span>
              </div>
            ))}
          </div>
        </div>

        {/* Row 2: Reverse Marquee */}
        <div className="w-full overflow-hidden flex py-2">
          <div className="animate-marquee-reverse flex gap-4">
            {[...ROW2_LOGOS, ...ROW2_LOGOS].map((partner, i) => (
              <div
                key={i}
                className="px-5 py-3 rounded-xl bg-[#080f1e]/50 border border-slate-800/60 hover:border-cyan-500/50 hover:bg-[#0c152a] transition-all flex items-center gap-3 shrink-0 shadow-sm group cursor-default"
              >
                <div className="w-2 h-2 rounded-full bg-indigo-400/80 group-hover:scale-125 transition-transform shadow-sm shadow-indigo-400/50" />
                <span className="text-xs font-semibold text-slate-300 group-hover:text-cyan-300 transition-colors">{partner.name}</span>
                <span className="text-[10px] text-slate-500 font-mono">({partner.desc})</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Interactive Lifecycle Section with Auto-Advancing Wheel ── */}
      <section
        id="lifecycle"
        className="w-full max-w-7xl mx-auto px-6 py-24"
        onMouseEnter={() => setIsPaused(true)}
        onMouseLeave={() => setIsPaused(false)}
      >
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

        {/* Lifecycle Interactive Grid: Radial Arc on Left, Content in Center, Trace UI on Right */}
        <div className="glass-panel rounded-2xl p-6 sm:p-10 border border-cyan-500/20 shadow-2xl grid grid-cols-1 lg:grid-cols-12 gap-8 items-center relative overflow-hidden">
          {/* Subtle Ambient Radial Lighting */}
          <div className="absolute top-0 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

          {/* Left 3 cols: Orbit Stepper with Progress Bar */}
          <div className="lg:col-span-3 flex flex-row lg:flex-col justify-center gap-2.5 overflow-x-auto pb-4 lg:pb-0">
            {LIFECYCLE_STAGES.map((stage, idx) => {
              const isActive = activeStageIndex === idx;
              return (
                <button
                  key={stage.id}
                  onClick={() => setActiveStageIndex(idx)}
                  className={`relative flex items-center justify-between px-4 py-3.5 rounded-xl text-xs font-mono tracking-wide transition-all text-left border overflow-hidden shrink-0 ${
                    isActive
                      ? "bg-cyan-500/20 text-cyan-300 border-cyan-400 shadow-md shadow-cyan-500/20 translate-x-1"
                      : "bg-[#040812]/80 text-slate-400 border-slate-800 hover:text-slate-200 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center gap-3 relative z-10">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        isActive ? "bg-cyan-400 animate-pulse" : "bg-slate-600"
                      }`}
                    />
                    <span className="font-bold text-slate-200">
                      0{idx + 1}. {stage.name}
                    </span>
                  </div>

                  {/* Auto-cycling progress bar indicator on active tab */}
                  {isActive && (
                    <div className="absolute bottom-0 left-0 h-0.5 bg-gradient-to-r from-cyan-400 to-emerald-400 animate-progress-fill" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Active Phase Content (Center 4 cols) */}
          <div className="lg:col-span-4 space-y-5">
            <div>
              <span className="text-xs font-mono text-cyan-400 uppercase tracking-widest font-semibold">
                PHASE 0{activeStageIndex + 1}
              </span>
              <h3 className="text-3xl font-bold text-white tracking-tight mt-1">
                {activeStage.phaseTitle}
              </h3>
            </div>

            <p className="text-slate-300 text-sm leading-relaxed font-medium">
              {activeStage.highlightDesc}
            </p>

            <div className="space-y-2.5 pt-1">
              {activeStage.bullets.map((bullet, i) => (
                <div key={i} className="flex items-start gap-2.5 text-xs text-slate-400">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0 mt-1.5" />
                  <span>{bullet}</span>
                </div>
              ))}
            </div>

            <div className="pt-3 flex items-center gap-3">
              <Link
                href="/dashboard"
                className="lc-button-secondary text-xs px-4 py-2 text-cyan-300 border-cyan-500/30"
              >
                {activeStage.primaryBtn}
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
              <Link
                href="/scenarios"
                className="lc-button-secondary text-xs px-4 py-2"
              >
                {activeStage.secondaryBtn}
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Trace Inspector UI Frame (Right 5 cols) */}
          <div className="lg:col-span-5 relative">
            <div className="rounded-xl overflow-hidden border border-cyan-500/30 shadow-2xl shadow-cyan-950/40 group relative">
              <Image
                src="/images/trace-inspector.jpg"
                alt="ARL Trace Waterfall Inspector UI"
                width={640}
                height={360}
                className="w-full object-cover group-hover:scale-[1.02] transition-transform duration-500"
              />
              <div className="absolute top-3 right-3 px-2.5 py-1 rounded-full bg-[#030710]/80 backdrop-blur-md border border-cyan-500/40 text-[10px] font-mono text-cyan-300">
                Trace Inspector • Live View
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Three Architecture Diagram Cards (Screenshot 2 Exact Re-creation) ── */}
      <section id="modules" className="w-full max-w-7xl mx-auto px-6 py-20 border-t border-slate-900">
        <div className="text-center max-w-3xl mx-auto mb-14">
          <span className="font-mono text-xs text-cyan-400 uppercase tracking-widest bg-cyan-950/80 px-3 py-1 rounded-full border border-cyan-800/60">
            Composable Core Frameworks
          </span>
          <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight mt-4 mb-3">
            Modular Reliability Architecture
          </h2>
          <p className="text-slate-400 text-sm">
            Standalone, typed packages built with distributed systems rigor.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1: Fault Engine */}
          <div className="glass-panel rounded-2xl p-5 border border-slate-800/80 glass-panel-hover flex flex-col justify-between">
            <div>
              <div className="rounded-xl overflow-hidden border border-slate-800/80 mb-5 relative aspect-video bg-[#080f1e]">
                <Image
                  src="/images/diagram-fault-engine.jpg"
                  alt="Fault Engine Architecture Diagram"
                  fill
                  className="object-cover"
                />
              </div>
              <div className="flex items-center gap-2 mb-2">
                <span className="font-mono text-xs text-cyan-400 font-semibold">
                  arl.fault_engine
                </span>
              </div>
              <h3 className="text-lg font-bold text-white mb-2 leading-snug">
                Deterministic chaos injection with seeded PRNG
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                For simulating network timeouts, 429 rate limits, unhandled 500s, and the duplicate-inducing timeout-after-effect.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-slate-800/60 flex items-center justify-between text-xs text-cyan-400">
              <Link href="/scenarios" className="hover:underline inline-flex items-center gap-1">
                Explore fault-engine <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Card 2: Grading Engine */}
          <div className="glass-panel rounded-2xl p-5 border border-slate-800/80 glass-panel-hover flex flex-col justify-between">
            <div>
              <div className="rounded-xl overflow-hidden border border-slate-800/80 mb-5 relative aspect-video bg-[#080f1e]">
                <Image
                  src="/images/diagram-grading-engine.jpg"
                  alt="Grading Engine Architecture Diagram"
                  fill
                  className="object-cover"
                />
              </div>
              <div className="flex items-center gap-2 mb-2">
                <span className="font-mono text-xs text-emerald-400 font-semibold">
                  arl.grading_engine
                </span>
              </div>
              <h3 className="text-lg font-bold text-white mb-2 leading-snug">
                13 typed relational invariants (zero eval)
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                For safe JMESPath state traversal and mathematical invariants without flaky LLM-as-a-judge hallucinations.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-slate-800/60 flex items-center justify-between text-xs text-cyan-400">
              <Link href="/dashboard" className="hover:underline inline-flex items-center gap-1">
                Explore grading-engine <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Card 3: Evidence Ledger */}
          <div className="glass-panel rounded-2xl p-5 border border-slate-800/80 glass-panel-hover flex flex-col justify-between">
            <div>
              <div className="rounded-xl overflow-hidden border border-slate-800/80 mb-5 relative aspect-video bg-[#080f1e]">
                <Image
                  src="/images/diagram-evidence-ledger.jpg"
                  alt="Evidence Ledger Architecture Diagram"
                  fill
                  className="object-cover"
                />
              </div>
              <div className="flex items-center gap-2 mb-2">
                <span className="font-mono text-xs text-indigo-400 font-semibold">
                  arl.evidence
                </span>
              </div>
              <h3 className="text-lg font-bold text-white mb-2 leading-snug">
                Tamper-evident cryptographic ledger &amp; instant replay
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                For recording every trajectory into an immutable SHA-256 block chain with single-command reproduction via CLI.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-slate-800/60 flex items-center justify-between text-xs text-cyan-400">
              <Link href="/reports" className="hover:underline inline-flex items-center gap-1">
                Explore evidence <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Tested at Scale: Career-Agents 167-Agent Benchmark (Case Study Showcase) ── */}
      <section id="benchmarks" className="w-full bg-[#02050b] border-y border-slate-900 py-24 px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-6 space-y-6">
            <span className="font-mono text-xs text-cyan-400 uppercase tracking-widest bg-cyan-950/80 px-3 py-1 rounded-full border border-cyan-800/60">
              Verified Production Benchmark
            </span>
            <h2 className="text-3xl sm:text-5xl font-bold text-white tracking-tight leading-tight">
              Tested at Scale: 167 Autonomous Agents in Career-Agents
            </h2>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
              ARL doesn&apos;t evaluate synthetic toys. We verified the entire Career-Agents multi-agent repository across Model Context Protocol (MCP) tool discovery, JSON-RPC stdio execution, and zero unhandled exceptions under malformed chaos inputs.
            </p>

            <div className="grid grid-cols-2 gap-4 pt-2 font-mono text-xs">
              <div className="p-4 rounded-xl bg-[#080f1e] border border-cyan-500/20">
                <div className="text-2xl font-bold text-cyan-300">167 / 167</div>
                <div className="text-slate-400 mt-1">Autonomous Agents Validated</div>
              </div>
              <div className="p-4 rounded-xl bg-[#080f1e] border border-cyan-500/20">
                <div className="text-2xl font-bold text-emerald-400">100%</div>
                <div className="text-slate-400 mt-1">MCP Conformance Tests</div>
              </div>
              <div className="p-4 rounded-xl bg-[#080f1e] border border-cyan-500/20">
                <div className="text-2xl font-bold text-amber-400">0</div>
                <div className="text-slate-400 mt-1">Unhandled -32601 Leaks</div>
              </div>
              <div className="p-4 rounded-xl bg-[#080f1e] border border-cyan-500/20">
                <div className="text-2xl font-bold text-indigo-400">95% CI</div>
                <div className="text-slate-400 mt-1">Wilson Statistical Bounds</div>
              </div>
            </div>

            <div className="pt-2">
              <Link
                href="/dashboard"
                className="lc-button-primary text-xs px-5 py-2.5 inline-flex"
              >
                Inspect Benchmark Suite
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          <div className="lg:col-span-6 relative">
            <div className="rounded-2xl overflow-hidden border border-cyan-500/30 shadow-2xl shadow-cyan-950/40 group">
              <Image
                src="/images/case-study-mcp.jpg"
                alt="Career-Agents Benchmark Telemetry and Wilson Confidence Intervals"
                width={720}
                height={405}
                className="w-full object-cover group-hover:scale-[1.02] transition-transform duration-500"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ── Interactive Live Chaos Playground ── */}
      <section id="playground" className="w-full bg-[#030710] py-24 px-6 border-b border-slate-900">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-12">
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
            <div className="bg-[#03060f] rounded-xl p-5 font-mono text-xs space-y-2.5 min-h-[200px] max-h-[300px] overflow-y-auto border border-slate-900">
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

      {/* ── Enterprise Governance & Cryptographic Security Section ── */}
      <section id="governance" className="w-full bg-[#02050b] border-b border-slate-900 py-24 px-6">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-6 relative order-2 lg:order-1">
            <div className="rounded-2xl overflow-hidden border border-cyan-500/30 shadow-2xl shadow-cyan-950/40 group">
              <Image
                src="/images/enterprise-governance.jpg"
                alt="Cryptographic SHA-256 Ledger, Fail-Closed CI Gate, and Secret Redaction"
                width={720}
                height={405}
                className="w-full object-cover group-hover:scale-[1.02] transition-transform duration-500"
              />
            </div>
          </div>

          <div className="lg:col-span-6 space-y-6 order-1 lg:order-2">
            <span className="font-mono text-xs text-indigo-400 uppercase tracking-widest bg-indigo-950/80 px-3 py-1 rounded-full border border-indigo-800/60">
              Enterprise Governance &amp; Compliance
            </span>
            <h2 className="text-3xl sm:text-5xl font-bold text-white tracking-tight leading-tight">
              Cryptographically Auditable Agent Infrastructure
            </h2>
            <p className="text-slate-300 text-sm sm:text-base leading-relaxed">
              Autonomous agents that touch customer databases, financial APIs, or sensitive documents cannot rely on probabilistic tests. ARL provides deterministic, tamper-evident guarantees.
            </p>

            <div className="space-y-4 pt-1">
              <div className="flex items-start gap-3 text-sm">
                <div className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                </div>
                <div>
                  <strong className="text-white">Tamper-Evident SHA-256 Chain</strong>:{" "}
                  <span className="text-slate-400">Every trial persists cryptographic block hashes on disk to guarantee zero post-facto audit tampering.</span>
                </div>
              </div>

              <div className="flex items-start gap-3 text-sm">
                <div className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0 mt-0.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                </div>
                <div>
                  <strong className="text-white">Automatic Secret &amp; Token Redaction</strong>:{" "}
                  <span className="text-slate-400">Recursively cleans bearer tokens, API keys, and cookie headers before persisting evidence.</span>
                </div>
              </div>

              <div className="flex items-start gap-3 text-sm">
                <div className="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0 mt-0.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                </div>
                <div>
                  <strong className="text-white">Fail-Closed CI Gate</strong>:{" "}
                  <span className="text-slate-400">Critical invariant failures exit with code 1 in GitHub Actions, stopping broken agent PR merges cold.</span>
                </div>
              </div>
            </div>

            <div className="pt-2">
              <Link
                href="/reports"
                className="lc-button-secondary text-xs px-5 py-2.5 inline-flex"
              >
                View Cryptographic Evidence Reports
                <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Pre-Footer CTA with Cybernetic Particle Net (Screenshot 3 Exact Re-creation) ── */}
      <section className="w-full relative min-h-[420px] flex items-center justify-center overflow-hidden border-b border-slate-900 bg-[#02050b]">
        {/* Left Particle Funnel Image */}
        <div className="absolute left-0 top-0 bottom-0 w-full md:w-3/5 pointer-events-none opacity-80">
          <Image
            src="/images/particle-funnel.jpg"
            alt="Cybernetic Particle Mesh Funnel"
            fill
            className="object-cover object-left"
          />
          {/* Gradient fade to pure black on the right */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[#02050b]/40 to-[#02050b]" />
        </div>

        {/* CTA Content on the Right */}
        <div className="relative z-10 max-w-7xl mx-auto px-6 py-20 w-full flex flex-col md:flex-row items-center justify-end">
          <div className="max-w-xl text-left space-y-6">
            <h2 className="text-3xl sm:text-5xl font-bold text-white tracking-tight leading-tight">
              Get started with Agent Reliability Lab
            </h2>

            <div className="flex items-center gap-4">
              <Link
                href="/dashboard"
                className="lc-button-primary text-sm px-6 py-3 font-semibold shadow-xl shadow-white/10"
              >
                Start building
              </Link>
              <Link
                href="https://github.com/karthikrshet/agent-reliability"
                target="_blank"
                className="lc-button-secondary text-sm px-6 py-3 font-semibold"
              >
                Get a demo
              </Link>
            </div>

            <p className="text-sm text-slate-400 leading-relaxed">
              Use ARL, the agent engineering platform, to break your AI agents before production does.
            </p>
          </div>
        </div>
      </section>

      {/* ── Giant LangChain Style Footer with Outlined Watermark (Screenshot 4) ── */}
      <footer className="w-full bg-[#020409] pt-20 pb-12 px-6 relative overflow-hidden text-sm text-slate-400">
        <div className="max-w-7xl mx-auto space-y-16">
          {/* 4-Column Navigation & Newsletter */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10">
            {/* Col 1: Products */}
            <div className="space-y-3">
              <h4 className="text-xs font-mono uppercase tracking-widest text-slate-200 font-semibold">
                Products
              </h4>
              <ul className="space-y-2 text-xs text-slate-400">
                <li><Link href="/dashboard" className="hover:text-cyan-400 transition">ARL Platform</Link></li>
                <li><Link href="#modules" className="hover:text-cyan-400 transition">Chaos Fault Engine</Link></li>
                <li><Link href="#modules" className="hover:text-cyan-400 transition">13 Typed Invariants</Link></li>
                <li><Link href="#modules" className="hover:text-cyan-400 transition">Evidence Ledger</Link></li>
                <li><Link href="/scenarios" className="hover:text-cyan-400 transition">25 Scenarios Catalog</Link></li>
                <li><Link href="/reports" className="hover:text-cyan-400 transition">Audit Reports</Link></li>
              </ul>
            </div>

            {/* Col 2: Resources */}
            <div className="space-y-3">
              <h4 className="text-xs font-mono uppercase tracking-widest text-slate-200 font-semibold">
                Resources
              </h4>
              <ul className="space-y-2 text-xs text-slate-400">
                <li><Link href="https://github.com/karthikrshet/agent-reliability#readme" target="_blank" className="hover:text-cyan-400 transition">Documentation</Link></li>
                <li><Link href="https://github.com/karthikrshet/agent-reliability" target="_blank" className="hover:text-cyan-400 transition">GitHub Repository</Link></li>
                <li><Link href="/runs" className="hover:text-cyan-400 transition">Wilson Score Statistics</Link></li>
                <li><Link href="#playground" className="hover:text-cyan-400 transition">Failure Simulation</Link></li>
                <li><Link href="/dashboard" className="hover:text-cyan-400 transition">Quickstart CLI</Link></li>
              </ul>
            </div>

            {/* Col 3: Company / Project */}
            <div className="space-y-3">
              <h4 className="text-xs font-mono uppercase tracking-widest text-slate-200 font-semibold">
                Company
              </h4>
              <ul className="space-y-2 text-xs text-slate-400">
                <li><Link href="https://github.com/karthikrshet/agent-reliability" target="_blank" className="hover:text-cyan-400 transition">About ARL</Link></li>
                <li><Link href="https://github.com/karthikrshet/agent-reliability/blob/main/LICENSE" target="_blank" className="hover:text-cyan-400 transition">License (MIT)</Link></li>
                <li><Link href="https://github.com/karthikrshet/agent-reliability/actions" target="_blank" className="hover:text-cyan-400 transition">CI Status</Link></li>
                <li><Link href="https://github.com/karthikrshet" target="_blank" className="hover:text-cyan-400 transition">Maintainer Profile</Link></li>
              </ul>
            </div>

            {/* Col 4 & 5: Newsletter & Social */}
            <div className="lg:col-span-2 space-y-4">
              <h4 className="text-xs font-mono uppercase tracking-widest text-slate-200 font-semibold">
                Sign up for our newsletter to stay up to date
              </h4>
              <form onSubmit={handleSubscribe} className="space-y-3">
                <div className="relative">
                  <input
                    type="email"
                    placeholder="Your email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full px-4 py-2.5 rounded-xl bg-[#040812] border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition font-mono"
                  />
                </div>
                <div className="flex items-center justify-between gap-4">
                  <button
                    type="submit"
                    className="lc-button-primary text-xs px-5 py-2 font-mono"
                  >
                    {subscribed ? "Subscribed!" : "Subscribe"}
                  </button>
                  <div className="flex items-center gap-3 text-slate-500">
                    <Link href="https://github.com/karthikrshet/agent-reliability" target="_blank" className="hover:text-cyan-400 transition">
                      <Github className="w-4 h-4" />
                    </Link>
                    <Link href="https://linkedin.com" target="_blank" className="hover:text-cyan-400 transition">
                      <Linkedin className="w-4 h-4" />
                    </Link>
                    <Link href="https://twitter.com" target="_blank" className="hover:text-cyan-400 transition">
                      <Twitter className="w-4 h-4" />
                    </Link>
                    <Link href="https://youtube.com" target="_blank" className="hover:text-cyan-400 transition">
                      <Youtube className="w-4 h-4" />
                    </Link>
                  </div>
                </div>
              </form>
            </div>
          </div>

          {/* Massive Outlined Watermark Typography (Screenshot 4) */}
          <div className="w-full text-center overflow-hidden pt-12 pb-4">
            <span className="huge-outline-text block font-mono">
              AgentReliabilityLab
            </span>
          </div>

          {/* Bottom Operational Status Bar */}
          <div className="pt-6 border-t border-slate-900 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 font-mono">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400/80" />
              <span className="text-slate-400">All systems operational</span>
            </div>

            <div className="flex items-center gap-6">
              <Link href="https://github.com/karthikrshet/agent-reliability" target="_blank" className="hover:text-cyan-400 transition">
                Privacy policy
              </Link>
              <Link href="https://github.com/karthikrshet/agent-reliability" target="_blank" className="hover:text-cyan-400 transition">
                Terms of service
              </Link>
              <span>MIT License © 2026 Karthik Rajesh Shet</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
