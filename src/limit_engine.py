"""Institutional Limit Order Engine.

TidoQuant places LIMIT orders at calculated prices and waits for market
to fill them. Professional execution: minimize slippage, maker rebates.

Order lifecycle:
  PENDING  → placed at limit_price, waiting for price action
  FILLED   → candle H/L touched limit_price → position opened
  EXPIRED  → not filled within expiry window
"""
from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

from .config import STARTING_EQUITY, MAKER_FEE, LIMIT_ORDER_EXPIRY_CANDLES
from .database import close_trade, get_open_trades, latest_equity

log = logging.getLogger("tidoquant")

_FAKE_DB_PATH = os.environ.get("DB_PATH", "journal/tidoquant.db")


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    EXPIRED = "expired"


@dataclass
class LimitOrder:
    trade_id: int
    symbol: str
    direction: str
    limit_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    leverage: int
    strategy: str = "swing"
    status: OrderStatus = OrderStatus.PENDING
    entry_price: Optional[float] = None
    filled_at: Optional[str] = None
    expires_after: int = LIMIT_ORDER_EXPIRY_CANDLES
    candles_since_placed: int = 0
    time_stop_candles: Optional[int] = None
    _ts_count: int = 0


class LimitOrderEngine:
    """Manages limit orders and tracks open positions."""

    def __init__(self):
        self.equity = latest_equity()
        self._orders: Dict[int, LimitOrder] = {}
        self._open_positions: Dict[int, LimitOrder] = {}

        for row in get_open_trades():
            lo = LimitOrder(
                trade_id=row["id"],
                symbol=row["symbol"],
                direction=row["direction"],
                limit_price=row["entry_price"],
                stop_loss=row["sl"] or 0.0,
                take_profit=row["tp"] or 0.0,
                position_size=row["position_size"] or 0.0,
                leverage=row["leverage"] or 1,
                status=OrderStatus.FILLED,
                entry_price=row["entry_price"],
                filled_at=row["entered_at"],
            )
            self._open_positions[lo.trade_id] = lo

        log.info("LimitOrderEngine: equity=%.2f orders=%d positions=%d",
                 self.equity, len(self._orders), len(self._open_positions))

    def is_trading_allowed(self) -> bool:
        from .config import DRAWDOWN_CIRCUIT_BREAKER as DD, STARTING_EQUITY as SE
        return self.equity > (SE * (1 - DD))

    def get_gross_exposure(self) -> float:
        return sum(p.position_size * p.leverage for p in self._open_positions.values())

    def place_limit_order(
        self, trade_id: int, symbol: str, direction: str,
        limit_price: float, stop_loss: float, take_profit: float,
        position_size: float, leverage: int, *,
        strategy: str = "swing", time_stop_candles: Optional[int] = None,
    ) -> LimitOrder:
        order = LimitOrder(
            trade_id=trade_id, symbol=symbol, direction=direction,
            limit_price=limit_price, stop_loss=stop_loss,
            take_profit=take_profit, position_size=position_size,
            leverage=leverage, strategy=strategy,
            time_stop_candles=time_stop_candles,
        )
        self._orders[trade_id] = order
        log.info("LIMIT PLACED id=%d %s %s @ %.4f size=$%.2f lev=%d",
                 trade_id, symbol, direction, limit_price, position_size, leverage)
        return order

    def cancel_order(self, trade_id: int):
        if trade_id in self._orders:
            self._orders[trade_id].status = OrderStatus.EXPIRED
            del self._orders[trade_id]
            with sqlite3.connect(_FAKE_DB_PATH) as conn:
                conn.execute("UPDATE trades SET status='cancelled', reason='cancelled' WHERE id=?", (trade_id,))
                conn.commit()

    def tick(self, symbol: str, high: float, low: float, close: float):
        """Process candle tick against pending orders + open positions."""
        # ─── 1. Check pending orders for fills ───
        for oid, order in list(self._orders.items()):
            if order.symbol != symbol or order.status != OrderStatus.PENDING:
                continue
            order.candles_since_placed += 1

            if order.direction == "long":
                filled = low <= order.limit_price <= high
            else:
                filled = low <= order.limit_price <= high

            if filled:
                order.status = OrderStatus.FILLED
                order.entry_price = close
                order.filled_at = datetime.now(timezone.utc).isoformat()
                self._open_positions[oid] = order
                del self._orders[oid]
                fee = order.position_size * MAKER_FEE
                self.equity -= fee

                with sqlite3.connect(_FAKE_DB_PATH) as conn:
                    conn.execute("""UPDATE trades SET sl=?,tp=?,position_size=?,leverage=?,
                        entry_price=?,status='open',entered_at=datetime('now')
                        WHERE id=?""", (order.stop_loss, order.take_profit,
                                        order.position_size, order.leverage,
                                        close, oid))
                    conn.commit()
                log.info("FILLED id=%d %s @ %.4f fee=$%.4f", oid, symbol, close, fee)

            elif order.candles_since_placed >= order.expires_after:
                order.status = OrderStatus.EXPIRED
                del self._orders[oid]
                with sqlite3.connect(_FAKE_DB_PATH) as conn:
                    conn.execute("UPDATE trades SET status='cancelled',reason='limit_expired' WHERE id=?", (oid,))
                    conn.commit()
                log.info("EXPIRED id=%d %s (unfilled %d candles)", oid, symbol, order.expires_after)

        # ─── 2. Check open positions for SL/TP ───
        for pid, pos in list(self._open_positions.items()):
            if pos.symbol != symbol:
                continue
            entry = pos.entry_price or 0.0
            sl, tp = pos.stop_loss, pos.take_profit
            mult = 1 if pos.direction == "long" else -1
            size, lev = pos.position_size, pos.leverage

            sl_hit = (pos.direction == "long" and low <= sl) or \
                     (pos.direction == "short" and high >= sl)
            tp_hit = (pos.direction == "long" and high >= tp) or \
                     (pos.direction == "short" and low <= tp)

            if sl_hit or tp_hit:
                exit_px = sl if sl_hit else tp
                reason = "SL_HIT" if sl_hit else "TP_HIT"
                pnl_pct = (exit_px - entry) / max(entry, 0.001) * mult * lev
                pnl = size * pnl_pct
                self.equity += pnl
                close_trade(pid, exit_px, pnl, reason)
                del self._open_positions[pid]
                log.info("%s %s: %s PnL=$%.2f (%.1f%%) eq=$%.2f",
                         symbol, pos.direction, reason, pnl, pnl_pct * 100, self.equity)
                continue

            # Time-stop for scalpers
            if pos.strategy == "scalper" and pos.time_stop_candles:
                pos._ts_count += 1
                if pos._ts_count >= pos.time_stop_candles:
                    exit_px = close
                    pnl_pct = (exit_px - entry) / max(entry, 0.001) * mult * lev
                    pnl = size * pnl_pct
                    self.equity += pnl
                    close_trade(pid, exit_px, pnl, "TIME_STOP")
                    del self._open_positions[pid]
                    log.info("%s %s: TIME_STOP PnL=$%.2f", symbol, pos.direction, pnl)

    def open_limit_from_pipeline(self, trade_id: int, symbol: str, direction: str,
                                 entry_price: float, mayne) -> LimitOrder:
        """Helper: compute limit price from Mayne sweep level and place order."""
        if mayne and mayne.sweep_level:
            limit_price = mayne.sweep_level
        elif direction == "long":
            limit_price = entry_price * 0.998
        else:
            limit_price = entry_price * 1.002

        # Determine risk bracket
        from .config import RISK_BRACKETS, STARTING_EQUITY
        score = mayne.score if mayne else 60
        bracket = None
        for br in RISK_BRACKETS:
            if br.score_min <= score <= br.score_max:
                bracket = br
                break
        if not bracket:
            bracket = RISK_BRACKETS[0]

        risk_usd = STARTING_EQUITY * bracket.risk_pct
        # Compute stop loss distance (in price terms)
        diff = abs(entry_price - limit_price) or entry_price * 0.005  # 0.5% min
        sl_distance = entry_price * 0.015  # 1.5% default
        sl = limit_price - sl_distance if direction == "long" else limit_price + sl_distance
        tp_distance = sl_distance * 2  # 2:1 RR
        tp = limit_price + tp_distance if direction == "long" else limit_price - tp_distance
        position_size = risk_usd  # simplified

        return self.place_limit_order(
            trade_id, symbol, direction, limit_price, sl, tp,
            position_size, bracket.leverage,
        )
