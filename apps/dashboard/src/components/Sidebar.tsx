"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  Activity,
  Boxes,
  FileCheck,
  PlayCircle,
  Zap,
  CheckCircle2,
  Sparkles,
  ArrowUpRight,
  Menu,
  X,
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
  const [mobileOpen, setMobileOpen] = useState(false);

  const NavContent = () => (
    <div className="flex flex-col justify-between h-full">
      <div>
        {/* Brand Header */}
        <div className="p-6 border-b border-slate-800/80 flex items-center justify-between">
          <Link
            href="/"
            onClick={() => setMobileOpen(false)}
            className="flex items-center gap-3 group"
          >
            <div className="relative w-10 h-10 rounded-xl overflow-hidden shadow-lg shadow-cyan-500/20 border border-cyan-500/40 group-hover:scale-105 transition-transform bg-[#080f1e] flex items-center justify-center shrink-0">
              <Image
                src="/logo.png"
                alt="ARL Logo"
                width={40}
                height={40}
                className="object-cover"
                priority
              />
            </div>
            <div>
              <div className="font-bold text-base tracking-tight text-white flex items-center gap-2">
                ARL Platform
                <span className="text-[10px] font-mono tracking-widest px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60 uppercase">
                  v0.3
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium">Agent Reliability Lab</p>
            </div>
          </Link>
          {/* Mobile close button */}
          <button
            onClick={() => setMobileOpen(false)}
            className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Workspace Status Badge */}
        <div className="px-6 py-4">
          <div className="p-3.5 rounded-xl bg-[#080f1e] border border-cyan-500/20 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-2.5">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400/50" />
              <div>
                <p className="text-xs font-semibold text-slate-200">Evaluation Workspace</p>
                <p className="text-[11px] text-slate-400 font-mono">env: customer-support</p>
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
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10"
                    : "text-slate-400 hover:text-slate-100 hover:bg-[#080f1e]/80 border border-transparent"
                }`}
              >
                <Icon
                  className={`w-4 h-4 transition-colors ${
                    isActive ? "text-cyan-400" : "text-slate-500 group-hover:text-slate-300"
                  }`}
                />
                <span className="flex-1">{item.name}</span>
                {item.href === "/" && (
                  <ArrowUpRight className="w-3.5 h-3.5 text-slate-600" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer System Status */}
      <div className="p-4 m-4 rounded-xl bg-[#080f1e] border border-slate-800/80 shadow-inner space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800/60">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-semibold text-slate-200">Engine Online</span>
          </div>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/60">
            HEALTHY
          </span>
        </div>
        <div className="space-y-1.5 text-[11px] text-slate-400 font-mono">
          <div className="flex justify-between items-center">
            <span className="text-slate-500">API Server:</span>
            <span className="text-slate-300">localhost:8000</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500">Evidence Ledger:</span>
            <span className="text-cyan-400">SHA-256 Valid</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500">Invariants:</span>
            <span className="text-slate-300">13 Typed AST</span>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* ── Mobile Top Header Bar (md:hidden) ── */}
      <div className="md:hidden w-full bg-[#030710]/95 backdrop-blur-xl border-b border-slate-800/80 px-4 py-3 flex items-center justify-between sticky top-0 z-40">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="relative w-8 h-8 rounded-lg overflow-hidden border border-cyan-500/40 bg-[#080f1e] flex items-center justify-center shrink-0">
            <Image
              src="/logo.png"
              alt="ARL Logo"
              width={32}
              height={32}
              className="object-cover"
              priority
            />
          </div>
          <span className="font-bold text-sm tracking-tight text-white">ARL Platform</span>
        </Link>
        <button
          onClick={() => setMobileOpen(true)}
          className="p-2 rounded-lg bg-[#080f1e] border border-slate-800 text-slate-300 hover:text-white"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>
      </div>

      {/* ── Mobile Slide-Over Drawer ── */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
            onClick={() => setMobileOpen(false)}
          />
          {/* Drawer content */}
          <div className="relative w-72 max-w-[80vw] bg-[#030710] border-r border-slate-800 h-full shadow-2xl flex flex-col z-10">
            <NavContent />
          </div>
        </div>
      )}

      {/* ── Desktop Fixed Sidebar (hidden on mobile, visible md+) ── */}
      <aside className="hidden md:flex w-72 border-r border-slate-800/80 bg-[#030710]/95 backdrop-blur-xl flex-col justify-between shrink-0 h-screen sticky top-0 z-40">
        <NavContent />
      </aside>
    </>
  );
}
