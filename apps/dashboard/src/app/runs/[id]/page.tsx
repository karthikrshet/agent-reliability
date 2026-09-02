"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Bug,
  Database,
  CheckCircle2,
  XCircle,
  Hash,
  Terminal,
  ChevronRight,
  Layers,
} from "lucide-react";

interface TurnStep {
  turnIndex: number;
  userPrompt: string;
  observableAction: string;
  toolCall: {
    toolName: string;
    arguments: Record<string, any>;
    injectedFault?: {
      type: string;
      description: string;
    };
    rawResponse: Record<string, any>;
    latencyMs: number;
  };
  agentResponse: string;
}

const SAMPLE_TRAJECTORY: TurnStep[] = [
  {
    turnIndex: 1,
    userPrompt: "Hi, can you check the status of my order #1042? Also if it hasn't shipped yet, cancel it.",
    observableAction: "Dispatched order.lookup(order_id='order-1042', customer_id='cust-501')",
    toolCall: {
      toolName: "order.lookup",
      arguments: { order_id: "order-1042", customer_id: "cust-501" },
      injectedFault: {
        type: "HTTP_500_INTERNAL_SERVER_ERROR",
        description: "Fault engine injected transient 500 error on 1st attempt to test agent retry resilience.",
      },
      rawResponse: {
        error: "InternalServerError",
        message: "Simulated transient upstream database timeout. Retry permitted.",
        status_code: 500,
      },
      latencyMs: 312,
    },
    agentResponse: "I encountered a transient system delay while looking up your order. Retrying immediately...",
  },
  {
    turnIndex: 2,
    userPrompt: "[SYSTEM RETRY]",
    observableAction: "Retried order.lookup after transient 500 backoff",
    toolCall: {
      toolName: "order.lookup",
      arguments: { order_id: "order-1042", customer_id: "cust-501" },
      rawResponse: {
        order_id: "order-1042",
        status: "processing",
        items: [{ sku: "SKU-99", name: "Ergonomic Mechanical Keyboard", price: 129.99 }],
        can_cancel: true,
      },
      latencyMs: 145,
    },
    agentResponse: "Your order #1042 is currently processing and has not shipped yet. Would you like me to cancel it for a full refund of $129.99?",
  },
  {
    turnIndex: 3,
    userPrompt: "Yes please cancel it.",
    observableAction: "Dispatched order.cancel with unique idempotency_key",
    toolCall: {
      toolName: "order.cancel",
      arguments: {
        order_id: "order-1042",
        customer_id: "cust-501",
        idempotency_key: "idem-cancel-1042-88219",
      },
      rawResponse: {
        order_id: "order-1042",
        status: "cancelled",
        refund_id: "ref-7801",
        refund_amount: 129.99,
        success: true,
      },
      latencyMs: 198,
    },
    agentResponse: "I have successfully cancelled your order #1042. A refund of $129.99 has been processed to your original payment method.",
  },
];

