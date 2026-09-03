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
    <div className="flex flex-col md:flex-row min-h-screen w-full bg-[#030710] text-slate-100 antialiased selection:bg-cyan-500/20 selection:text-cyan-200 overflow-x-hidden">
      <Sidebar />
      <main className="flex-1 w-full min-w-0 overflow-y-auto min-h-screen bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(127,200,255,0.06),rgba(0,0,0,0))]">
        {children}
      </main>
    </div>
  );
}
