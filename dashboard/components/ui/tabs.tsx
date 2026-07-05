import React from "react";
import { cn } from "@/components/cn";

/* ─────────────────────────────────────────────────────────────────
   Tabs — minimal controlled tab bar
   ───────────────────────────────────────────────────────────────── */
export interface TabsProps {
  value: string;
  onValueChange: (v: string) => void;
  items: { value: string; label: string; icon?: React.ReactNode; right?: React.ReactNode }[];
  className?: string;
}

export function Tabs({ value, onValueChange, items, className }: TabsProps) {
  return (
    <div className={cn("flex items-center gap-1 p-1 rounded-xl bg-white/5 border border-[color:var(--border)] w-fit", className)}>
      {items.map(item => {
        const active = value === item.value;
        return (
          <button
            key={item.value}
            onClick={() => onValueChange(item.value)}
            className={cn(
              "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              active
                ? "bg-[color:var(--primary-soft)] text-[color:var(--primary)] shadow-[0_0_0_1px_rgba(99,102,241,0.3)_inset]"
                : "text-[color:var(--muted-foreground)] hover:text-foreground hover:bg-white/5",
            )}
          >
            {item.icon}
            {item.label}
            {item.right}
          </button>
        );
      })}
    </div>
  );
}
