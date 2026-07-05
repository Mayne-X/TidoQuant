import React from "react";
import { cn } from "@/components/cn";

/* ─────────────────────────────────────────────────────────────────
   DataTable — generic table with sticky header, hover, dense mode
   ───────────────────────────────────────────────────────────────── */
export function DataTable<T>({
  columns, rows, getKey, empty, dense = false, rowClassName,
}: {
  columns: {
    key: string;
    header: React.ReactNode;
    className?: string;
    align?: "left" | "right" | "center";
    render: (row: T) => React.ReactNode;
  }[];
  rows: T[];
  getKey: (row: T) => string | number;
  empty?: React.ReactNode;
  dense?: boolean;
  rowClassName?: (row: T) => string;
}) {
  return (
    <div className="overflow-x-auto max-h-[480px] overflow-y-auto rounded-lg border border-[color:var(--border)]">
      <table className="w-full text-sm tabular">
        <thead className="sticky top-0 z-10 bg-[color:var(--surface-raised)]/95 backdrop-blur border-b border-[color:var(--border)]">
          <tr>
            {columns.map(c => (
              <th
                key={c.key}
                className={cn(
                  "font-medium text-[10px] uppercase tracking-wider text-[color:var(--muted-foreground)]",
                  dense ? "py-2" : "py-3",
                  "px-3",
                  c.align === "right" && "text-right",
                  c.align === "center" && "text-center",
                  !c.align && "text-left",
                  c.className,
                )}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="py-8">
                {empty || <div className="text-xs text-center text-[color:var(--muted-foreground)]">No data</div>}
              </td>
            </tr>
          ) : (
            rows.map(row => (
              <tr
                key={getKey(row)}
                className={cn(
                  "border-b border-[color:var(--border)]/60 hover:bg-white/[0.03] transition-colors",
                  rowClassName?.(row),
                )}
              >
                {columns.map(c => (
                  <td
                    key={c.key}
                    className={cn(
                      dense ? "py-2" : "py-3",
                      "px-3",
                      c.align === "right" && "text-right",
                      c.align === "center" && "text-center",
                      c.className,
                    )}
                  >
                    {c.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
