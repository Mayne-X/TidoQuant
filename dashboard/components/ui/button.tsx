import React from "react";
import { cn } from "@/components/cn";

type ButtonVariant = "primary" | "secondary" | "ghost" | "outline" | "destructive";
type ButtonSize = "sm" | "md" | "icon";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-[color:var(--primary)] text-white hover:brightness-110 active:brightness-95",
  secondary: "bg-[color:var(--surface-raised)] text-foreground hover:bg-[color:var(--surface-overlay)] border border-[color:var(--border)]",
  ghost: "bg-transparent text-foreground/80 hover:bg-white/5",
  outline: "bg-transparent text-foreground border border-[color:var(--border-strong)] hover:bg-white/5",
  destructive: "bg-[color:var(--destructive)] text-white hover:brightness-110",
};

const sizes: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-9 px-4 text-sm",
  icon: "h-9 w-9",
};

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  asChild?: boolean;
}

export function Button({
  className,
  variant = "secondary",
  size = "sm",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all duration-150",
        "focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)]",
        "disabled:opacity-50 disabled:pointer-events-none",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  );
}
