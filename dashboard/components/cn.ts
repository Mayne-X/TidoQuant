import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtUSD(n: number, digits = 2) {
  if (Number.isNaN(n) || n == null) return "$0.00";
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtNum(n: number, digits = 2) {
  if (Number.isNaN(n) || n == null) return "0";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtPct(n: number, digits = 2) {
  if (Number.isNaN(n) || n == null) return "0%";
  return `${n >= 0 ? "+" : ""}${n.toFixed(digits)}%`;
}

export function fmtSigned(n: number, digits = 2) {
  if (Number.isNaN(n) || n == null) return "0.00";
  return `${n >= 0 ? "+" : ""}${n.toFixed(digits)}`;
}

export function relTime(iso?: string | null) {
  if (!iso) return "—";
  const d = new Date(iso + (iso.endsWith("Z") ? "" : "Z"));
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}
