import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/AppShell";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Agent Reliability Lab — Break your AI agent before production does",
  description:
    "Deterministic fault injection, stateful distributed-systems invariants, reproducible failure replay, and fail-closed CI gates for autonomous AI agents.",
  icons: {
    icon: "/logo.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="bg-[#030710] text-slate-100 min-h-screen antialiased font-sans">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
