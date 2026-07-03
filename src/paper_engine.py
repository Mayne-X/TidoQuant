"""Paper Trading Engine.

Handles accounting, equity tracking, trade simulation, and fee deduction.
Does NOT poll the market — the main loop drives the state updates.
"""
from __future__ import annotations
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional
from .config import STARTING_EQUITY, TAKER_FEE, DRAWDOWN_CIRCUIT_BREAKER

class PaperEngine:
    def __init__(self, journal_path: str):
        self.equity = STARTING_EQUITY
        self.journal_path = journal_path
        self.open_positions: List[Dict] = []
        self.log = logging.getLogger("tidoquant")

    def is_trading_allowed(self) -> bool:
        # Check circuit breaker
        return self.equity > (STARTING_EQUITY * (1 - DRAWDOWN_CIRCUIT_BREAKER))

    def open_position(self, signal: Dict):
        """Register a new trade signal."""
        # Simple simulation: Assume limit fill at entry price.
        # Deduct fee immediately.
        fee = signal["position_size"] * TAKER_FEE
        self.equity -= fee
        
        pos = {
            **signal,
            "entry_time": datetime.utcnow().isoformat(),
            "status": "open",
            "fee_paid": fee
        }
        self.open_positions.append(pos)
        self.log.info("Position opened: %s", signal["symbol"])

    def update_price(self, symbol: str, current_price: float):
        """Update market price for open positions, check SL/TP."""
        for pos in self.open_positions[:]:
            if pos["symbol"] != symbol:
                continue
                
            # Check Stop Loss
            if (pos["direction"] == "long" and current_price <= pos["sl"]) or \
               (pos["direction"] == "short" and current_price >= pos["sl"]):
                self._close_position(pos, "SL_HIT", current_price)
                
            # Check Take Profit
            elif (pos["direction"] == "long" and current_price >= pos["tp"]) or \
                 (pos["direction"] == "short" and current_price <= pos["tp"]):
                self._close_position(pos, "TP_HIT", current_price)

    def _close_position(self, pos: Dict, reason: str, exit_price: float):
        # Calc PnL
        size = pos["position_size"]
        leverage = pos["leverage"]
        entry = pos["entry"]
        
        # PnL % = (Exit - Entry) / Entry * Dir * Lev
        dir_mult = 1 if pos["direction"] == "long" else -1
        pnl_pct = (exit_price - entry) / entry * dir_mult * leverage
        
        profit = size * pnl_pct
        self.equity += profit
        
        pos.update({
            "status": "closed",
            "reason": reason,
            "exit_price": exit_price,
            "pnl": profit,
            "exit_time": datetime.utcnow().isoformat()
        })
        
        # Log to journal
        with open(self.journal_path, "a") as f:
            f.write(json.dumps(pos) + "\n")
            
        self.open_positions.remove(pos)
        self.log.info("Position closed: %s | PnL: %.2f | Equity: %.2f", 
                     pos["symbol"], profit, self.equity)
