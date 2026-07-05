"""Paper Trading Engine with SQLite persistence.

Tracks equity, open positions, and closed trade settlement.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .config import STARTING_EQUITY, TAKER_FEE, DRAWDOWN_CIRCUIT_BREAKER
from .core.signal_packet import SignalPacket
from .database import close_trade, get_open_trades, latest_equity

log = logging.getLogger("tidoquant")


class PaperEngine:
    def __init__(self):
        self.equity = latest_equity()
        self._positions: Dict[int, dict] = {}  # trade_id -> position snapshot

        # Reload open positions from DB
        for row in get_open_trades():
            self._positions[row["id"]] = {
                "symbol": row["symbol"],
                "direction": row["direction"],
                "entry_price": row["entry_price"],
                "sl": row["sl"],
                "tp": row["tp"],
                "position_size": row["position_size"],
                "leverage": row["leverage"],
            }

        log.info(
            "PaperEngine initialised: equity=%.2f open_positions=%d",
            self.equity, len(self._positions),
        )

    def is_trading_allowed(self) -> bool:
        return self.equity > (STARTING_EQUITY * (1 - DRAWDOWN_CIRCUIT_BREAKER))

    def open_position(self, packet: SignalPacket, trade_id: int):
        """Register a new trade. Deduct taker fee from equity."""
        fee = (packet.position_size_usd or 0) * TAKER_FEE
        self.equity -= fee

        self._positions[trade_id] = {
            "symbol": packet.symbol,
            "direction": packet.direction,
            "entry_price": packet.entry_price,
            "sl": packet.stop_loss,
            "tp": packet.take_profit,
            "position_size": packet.position_size_usd or 0,
            "leverage": packet.leverage or 1,
        }

        log.info(
            "Position opened: %s %s | size=$%.2f lev=%d | fee=$%.4f",
            packet.symbol, packet.direction,
            packet.position_size_usd or 0,
            packet.leverage or 1,
            fee,
        )

    def update_positions(self, symbol: str, high: float, low: float):
        """Check SL/TP for all open positions on this symbol using candle H/L."""
        for trade_id, pos in list(self._positions.items()):
            if pos["symbol"] != symbol:
                continue

            entry = pos["entry_price"]
            sl = pos["sl"]
            tp = pos["tp"]
            direction = pos["direction"]
            size = pos["position_size"]
            leverage = pos["leverage"]

            # SL/TP hit logic based on High/Low to catch intra-interval spikes
            sl_hit = (direction == "long" and low <= sl) or \
                     (direction == "short" and high >= sl)
            tp_hit = (direction == "long" and high >= tp) or \
                     (direction == "short" and low <= tp)

            if sl_hit or tp_hit:
                # If both hit, prioritize SL for conservative risk management
                exit_price = sl if sl_hit else tp
                reason = "SL_HIT" if sl_hit else "TP_HIT"
                mult = 1 if direction == "long" else -1
                pnl_pct = (exit_price - entry) / entry * mult * leverage
                pnl = size * pnl_pct

                self.equity += pnl  # return margin + profit
                close_trade(trade_id, exit_price, pnl, reason)
                del self._positions[trade_id]

                log.info(
                    "%s: %s | PnL=$%.2f (%.2f%%) | Equity=$%.2f",
                    symbol, reason, pnl, pnl_pct * 100, self.equity,
                )
