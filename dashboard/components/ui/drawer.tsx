import React from "react";
import { X } from "lucide-react";
import { cn } from "@/components/cn";

/* ─────────────────────────────────────────────────────────────────
   Drawer — click-to-open side panel (Agent detail viewer)
   ───────────────────────────────────────────────────────────────── */
export function Drawer({
  open, onClose, side = "right", children, title, subtitle, width = "w-[640px] max-w-[92vw]",
}: {
  open: boolean;
  onClose: () => void;
  side?: "right" | "left";
  children: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  width?: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-[fadeIn_120ms_ease-out]"
        onClick={onClose}
      />
      <div
        className={cn(
          "absolute top-0 bottom-0 bg-[color:var(--surface)] border border-[color:var(--border)]",
          "shadow-[0_22px_50px_-16px_rgba(0,0,0,0.7)]",
          side === "right" ? "right-0" : "left-0",
          width,
        )}
        role="dialog"
        aria-modal
      >
        <div className="flex items-center justify-between p-4 border-b border-[color:var(--border)]">
          <div>
            {title && <h3 className="text-sm font-semibold">{title}</h3>}
            {subtitle && <p className="text-xs text-[color:var(--muted-foreground)] mt-0.5">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg grid place-items-center text-[color:var(--muted-foreground)] hover:text-foreground hover:bg-white/5"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="overflow-y-auto p-5 h-[calc(100vh-65px)]">{children}</div>
      </div>
    </div>
  );
}
