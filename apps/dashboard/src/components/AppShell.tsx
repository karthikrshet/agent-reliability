"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLanding = pathname === "/" || pathname === "/landing";

  if (isLanding) {
    return (
      <div className="w-full min-h-screen bg-[#030710] text-slate-100 overflow-x-hidden selection:bg-cyan-500/20 selection:text-cyan-200">
        {children}
      </div>
    );
  }

  return (
    <div className="flex min-h-screen w-full bg-slate-950 text-slate-100 antialiased">
      <Sidebar />
      <main className="flex-1 overflow-y-auto min-h-screen bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.15),rgba(255,255,255,0))]">
        {children}
      </main>
    </div>
  );
}
