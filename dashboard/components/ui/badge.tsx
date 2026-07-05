import React from "react";
import { cn } from "@/components/cn";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: "neutral" | "success" | "destructive" | "warning" | "info" | "primary" | "purple" | "pink";
  outline?: boolean;
  icon?: React.ReactNode;
}

const toneClasses: Record<NonNullable<BadgeProps["tone"]>, string> = {
  neutral:     "bg-white/5 text-foreground/80 border border-[color:var(--border)]",
  success:     "bg-[color:var(--success-soft)] text-[color:var(--success-foreground)] border border-[color:var(--success)]/30",
  destructive: "bg-[color:var(--destructive-soft)] text-[color:var(--destructive-foreground)] border border-[color:var(--destructive)]/30",
  warning:     "bg-[color:var(--warning-soft)] text-[color:var(--warning-foreground)] border border-[color:var(--warning)]/30",
  info:        "bg-[color:var(--info-soft)] text-[color:var(--info-foreground)] border border-[color:var(--info)]/30",
  primary:     "bg-[color:var(--primary-soft)] text-[color:var(--primary)] border border-[color:var(--primary)]/30",
  purple:      "bg-[color:var(--accent-purple-soft)] text-[color:var(--accent-purple)] border border-[color:var(--accent-purple)]/30",
  pink:        "bg-[color:var(--accent-pink-soft)] text-[color:var(--accent-pink)] border border-[color:var(--accent-pink)]/30",
};

export function Badge({ className, tone = "neutral", icon, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium uppercase tracking-wider",
        toneClasses[tone],
        className,
      )}
      {...props}
    >
      {icon}
      {children}
    </span>
  );
}
