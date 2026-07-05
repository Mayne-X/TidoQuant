import React from "react";
import { cn, fmtPct, fmtUSD } from "@/components/cn";
import { ArrowDown, ArrowUp, Minus } from "lucide-react";

type Tone = "neutral" | "success" | "destructive" | "warning" | "info" | "primary" | "purple" | "pink";

const toneTextClass: Record<Tone, string> = {
  neutral: "text-foreground",
  success: "text-[color:var(--success-foreground)]",
  destructive: "text-[color:var(--destructive-foreground)]",
  warning: "text-[color:var(--warning-foreground)]",
  info:    "text-[color:var(--info-foreground)]",
  primary: "text-[color:var(--primary)]",
  purple:  "text-[color:var(--accent-purple)]",
  pink:    "text-[color:var(--accent-pink)]",
};

const toneAccent: Record<Tone, string> = {
  neutral: "from-white/10 to-white/0",
  success: "from-[color:var(--success)]/40 to-[color:var(--success)]/0",
  destructive: "from-[color:var(--destructive)]/40 to-[color:var(--destructive)]/0",
  warning: "from-[color:var(--warning)]/40 to-[color:var(--warning)]/0",
  info:    "from-[color:var(--info)]/40 to-[color:var(--info)]/0",
  primary: "from-[color:var(--primary)]/40 to-[color:var(--primary)]/0",
  purple:  "from-[color:var(--accent-purple)]/40 to-[color:var(--accent-purple)]/0",
  pink:    "from-[color:var(--accent-pink)]/40 to-[color:var(--accent-pink)]/0",
};

const toneSoftBg: Record<Tone, string> = {
  neutral: "bg-white/5",
  success: "bg-[color:var(--success-soft)]",
  destructive: "bg-[color:var(--destructive-soft)]",
  warning: "bg-[color:var(--warning-soft)]",
  info:    "bg-[color:var(--info-soft)]",
  primary: "bg-[color:var(--primary-soft)]",
  purple:  "bg-[color:var(--accent-purple-soft)]",
  pink:    "bg-[color:var(--accent-pink-soft)]",
};

interface StatCardProps {
  label: string;
  value: string | number;
  hint?: string;
  delta?: number;
  tone?: Tone;
  icon?: React.ReactNode;
  asCurrency?: boolean;
  asPercent?: boolean;
  subtitle?: string;
  sparkline?: number[];
}

export function StatCard({
  label, value, hint, delta, tone = "neutral",
  icon, subtitle, sparkline,
}: StatCardProps) {
  const Trend =
    delta == null ? null : delta > 0 ? ArrowUp : delta < 0 ? ArrowDown : Minus;
  const trendTone =
    delta == null ? "" :
    delta > 0 ? "text-[color:var(--success-foreground)]" :
    delta < 0 ? "text-[color:var(--destructive-foreground)]" :
    "text-[color:var(--muted-foreground)]";

  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-[14px]",
        "bg-[color:var(--surface)] border border-[color:var(--border)]",
        "shadow-[0_1px_0_rgba(255,255,255,0.02)_inset,0_18px_40px_-22px_rgba(0,0,0,0.6)]",
        "transition-all duration-200 hover:border-[color:var(--border-strong)]",
      )}
    >
      {/* Decorative gradient */}
      <div className={cn("absolute inset-0 bg-gradient-to-br opacity-50 pointer-events-none", toneAccent[tone])} />

      <div className="relative p-4">
        <div className="flex items-center justify-between">
          <p className="text-[11px] font-medium uppercase tracking-wider text-[color:var(--muted-foreground)]">{label}</p>
          {icon && (
            <div className={cn("w-9 h-9 rounded-lg grid place-items-center", toneSoftBg[tone])}>
              <span className={toneTextClass[tone]}>{icon}</span>
            </div>
          )}
        </div>

        <p className={cn("mt-2 text-2xl font-semibold tabular tracking-tight", toneTextClass[tone])}>
          {value}
        </p>

        {(hint || delta != null || subtitle) && (
          <div className="mt-1.5 flex items-center gap-2 text-xs">
            {delta != null && Trend && (
              <span className={cn("inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md tabular", trendTone, toneSoftBg[tone])}>
                <Trend className="w-3 h-3" />
                {fmtPct(delta)}
              </span>
            )}
            {hint && <span className="text-[color:var(--muted-foreground)]">{hint}</span>}
            {!hint && subtitle && <span className="text-[color:var(--muted-foreground)]">{subtitle}</span>}
          </div>
        )}

        {sparkline && sparkline.length > 1 && (
          <div className="mt-3 -mx-2">
            <Sparkline values={sparkline} tone={tone} />
          </div>
        )}
      </div>
    </div>
  );
}

/* Inline sparkline (no dependency) */
export function Sparkline({ values, tone = "primary", height = 36 }: { values: number[]; tone?: Tone; height?: number }) {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 100;
  const h = height;
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return [x, y] as const;
  });
  const path = points.map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`).join(" ");
  const area = `${path} L ${w} ${h} L 0 ${h} Z`;
  const stroke =
    tone === "success" ? "var(--success-foreground)" :
    tone === "destructive" ? "var(--destructive-foreground)" :
    tone === "warning" ? "var(--warning-foreground)" :
    tone === "info" ? "var(--info-foreground)" :
    tone === "purple" ? "var(--accent-purple)" :
    tone === "pink" ? "var(--accent-pink)" :
    "var(--primary)";

  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="w-full" style={{ height }}>
      <defs>
        <linearGradient id={`spark-${tone}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%"  stopColor={stroke} stopOpacity="0.35" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#spark-${tone})`} />
      <path d={path} fill="none" stroke={stroke} strokeWidth={1.5} />
    </svg>
  );
}
