"""SQLite database layer for trade journaling, equity tracking, agent logs.

Tables:
  trades            — every opened and closed trade
  agent_logs        — per-agent LLM call record (prompt, response, latency)
  equity_snapshots  — equity recorded after each scan cycle
"""
from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

from ..config import DB_PATH


log = logging.getLogger("tidoquant")


def _db() -> sqlite3.Connection:
    """Get a new connection. WAL mode for concurrent reads."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def migrate():
    """Create tables if they don't exist."""
    with _db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS trades (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT NOT NULL,
            direction       TEXT NOT NULL,
            entry_price     REAL NOT NULL,
            exit_price      REAL,
            sl              REAL,
            tp              REAL,
            position_size   REAL,
            leverage        INTEGER,
            pnl             REAL,
            reason          TEXT,
            status          TEXT DEFAULT 'open',
            mayne_score     INTEGER,
            manager_decision TEXT,
            manager_confidence INTEGER,
            debate_transcript TEXT,
            entered_at      TEXT DEFAULT (datetime('now')),
            exited_at       TEXT
        );

        CREATE TABLE IF NOT EXISTS agent_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_id    INTEGER REFERENCES trades(id),
            agent_name  TEXT NOT NULL,
            prompt      TEXT,
            response    TEXT,
            latency_ms  INTEGER,
            error       TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS equity_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            equity      REAL NOT NULL,
            timestamp   TEXT DEFAULT (datetime('now'))
        );
        """)


# ── Trades ──────────────────────────────────────────────────

def insert_placeholder_trade(symbol: str, direction: str, entry_price: float) -> int:
    """Create a placeholder trade before pipeline runs so agents can log against it.
    Returns the trade_id. Call update_trade() after pipeline completes."""
    with _db() as db:
        cur = db.execute(
            """INSERT INTO trades
               (symbol, direction, entry_price, status)
               VALUES (?,?,?,'analyzing')""",
            (symbol, direction, entry_price),
        )
        return cur.lastrowid


def update_trade(trade_id: int, packet) -> None:
    """Update a placeholder trade with full pipeline output.
    Status: 'open' if GO, 'rejected' if NO-GO/None."""
    decision = packet.manager_decision
    status = 'open' if decision == 'GO' else 'rejected'
    with _db() as db:
        db.execute(
            """UPDATE trades SET
               sl=?, tp=?, position_size=?, leverage=?,
               mayne_score=?, manager_decision=?,
               manager_confidence=?, debate_transcript=?,
               status=?
               WHERE id=?""",
            (
                packet.stop_loss, packet.take_profit,
                packet.position_size_usd, packet.leverage,
                packet.mayne.score, packet.manager_decision,
                packet.manager_confidence, packet.debate_transcript(),
                status,
                trade_id,
            ),
        )


def insert_trade(packet) -> int:
    """Open a new trade. Returns the trade id."""
    with _db() as db:
        cur = db.execute(
            """INSERT INTO trades
               (symbol, direction, entry_price, sl, tp, position_size,
                leverage, mayne_score, manager_decision,
                manager_confidence, debate_transcript, status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,'open')""",
            (
                packet.symbol,
                packet.direction,
                packet.entry_price,
                packet.stop_loss,
                packet.take_profit,
                packet.position_size_usd,
                packet.leverage,
                packet.mayne.score,
                packet.manager_decision,
                packet.manager_confidence,
                packet.debate_transcript(),
            ),
        )
        return cur.lastrowid


def close_trade(trade_id: int, exit_price: float, pnl: float, reason: str):
    """Mark a trade as closed."""
    with _db() as db:
        db.execute(
            """UPDATE trades SET exit_price=?, pnl=?, reason=?, status='closed',
               exited_at=datetime('now') WHERE id=?""",
            (exit_price, pnl, reason, trade_id),
        )


def get_open_trades() -> List[dict]:
    with _db() as db:
        rows = db.execute("SELECT * FROM trades WHERE status='open'").fetchall()
        return [dict(r) for r in rows]


def get_closed_trades(limit: int = 100) -> List[dict]:
    with _db() as db:
        rows = db.execute(
            "SELECT * FROM trades WHERE status='closed' ORDER BY exited_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Agent Logs ──────────────────────────────────────────────

def log_agent_call(
    trade_id: int,
    agent_name: str,
    prompt: str,
    response: str,
    latency_ms: int,
    error: Optional[str] = None,
):
    with _db() as db:
        db.execute(
            """INSERT INTO agent_logs
               (trade_id, agent_name, prompt, response, latency_ms, error)
               VALUES (?,?,?,?,?,?)""",
            (trade_id, agent_name, prompt, response, latency_ms, error),
        )


# ── Equity ──────────────────────────────────────────────────

def snapshot_equity(equity: float):
    with _db() as db:
        db.execute("INSERT INTO equity_snapshots (equity) VALUES (?)", (equity,))


def latest_equity() -> float:
    with _db() as db:
        row = db.execute(
            "SELECT equity FROM equity_snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
        from ..config import STARTING_EQUITY
        return float(row["equity"]) if row else STARTING_EQUITY


def equity_history(limit: int = 500) -> List[dict]:
    with _db() as db:
        rows = db.execute(
            "SELECT * FROM equity_snapshots ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Dashboard helper ────────────────────────────────────────

def dashboard_summary() -> dict:
    """Aggregate stats for the frontend dashboard."""
    with _db() as db:
        eq = db.execute("SELECT equity FROM equity_snapshots ORDER BY id DESC LIMIT 1").fetchone()
        stats = db.execute("""
            SELECT
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN status='closed' AND pnl>0 THEN 1 ELSE 0 END),0) as wins,
                COALESCE(SUM(CASE WHEN status='closed' AND pnl<0 THEN 1 ELSE 0 END),0) as losses,
                COALESCE(SUM(pnl),0) as total_pnl
            FROM trades WHERE status='closed'
        """).fetchone()
        from ..config import STARTING_EQUITY
        return {
            "equity": float(eq["equity"]) if eq else STARTING_EQUITY,
            "total_trades": stats["total"],
            "wins": stats["wins"],
            "losses": stats["losses"],
            "total_pnl": round(stats["total_pnl"], 2),
        }


def dashboard_detail() -> dict:
    """Richer stats for charts."""
    with _db() as db:
        eq = db.execute("SELECT equity FROM equity_snapshots ORDER BY id DESC LIMIT 1").fetchone()
        stats = db.execute("""
            SELECT
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END),0) as wins,
                COALESCE(SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END),0) as losses,
                COALESCE(AVG(CASE WHEN pnl>0 THEN pnl END),0) as avg_win,
                COALESCE(AVG(CASE WHEN pnl<0 THEN pnl END),0) as avg_loss,
                COALESCE(MAX(pnl),0) as best_trade,
                COALESCE(MIN(pnl),0) as worst_trade,
                COALESCE(SUM(CASE WHEN pnl>0 THEN pnl END),0) as gross_profit,
                COALESCE(ABS(SUM(CASE WHEN pnl<0 THEN pnl END)),0) as gross_loss
            FROM trades WHERE status='closed'
        """).fetchone()
        # Find max drawdown from equity snapshots
        from ..config import STARTING_EQUITY
        rows = db.execute(
            "SELECT equity FROM equity_snapshots ORDER BY id ASC"
        ).fetchall()
        peak = STARTING_EQUITY
        max_dd = 0.0
        for r in rows:
            v = float(r["equity"])
            if v > peak: peak = v
            dd = (peak - v) / peak * 100
            if dd > max_dd: max_dd = dd
        return {
            "equity": float(eq["equity"]) if eq else STARTING_EQUITY,
            "total_trades": stats["total"],
            "total_pnl": round(stats["gross_profit"] - stats["gross_loss"], 2),
            "wins": stats["wins"],
            "losses": stats["losses"],
            "avg_win": round(stats["avg_win"], 2),
            "avg_loss": round(stats["avg_loss"], 2),
            "best_trade": round(stats["best_trade"], 2),
            "worst_trade": round(stats["worst_trade"], 2),
            "win_rate": round(stats["wins"] / max(1, stats["total"]) * 100, 1),
            "profit_factor": round(
                stats["gross_profit"] / max(0.01, stats["gross_loss"]), 2
            ),
            "max_drawdown_pct": round(max_dd, 2),
        }


def trades_by_symbol() -> List[dict]:
    with _db() as db:
        rows = db.execute("""
            SELECT symbol,
                   COUNT(*) as count,
                   SUM(CASE WHEN pnl>0 THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN pnl<0 THEN 1 ELSE 0 END) as losses,
                   COALESCE(SUM(pnl),0) as total_pnl
            FROM trades WHERE status='closed'
            GROUP BY symbol ORDER BY total_pnl DESC
        """).fetchall()
        return [dict(r) for r in rows]


def daily_pnl(limit: int = 30) -> List[dict]:
    with _db() as db:
        rows = db.execute("""
            SELECT DATE(exited_at) as day,
                   COUNT(*) as trades,
                   COALESCE(SUM(pnl),0) as pnl
            FROM trades WHERE status='closed' AND exited_at IS NOT NULL
            GROUP BY DATE(exited_at)
            ORDER BY day DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def agent_summary(trade_id: int) -> List[dict]:
    with _db() as db:
        rows = db.execute(
            "SELECT agent_name, latency_ms, error FROM agent_logs WHERE trade_id=? ORDER BY id",
            (trade_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def cycle_logs(limit: int = 20) -> List[dict]:
    """Summary of recent scan cycles: equity snapshots with trade counts."""
    with _db() as db:
        rows = db.execute("""
            SELECT e.id, e.equity, e.timestamp,
                   (SELECT COUNT(*) FROM trades WHERE status='closed' AND
                    exited_at >= datetime(e.timestamp, '-15 minutes')) as trades_since
            FROM equity_snapshots e
            ORDER BY e.id DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


def pipeline_detail(limit: int = 5) -> List[dict]:
    """Most recent pipeline runs with full agent logs and trade outcome."""
    with _db() as db:
        # Ensure index exists for performance
        db.execute("CREATE INDEX IF NOT EXISTS idx_agent_logs_trade_id ON agent_logs(trade_id)")

        # Fetch cycles
        cycles = db.execute("""
            SELECT e.id, e.equity, e.timestamp
            FROM equity_snapshots e
            ORDER BY e.id DESC LIMIT ?
        """, (limit,)).fetchall()
        
        result = []
        if not cycles:
            return result

        # Fetch all trades for these cycles in one batch
        cycle_timestamps = [c["timestamp"] for c in cycles]
        # Using placeholder expansion for the IN clause
        placeholders = ', '.join(['?'] * len(cycle_timestamps) * 2)
        trades_query = f"""
            SELECT id, symbol, direction, entry_price, exit_price,
                   sl, tp, position_size, leverage,
                   pnl, reason, status,
                   mayne_score, manager_decision, manager_confidence,
                   debate_transcript, entered_at, exited_at
            FROM trades
            WHERE entered_at >= datetime(?, '-15 minutes')
              AND entered_at <= datetime(?, '+15 minutes')
        """
        # This is tricky with a single batch query because of the time-window logic
        # Stick to trade-by-trade for logic correctness, but optimize the log fetch
        
        for cycle in cycles:
            entry = dict(cycle)
            trades = db.execute(f"{trades_query} ORDER BY id", (cycle["timestamp"], cycle["timestamp"])).fetchall()
            
            if not trades:
                entry["trades"] = []
                result.append(entry)
                continue

            trade_ids = [t["id"] for t in trades]
            # Batch fetch logs
            log_placeholders = ', '.join(['?'] * len(trade_ids))
            logs = db.execute(f"""
                SELECT trade_id, agent_name, prompt, response, latency_ms, error, created_at
                FROM agent_logs WHERE trade_id IN ({log_placeholders}) ORDER BY id
            """, trade_ids).fetchall()
            
            # Map logs to trades
            logs_by_trade = {}
            for log in logs:
                tid = log["trade_id"]
                if tid not in logs_by_trade: logs_by_trade[tid] = []
                logs_by_trade[tid].append(dict(log))

            entry["trades"] = []
            for t in trades:
                td = dict(t)
                td["agents"] = logs_by_trade.get(t["id"], [])
                entry["trades"].append(td)
            result.append(entry)
        return result