export default function RunDetailPage() {
  const params = useParams();
  const runId = params?.id || "run-e2e-canary-01";
  const [selectedTurn, setSelectedTurn] = useState<number>(1);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Back button & title */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/runs"
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white font-mono">{runId}</h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-bold uppercase tracking-wider">
                COMPLETED &bull; READY
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Trial 1 of 3 &bull; Scenario: <code className="text-indigo-300">er-01-transient-500-retry</code>
            </p>
          </div>
        </div>

        {/* Cryptographic Proof Hash Badge */}
        <div className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 flex items-center gap-2">
          <Hash className="w-4 h-4 text-emerald-400" />
          <div>
            <p className="text-[10px] text-slate-400 uppercase font-semibold">Evidence Ledger Hash</p>
            <p className="text-xs font-mono text-emerald-400">0e94c8fa721d...a89c</p>
          </div>
        </div>
      </div>

      {/* Trial Score Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl glass-panel">
          <p className="text-xs text-slate-400">Trial Verdict</p>
          <p className="text-lg font-bold text-emerald-400 flex items-center gap-1.5 mt-0.5">
            <CheckCircle2 className="w-5 h-5" /> PASS
          </p>
          <p className="text-[11px] text-slate-500 mt-1">Zero safety vetoes</p>
        </div>
        <div className="p-4 rounded-xl glass-panel">
          <p className="text-xs text-slate-400">Deterministic Score</p>
          <p className="text-lg font-bold text-white font-mono mt-0.5">1.00 / 1.00</p>
          <p className="text-[11px] text-emerald-400 mt-1">All expected effects matched</p>
        </div>
        <div className="p-4 rounded-xl glass-panel">
          <p className="text-xs text-slate-400">Budget Consumed</p>
          <p className="text-lg font-bold text-white font-mono mt-0.5">3 / 6 Turns</p>
          <p className="text-[11px] text-slate-400 mt-1">3 tool calls (Max: 4)</p>
        </div>
        <div className="p-4 rounded-xl glass-panel">
          <p className="text-xs text-slate-400">Fault Recovered</p>
          <p className="text-lg font-bold text-indigo-400 flex items-center gap-1 mt-0.5">
            <Bug className="w-5 h-5" /> 1 Injected (Recovered)
          </p>
          <p className="text-[11px] text-slate-400 mt-1">HTTP 500 backoff handled</p>
        </div>
      </div>

      {/* Trajectory & Fault Timeline Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Turn Navigation List */}
        <div className="space-y-3">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Agent Execution Turns ({SAMPLE_TRAJECTORY.length})
          </h3>
          <div className="space-y-2">
            {SAMPLE_TRAJECTORY.map((step) => {
              const isSelected = selectedTurn === step.turnIndex;
              const hasFault = !!step.toolCall.injectedFault;
              return (
                <div
                  key={step.turnIndex}
                  onClick={() => setSelectedTurn(step.turnIndex)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition ${
                    isSelected
                      ? "bg-indigo-600/15 border-indigo-500/40 text-white"
                      : "bg-slate-900/40 border-slate-800 text-slate-300 hover:bg-slate-900/80"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-xs text-indigo-300">Turn #{step.turnIndex}</span>
                    <div className="flex items-center gap-1.5">
                      {hasFault && (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                          FAULT INJECTED
                        </span>
                      )}
                      <span className="text-[11px] font-mono text-slate-400">
                        {step.toolCall.latencyMs}ms
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-300 line-clamp-1 font-mono">{step.toolCall.toolName}()</p>
                </div>
              );
            })}
          </div>

          {/* Grader Findings Box */}
          <div className="p-4 rounded-xl glass-panel space-y-3 mt-6">
            <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Automated Grader Verdicts
            </h4>
            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
                <div>
                  <p className="font-semibold text-slate-200">EffectMatchGrader</p>
                  <p className="text-[11px] text-slate-400">orders.order-1042.status == cancelled</p>
                </div>
                <span className="text-emerald-400 font-bold">1.0</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
                <div>
                  <p className="font-semibold text-slate-200">BudgetGrader</p>
                  <p className="text-[11px] text-slate-400">3/6 turns &bull; 3/4 calls</p>
                </div>
                <span className="text-emerald-400 font-bold">1.0</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between">
                <div>
                  <p className="font-semibold text-slate-200">SemanticLLMJudge</p>
                  <p className="text-[11px] text-slate-400">Polite error explanation</p>
                </div>
                <span className="text-emerald-400 font-bold">0.96</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Detailed Turn & Tool Inspector */}
        <div className="lg:col-span-2 space-y-4">
          {SAMPLE_TRAJECTORY.filter((s) => s.turnIndex === selectedTurn).map((step) => (
            <div key={step.turnIndex} className="space-y-4">
              {/* User Prompt */}
              <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
                <p className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider mb-1">
                  User Message
                </p>
                <p className="text-sm text-slate-200">{step.userPrompt}</p>
              </div>

              {/* Observable Execution Action */}
              <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800">
                <p className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider mb-1">
                  Observable Agent Action
                </p>
                <p className="text-xs text-slate-300 font-mono">{step.observableAction}</p>
              </div>

              {/* Tool Execution & Fault Injection */}
              <div className="p-5 rounded-xl glass-panel space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-bold text-white font-mono">
                      Tool Invocation: {step.toolCall.toolName}()
                    </span>
                  </div>
                  <span className="text-xs font-mono text-slate-400">
                    Latency: {step.toolCall.latencyMs}ms
                  </span>
                </div>

                {/* Arguments Code Block */}
                <div>
                  <p className="text-[11px] text-slate-400 mb-1">Arguments Sent to Tool Proxy:</p>
                  <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-xs font-mono text-indigo-300 overflow-x-auto">
                    {JSON.stringify(step.toolCall.arguments, null, 2)}
                  </pre>
                </div>

                {/* Fault Alert Box if injected */}
                {step.toolCall.injectedFault && (
                  <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 space-y-1">
                    <div className="flex items-center gap-1.5 text-amber-400 font-bold text-xs">
                      <Bug className="w-4 h-4" />
                      Fault Injected: {step.toolCall.injectedFault.type}
                    </div>
                    <p className="text-xs text-amber-200/90 leading-relaxed">
                      {step.toolCall.injectedFault.description}
                    </p>
                  </div>
                )}

                {/* Response Code Block */}
                <div>
                  <p className="text-[11px] text-slate-400 mb-1">Tool Proxy Response:</p>
                  <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-xs font-mono text-emerald-300 overflow-x-auto">
                    {JSON.stringify(step.toolCall.rawResponse, null, 2)}
                  </pre>
                </div>
              </div>

              {/* Agent Assistant Response */}
              <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
                <p className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider mb-1">
                  Agent Final Turn Response
                </p>
                <p className="text-sm text-slate-200">{step.agentResponse}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
