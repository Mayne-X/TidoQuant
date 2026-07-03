"""Check what data exists in the live Docker DB and how the pipeline page renders."""
from __future__ import annotations

import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DB = os.path.join(os.path.dirname(__file__), "..", "journal", "tidoquant.db")

if not os.path.exists(DB):
    print(f"DB not found at {DB}")
    sys.exit(1)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

cycles = conn.execute("SELECT * FROM equity_snapshots ORDER BY id DESC LIMIT 5").fetchall()
print(f"Cycles: {len(cycles)}")
for c in cycles:
    trades = conn.execute(
        """SELECT id, symbol, direction, mayne_score, manager_decision,
                  pnl, status, debate_transcript
           FROM trades
           WHERE entered_at >= datetime(?, '-15 minutes')
             AND entered_at <= datetime(?, '+15 minutes')""",
        (c["timestamp"], c["timestamp"]),
    ).fetchall()
    print(f"  Cycle #{c['id']} ({c['timestamp']}): {len(trades)} trades")
    for t in trades:
        agents = conn.execute(
            "SELECT agent_name FROM agent_logs WHERE trade_id=?", (t["id"],)
        ).fetchall()
        dt = t["debate_transcript"] or ""
        dt_preview = dt[:80].replace("\n", " | ") if dt else "(none)"
        print(f"    Trade #{t['id']} {t['symbol']} {t['direction']} "
              f"score={t['mayne_score']} mgr={t['manager_decision']} "
              f"pnl={t['pnl']} agents={len(agents)}")
        print(f"      Transcript: {dt_preview}")
        if agents:
            for a in agents:
                print(f"      Agent: {a['agent_name']}")

# Also check if the DB path is the one Docker uses
print(f"\nDB path: {DB}")
conn.close()
