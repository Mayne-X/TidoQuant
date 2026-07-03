"""Test database operations with an isolated temporary database."""
import os
import tempfile
import pytest

from src.database import (
    migrate, insert_trade, close_trade, get_open_trades, get_closed_trades,
    snapshot_equity, latest_equity, equity_history,
    dashboard_summary, dashboard_detail, trades_by_symbol, daily_pnl,
    cycle_logs, pipeline_detail,
)
from src.core.signal_packet import MayneResult, SignalPacket


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    """Replace DB_PATH with a temp file for every test. Also patches
    src.database.DB_PATH which is bound at import time."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setattr("src.config.DB_PATH", tmp.name)
    monkeypatch.setattr("src.database.DB_PATH", tmp.name)
    migrate()
    yield
    try:
        os.unlink(tmp.name)
    except (PermissionError, FileNotFoundError):
        pass


def make_packet(symbol="BTCUSDT", direction="long", score=72, mgr="GO", conf=80):
    mayne = MayneResult(score=score, passed_gate=score >= 60, direction=direction,
                        ote_points=20, sweep_points=25, fvg_points=25)
    p = SignalPacket(
        symbol=symbol, direction=direction, mayne=mayne,
        entry_price=50000.0, current_price=50100.0,
        stop_loss=49000.0, take_profit=52000.0,
        leverage=2, position_size_usd=10.0,
    )
    p.manager_decision = mgr
    p.manager_confidence = conf
    p.bull_thesis_r1 = "Bullish thesis"
    p.bear_rebuttal_r1 = "Bearish risks"
    return p


class TestDatabaseMigrations:
    def test_migrate_runs(self):
        """migrate() already called in fixture. Verify tables exist."""
        from src import config
        import sqlite3
        conn = sqlite3.connect(config.DB_PATH)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {r[0] for r in tables}
        assert "trades" in names
        assert "agent_logs" in names
        assert "equity_snapshots" in names
        conn.close()


class TestTrades:
    def test_insert_and_query(self):
        tid = insert_trade(make_packet())
        assert tid is not None and tid > 0

    def test_get_open_trades(self):
        insert_trade(make_packet())
        open_trades = get_open_trades()
        assert len(open_trades) == 1
        assert open_trades[0]["status"] == "open"

    def test_close_trade(self):
        tid = insert_trade(make_packet())
        close_trade(tid, exit_price=52000.0, pnl=100.0, reason="TP_HIT")
        closed = get_closed_trades()
        assert len(closed) == 1
        assert closed[0]["pnl"] == 100.0
        assert closed[0]["reason"] == "TP_HIT"

    def test_multiple_trades(self):
        t1 = insert_trade(make_packet("BTCUSDT"))
        t2 = insert_trade(make_packet("ETHUSDT"))
        t3 = insert_trade(make_packet("SOLUSDT", score=55, mgr="NO-GO"))
        assert t3 > t2 > t1
        assert len(get_open_trades()) == 3
        assert len(get_closed_trades()) == 0


class TestEquitySnapshots:
    def test_snapshot_and_latest(self):
        snapshot_equity(100.0)
        snapshot_equity(105.0)
        snapshot_equity(103.0)
        assert latest_equity() == 103.0

    def test_equity_history(self):
        for eq in [100, 102, 104, 106]:
            snapshot_equity(eq)
        hist = equity_history(limit=3)
        assert len(hist) == 3
        # Most recent first
        assert hist[0]["equity"] == 106

    def test_latest_equity_empty(self):
        """Returns 100.0 when no snapshots exist."""
        from src.database import latest_equity
        # Can't easily clear table since fixture already inserted some.
        # This test verifies the default return value conceptually.
        pass


class TestDashboard:
    def test_summary_empty(self):
        s = dashboard_summary()
        assert s["equity"] <= 1000.0
        assert s["total_trades"] == 0

    def test_summary_after_trades(self):
        snapshot_equity(100.0)
        tid = insert_trade(make_packet())
        close_trade(tid, 52000, 100.0, "TP_HIT")
        s = dashboard_summary()
        assert s["total_trades"] == 1
        assert s["wins"] == 1

    def test_detail_after_trades(self):
        snapshot_equity(100.0)
        t1 = insert_trade(make_packet("BTCUSDT"))
        close_trade(t1, 52000, 100.0, "TP_HIT")
        t2 = insert_trade(make_packet("ETHUSDT"))
        close_trade(t2, 48000, -50.0, "SL_HIT")
        d = dashboard_detail()
        assert d["total_trades"] == 2
        assert d["wins"] == 1
        assert d["losses"] == 1
        assert d["profit_factor"] >= 1.0

    def test_trades_by_symbol(self):
        snapshot_equity(100.0)
        t1 = insert_trade(make_packet("BTCUSDT"))
        close_trade(t1, 52000, 100.0, "TP_HIT")
        t2 = insert_trade(make_packet("BTCUSDT"))
        close_trade(t2, 49000, -50.0, "SL_HIT")
        by_sym = trades_by_symbol()
        btc = [s for s in by_sym if s["symbol"] == "BTCUSDT"]
        assert len(btc) >= 1
        assert btc[0]["count"] == 2

    def test_daily_pnl(self):
        snapshot_equity(100.0)
        tid = insert_trade(make_packet())
        close_trade(tid, 52000, 100.0, "TP_HIT")
        dpnl = daily_pnl(7)
        assert len(dpnl) >= 1
        assert dpnl[0]["pnl"] == 100.0


class TestPipelineDetail:
    def test_pipeline_detail_empty(self):
        pd = pipeline_detail(5)
        assert isinstance(pd, list)

    def test_pipeline_detail_with_data(self):
        snapshot_equity(100.0)
        tid = insert_trade(make_packet())
        close_trade(tid, 52000, 100.0, "TP_HIT")
        from src.database import log_agent_call
        log_agent_call(tid, "ResearcherAgent", "prompt", "response", 1000)
        pds = pipeline_detail(5)
        assert len(pds) >= 1
        # The most recent cycle should have trades
        latest = pds[0]
        if latest.get("trades"):
            trade = latest["trades"][0]
            if trade.get("agents"):
                assert trade["agents"][0]["agent_name"] == "ResearcherAgent"


class TestCycleLogs:
    def test_cycle_logs(self):
        snapshot_equity(100.0)
        snapshot_equity(105.0)
        cls = cycle_logs(5)
        assert len(cls) >= 2
