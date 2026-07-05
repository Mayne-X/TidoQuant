import React from "react";
import { cn } from "@/components/cn";

/* ─────────────────────────────────────────────────────────────────
   EmptyState — friendly placeholder
   ───────────────────────────────────────────────────────────────── */
export function EmptyState({
  icon, title, description, action, tone = "info", className,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  tone?: "info" | "success" | "warning" | "primary";
  className?: string;
}) {
  const toneClass: Record<typeof tone, string> = {
    info: "bg-[color:var(--info-soft)] text-[color:var(--info-foreground)]",
    success: "bg-[color:var(--success-soft)] text-[color:var(--success-foreground)]",
    warning: "bg-[color:var(--warning-soft)] text-[color:var(--warning-foreground)]",
    primary: "bg-[color:var(--primary-soft)] text-[color:var(--primary)]",
  } as const;
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center py-12 px-4 rounded-xl",
        "border border-dashed border-[color:var(--border)] bg-white/[0.02]",
        className,
      )}
    >
      {icon && (
        <div className={cn("w-12 h-12 rounded-xl grid place-items-center mb-4", toneClass[tone])}>
          {icon}
        </div>
      )}
      <h3 className="text-sm font-medium text-foreground">{title}</h3>
      {description && <p className="mt-1 text-xs text-[color:var(--muted-foreground)] max-w-md">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
