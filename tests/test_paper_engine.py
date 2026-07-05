"""Test paper trading engine: open, close, SL/TP, circuit breaker."""
import os
import tempfile
import pytest

from src.paper_engine import PaperEngine
from src.core.signal_packet import MayneResult, SignalPacket
from src.database import migrate, insert_trade, get_open_trades
from src.config import DB_PATH, STARTING_EQUITY


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    """Isolate DB for each test."""
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


def make_packet(symbol="BTCUSDT", direction="long", entry=50000.0,
                sl=49000.0, tp=52000.0, size=10.0, lev=2):
    mayne = MayneResult(score=72, passed_gate=True, direction=direction)
    p = SignalPacket(
        symbol=symbol, direction=direction, mayne=mayne,
        entry_price=entry, current_price=entry,
        stop_loss=sl, take_profit=tp,
        leverage=lev, position_size_usd=size,
    )
    p.manager_decision = "GO"
    p.manager_confidence = 80
    return p


class TestPaperEngine:
    def test_initial_equity(self):
        engine = PaperEngine()
        assert engine.equity == STARTING_EQUITY

    def test_open_position_deducts_fee(self):
        engine = PaperEngine()
        p = make_packet(size=100.0)
        tid = insert_trade(p)
        engine.open_position(p, tid)
        # Taker fee = 0.04% of 100 = 0.04
        assert engine.equity < STARTING_EQUITY
        assert len(engine._positions) == 1

    def test_tp_hit_closes_position(self):
        engine = PaperEngine()
        p = make_packet(symbol="BTCUSDT", entry=50000, tp=52000, sl=49000, size=100, lev=2)
        tid = insert_trade(p)
        engine.open_position(p, tid)

        # Price hits TP
        engine.update_positions("BTCUSDT", 52000, 52000)
        assert tid not in engine._positions
        assert engine.equity > STARTING_EQUITY - 0.04  # fee deducted but TP added

    def test_sl_hit_closes_position(self):
        engine = PaperEngine()
        p = make_packet(symbol="BTCUSDT", entry=50000, tp=52000, sl=49000, size=100, lev=2)
        tid = insert_trade(p)
        engine.open_position(p, tid)

        # Price hits SL
        engine.update_positions("BTCUSDT", 49000, 49000)
        assert tid not in engine._positions
        assert engine.equity < STARTING_EQUITY  # lost money + fee

    def test_no_action_on_mid_price(self):
        engine = PaperEngine()
        p = make_packet(symbol="BTCUSDT", entry=50000, tp=52000, sl=49000)
        tid = insert_trade(p)
        engine.open_position(p, tid)

        engine.update_positions("BTCUSDT", 50500, 50500)
        assert tid in engine._positions

    def test_circuit_breaker_at_30_percent(self):
        """Trading disallowed when equity drops below 70."""
        engine = PaperEngine()
        assert engine.is_trading_allowed()
        engine.equity = 69.0
        assert not engine.is_trading_allowed()

    def test_open_position_persists_to_db(self):
        engine = PaperEngine()
        p = make_packet()
        tid = insert_trade(p)
        engine.open_position(p, tid)
        db_open = get_open_trades()
        assert len(db_open) >= 1

    def test_long_pnl_calculation(self):
        """Long: entry=50000, exit=52000, lev=2, size=100. PnL = (2000/50000)*2*100 = $8."""
        engine = PaperEngine()
        p = make_packet(entry=50000, sl=49000, tp=52000, size=100, lev=2)
        tid = insert_trade(p)
        initial = engine.equity
        engine.open_position(p, tid)
        engine.update_positions("BTCUSDT", 52000, 52000)
        # Equity should be initial - fee + 8
        expected = initial - (100 * 0.0004) + 8.0
        assert abs(engine.equity - expected) < 0.01

    def test_short_pnl_calculation(self):
        engine = PaperEngine()
        p = make_packet(direction="short", entry=50000, sl=51000, tp=48000, size=100, lev=2)
        tid = insert_trade(p)
        initial = engine.equity
        engine.open_position(p, tid)
        # Short: price drops to 48000 = profit
        engine.update_positions("BTCUSDT", 48000, 48000)
        # PnL = (48000-50000)/50000 * (-1) * 2 * 100 = (2000/50000)*2*100 = $8
        expected = initial - (100 * 0.0004) + 8.0
        assert abs(engine.equity - expected) < 0.01

    def test_only_updates_matching_symbol(self):
        engine = PaperEngine()
        p = make_packet(symbol="BTCUSDT", entry=50000, sl=49000, tp=52000)
        tid = insert_trade(p)
        engine.open_position(p, tid)
        engine.update_positions("ETHUSDT", 999999, 999999)  # shouldn't affect BTC position
        assert tid in engine._positions
