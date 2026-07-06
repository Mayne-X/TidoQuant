"""Database sub-package: SQLite (ops) + TimescaleDB (candles) + Activity Logger."""
from .sqlite_ops import (
    migrate,
    insert_placeholder_trade,
    update_trade,
    insert_trade,
    close_trade,
    get_open_trades,
    get_closed_trades,
    log_agent_call,
    snapshot_equity,
    latest_equity,
    equity_history,
    dashboard_summary,
    dashboard_detail,
    trades_by_symbol,
    daily_pnl,
    agent_summary,
    cycle_logs,
    pipeline_detail,
)
from .activity_logger import log_activity, ActivityTrace
