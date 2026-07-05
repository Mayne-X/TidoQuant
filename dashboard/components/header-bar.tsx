import React from "react";
import { Pause, Play, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui";
import { cn } from "@/components/cn";

/* ─────────────────────────────────────────────────────────────────
   HeaderBar — page-level header w/ live status and polling toggle
   ───────────────────────────────────────────────────────────────── */
export function HeaderBar({
  title, subtitle, live, polling, onTogglePolling, children,
}: {
  title: string;
  subtitle?: React.ReactNode;
  live?: boolean;
  polling: boolean;
  onTogglePolling: () => void;
  children?: React.ReactNode;
}) {
  return (
    <header className="flex items-start sm:items-center justify-between gap-4 flex-wrap">
      <div>
        <div className="flex items-center gap-2.5">
          {live !== undefined && (
            <span
              className={cn(
                "inline-block w-2 h-2 rounded-full",
                live ? "bg-[color:var(--success)] live-pulse" : "bg-[color:var(--muted-foreground)]/40",
              )}
              aria-label={live ? "Live" : "Idle"}
            />
          )}
          <h1 className="text-xl sm:text-2xl font-semibold tracking-tight">{title}</h1>
        </div>
        {subtitle && <p className="text-sm text-[color:var(--muted-foreground)] mt-1">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-2">
        {children}
        <Button
          variant={polling ? "primary" : "outline"}
          size="sm"
          onClick={onTogglePolling}
          aria-label={polling ? "Pause auto-refresh" : "Resume auto-refresh"}
        >
          {polling ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          {polling ? "Pause" : "Resume"}
        </Button>
      </div>
    </header>
  );
}
