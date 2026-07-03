"""HTTP-level tests for the API server.

Starts the real HTTPServer on a random port in a thread,
makes real HTTP requests via urllib, and validates JSON responses.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import urllib.request
import urllib.error
from http.server import HTTPServer

import pytest

from src.api_server import APIHandler
from src.core.signal_packet import MayneResult, SignalPacket


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setattr("src.config.DB_PATH", tmp.name)
    monkeypatch.setattr("src.database.DB_PATH", tmp.name)
    from src.database import migrate
    migrate()
    yield tmp.name
    try:
        os.unlink(tmp.name)
    except (PermissionError, FileNotFoundError):
        pass


@pytest.fixture
def server(temp_db, monkeypatch):
    """Start the API server on a free port, yield the URL, then shut down."""
    port = _free_port()
    server = HTTPServer(("127.0.0.1", port), APIHandler)
    shut_it_down = threading.Event()

    def serve():
        while not shut_it_down.is_set():
            server.handle_request()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    time.sleep(0.05)
    url = f"http://127.0.0.1:{port}"
    yield url
    shut_it_down.set()
    server.server_close()


def _fetch(url: str) -> tuple[int | None, dict | str]:
    try:
        resp = urllib.request.urlopen(url, timeout=3)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())
    except Exception as e:
        return None, {"error": str(e)}


def _seed():
    from src.database import insert_trade, close_trade, log_agent_call, snapshot_equity
    mayne = MayneResult(score=72, passed_gate=True, direction="long",
                        ote_points=20, sweep_points=25, fvg_points=25)
    p = SignalPacket(symbol="BTCUSDT", direction="long", mayne=mayne,
                     entry_price=50000.0, current_price=50100.0,
                     stop_loss=49000.0, take_profit=52000.0,
                     leverage=2, position_size_usd=10.0)
    p.manager_decision = "GO"
    p.manager_confidence = 80
    tid = insert_trade(p)
    close_trade(tid, 51000.0, 200.0, "TP_HIT")
    for name, lat in [("MayneGate", 150), ("ManagerAgent", 900)]:
        log_agent_call(tid, name, "prompt", "response", lat)
    snapshot_equity(102.0)


class TestAPIHealth:
    def test_health_returns_ok(self, server):
        _, data = _fetch(f"{server}/api/health")
        assert data["status"] == "ok"

    def test_health_bare_path(self, server):
        _, data = _fetch(f"{server}/health")
        assert data["status"] == "ok"

    def test_404_returns_error(self, server):
        code, data = _fetch(f"{server}/api/nonexistent")
        assert code == 404
        assert "error" in data


class TestAPISummary:
    def test_summary_empty(self, server):
        _, data = _fetch(f"{server}/api/summary")
        assert data["equity"] <= 1000.0
        assert data["total_trades"] == 0

    def test_summary_with_data(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/summary")
        assert data["total_trades"] == 1
        assert data["wins"] == 1

    def test_summary_structure(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/summary")
        assert set(data.keys()) == {"equity", "total_trades", "wins", "losses", "total_pnl"}


class TestAPIDetail:
    def test_detail_empty(self, server):
        _, data = _fetch(f"{server}/api/detail")
        assert data["total_trades"] == 0

    def test_detail_structure(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/detail")
        for key in ("equity", "total_trades", "total_pnl", "wins", "losses",
                    "avg_win", "avg_loss", "best_trade", "worst_trade",
                    "win_rate", "profit_factor", "max_drawdown_pct"):
            assert key in data


class TestAPITrades:
    def test_trades_open_empty(self, server):
        _, data = _fetch(f"{server}/api/trades/open")
        assert data == []

    def test_trades_closed_with_data(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/trades/closed")
        assert len(data) >= 1
        assert data[0]["pnl"] == 200.0

    def test_trades_closed_structure(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/trades/closed")
        t = data[0]
        for key in ("id", "symbol", "direction", "entry_price", "pnl",
                    "status", "manager_decision"):
            assert key in t


class TestAPIPipeline:
    def test_pipeline_empty(self, server):
        _, data = _fetch(f"{server}/api/pipeline")
        assert isinstance(data, list)

    def test_pipeline_with_data(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/pipeline")
        assert len(data) >= 1
        cycle = data[0]
        assert "id" in cycle
        assert "equity" in cycle
        assert "trades" in cycle

    def test_pipeline_trade_has_agents(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/pipeline")
        has_trades = [c for c in data if c.get("trades")]
        if has_trades:
            trade = has_trades[0]["trades"][0]
            assert "agents" in trade
            assert len(trade["agents"]) >= 1
            assert trade["agents"][0]["agent_name"] == "MayneGate"

    def test_pipeline_bare_path(self, server):
        _seed()
        _, data = _fetch(f"{server}/pipeline")
        assert isinstance(data, list)

    def test_agent_log_structure(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/pipeline")
        for cycle in data:
            for trade in cycle.get("trades", []):
                for agent in trade.get("agents", []):
                    assert "agent_name" in agent
                    assert "prompt" in agent
                    assert "response" in agent
                    assert "latency_ms" in agent
                    assert "error" in agent


class TestAPIEquity:
    def test_equity_empty(self, server):
        _, data = _fetch(f"{server}/api/equity")
        assert isinstance(data, list)

    def test_equity_with_data(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/equity")
        assert len(data) >= 1
        assert "id" in data[0]
        assert "equity" in data[0]


class TestAPICycles:
    def test_cycles_with_data(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/cycles")
        assert isinstance(data, list)

    def test_cycle_structure(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/cycles")
        if data:
            assert "id" in data[0]
            assert "equity" in data[0]
            assert "trades_since" in data[0]


class TestAPIBySymbol:
    def test_by_symbol_with_data(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/trades/by_symbol")
        assert isinstance(data, list)
        if data:
            assert "symbol" in data[0]
            assert "total_pnl" in data[0]


class TestAPIDailyPnl:
    def test_daily_pnl_with_data(self, server):
        _seed()
        _, data = _fetch(f"{server}/api/pnl/daily")
        assert isinstance(data, list)
        if data:
            assert "day" in data[0]
            assert "pnl" in data[0]
