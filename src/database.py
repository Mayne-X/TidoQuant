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

from .config import DB_PATH


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
        return float(row["equity"]) if row else 100.0


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
        return {
            "equity": float(eq["equity"]) if eq else 100.0,
            "total_trades": stats["total"],
            "wins": stats["wins"],
            "losses": stats["losses"],
            "total_pnl": round(stats["total_pnl"], 2),
        }
