import React from "react";
import { cn } from "@/components/cn";

/* ─────────────────────────────────────────────────────────────────
   ProgressBar — for showing pipeline agent latency relative to a budget
   ───────────────────────────────────────────────────────────────── */
export function ProgressBar({
  value, max = 100, tone = "primary", className, showLabel = false,
}: {
  value: number;
  max?: number;
  tone?: "primary" | "success" | "warning" | "destructive" | "info";
  className?: string;
  showLabel?: boolean;
}) {
  const pct = Math.max(0, Math.min(100, (value / Math.max(1, max)) * 100));
  const toneBar: Record<typeof tone, string> = {
    primary: "bg-[color:var(--primary)]",
    success: "bg-[color:var(--success)]",
    warning: "bg-[color:var(--warning)]",
    destructive: "bg-[color:var(--destructive)]",
    info: "bg-[color:var(--info)]",
  } as const;
  return (
    <div className={cn("w-full", className)}>
      <div className="relative h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div
          className={cn("absolute inset-y-0 left-0 transition-all duration-300 rounded-full", toneBar[tone])}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <p className="mt-1 text-[10px] text-[color:var(--muted-foreground)] tabular">{value.toFixed(0)}ms</p>
      )}
    </div>
  );
}
