"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Boxes,
  FileCheck,
  PlayCircle,
  ShieldCheck,
  Zap,
  CheckCircle2,
  Sparkles,
} from "lucide-react";

const NAV_ITEMS = [
  { name: "Landing Page", href: "/", icon: Sparkles },
  { name: "Overview", href: "/dashboard", icon: Activity },
  { name: "Scenarios (25)", href: "/scenarios", icon: Boxes },
  { name: "Evaluation Runs", href: "/runs", icon: PlayCircle },
  { name: "Audit Reports & Evidence", href: "/reports", icon: FileCheck },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-72 border-r border-slate-800/80 bg-slate-950/60 backdrop-blur-xl flex flex-col justify-between shrink-0 h-screen sticky top-0">
      <div>
        {/* Brand Header */}
        <div className="p-6 border-b border-slate-800/60 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
                ARL Platform
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                  v0.2.1-beta
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium">Agent Reliability Lab</p>
            </div>
          </Link>
        </div>

        {/* Workspace Status Badge */}
        <div className="px-6 py-4">
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <div>
                <p className="text-xs font-semibold text-slate-200">Evaluation Workspace</p>
                <p className="text-[11px] text-slate-400">Environment: customer-support</p>
              </div>
            </div>
            <Zap className="w-4 h-4 text-amber-400" />
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="px-4 py-2 space-y-1.5">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? "bg-indigo-600/15 text-indigo-300 border border-indigo-500/30 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-indigo-400" : "text-slate-500"}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer System Status */}
      <div className="p-4 m-4 rounded-xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center gap-2 mb-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-semibold text-slate-200">Engine Online</span>
        </div>
        <div className="space-y-1 text-[11px] text-slate-400">
          <div className="flex justify-between">
            <span>API Server:</span>
            <span className="text-slate-300 font-mono">localhost:8000</span>
          </div>
          <div className="flex justify-between">
            <span>Evidence Ledger:</span>
            <span className="text-emerald-400 font-mono">SHA-256 Valid</span>
          </div>
          <div className="flex justify-between">
            <span>Scenarios Loaded:</span>
            <span className="text-slate-300 font-mono">25 Canonical</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
