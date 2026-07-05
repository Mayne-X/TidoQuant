import React from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { LayoutDashboard, Workflow, TrendingUp } from "lucide-react";
import { cn } from "@/components/cn";

const NAV = [
  { href: "/",         label: "Dashboard", icon: LayoutDashboard },
  { href: "/pipeline", label: "Pipeline",  icon: Workflow },
];

export function Sidebar({ equity, positionCount }: { equity?: number; positionCount?: number }) {
  const router = useRouter();
  return (
    <aside className="hidden lg:flex flex-col w-[240px] shrink-0 border-r border-[color:var(--border)] bg-[color:var(--surface)]/60 backdrop-blur sticky top-0 h-screen">
      <div className="px-5 py-5 border-b border-[color:var(--border)]">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-[color:var(--primary-soft)] grid place-items-center">
            <TrendingUp className="w-5 h-5 text-[color:var(--primary)]" />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight">TidoQuant</p>
            <p className="text-[10px] text-[color:var(--muted-foreground)] uppercase tracking-wider">Paper · v2.0</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {NAV.map(item => {
          const active = router.pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all",
                active
                  ? "bg-[color:var(--primary-soft)] text-[color:var(--primary)] shadow-[0_0_0_1px_rgba(99,102,241,0.25)_inset]"
                  : "text-[color:var(--muted-foreground)] hover:text-foreground hover:bg-white/5",
              )}
            >
              <Icon className="w-4 h-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-[color:var(--border)] space-y-2">
        <div className="px-3 py-2 rounded-lg bg-white/[0.02]">
          <p className="text-[10px] uppercase tracking-wider text-[color:var(--muted-foreground)]">Equity</p>
          <p className="text-base font-semibold tabular tracking-tight">
            ${equity?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) ?? "—"}
          </p>
        </div>
        <div className="px-3 py-2 rounded-lg bg-white/[0.02]">
          <p className="text-[10px] uppercase tracking-wider text-[color:var(--muted-foreground)]">Open Positions</p>
          <p className="text-base font-semibold tabular tracking-tight">{positionCount ?? 0}</p>
        </div>
      </div>
    </aside>
  );
}

export function MobileTopBar() {
  return (
    <header className="lg:hidden flex items-center justify-between px-4 py-3 border-b border-[color:var(--border)] bg-[color:var(--surface)]/80 backdrop-blur sticky top-0 z-30">
      <Link href="/" className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-[color:var(--primary-soft)] grid place-items-center">
          <TrendingUp className="w-4 h-4 text-[color:var(--primary)]" />
        </div>
        <p className="text-sm font-semibold">TidoQuant</p>
      </Link>
      <nav className="flex gap-1">
        {NAV.map(item => (
          <Link
            key={item.href}
            href={item.href}
            className="px-2 py-1 rounded-md text-xs font-medium text-[color:var(--muted-foreground)] hover:text-foreground hover:bg-white/5"
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
