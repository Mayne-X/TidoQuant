import React from "react";
import { cn } from "@/components/cn";

/* ─────────────────────────────────────────────────────────────────
   Card — surface, header, title, content, footer
   ───────────────────────────────────────────────────────────────── */

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  interactive?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(function Card(
  { className, interactive, children, ...props }, ref,
) {
  return (
    <div
      ref={ref}
      className={cn(
        "rounded-[14px] border border-[color:var(--border)] bg-[color:var(--surface)]/80 backdrop-blur",
        "shadow-[0_1px_0_rgba(255,255,255,0.02)_inset,0_18px_40px_-22px_rgba(0,0,0,0.6)]",
        interactive && "transition-all duration-200 hover:border-[color:var(--border-strong)] hover:bg-[color:var(--surface)]",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
});

export function CardHeader({ className, children }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex items-center justify-between gap-3 p-5 pb-3", className)}>{children}</div>;
}

export function CardTitle({ className, children, hint }: { className?: string; children: React.ReactNode; hint?: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-3">
      <h3 className={cn("text-sm font-semibold tracking-tight text-foreground", className)}>{children}</h3>
      {hint && <span className="text-xs text-[color:var(--muted-foreground)]">{hint}</span>}
    </div>
  );
}

export function CardContent({ className, children }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5 pt-2", className)}>{children}</div>;
}

export function CardFooter({ className, children }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex items-center justify-between gap-3 px-5 py-3 border-t border-[color:var(--border)] bg-white/[0.02] rounded-b-[14px]",
        className,
      )}
    >
      {children}
    </div>
  );
}
