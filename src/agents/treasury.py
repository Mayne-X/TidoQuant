"""Treasury Agent — risk-constrained position sizing and SL/TP placement."""
from __future__ import annotations

from ..config import RISK_BRACKETS, STARTING_EQUITY
from ..core.signal_packet import SignalPacket
from .base_agent import BaseAgent


class TreasuryAgent(BaseAgent):
    name = "treasury"

    def system_prompt(self) -> str:
        return (
            "You are the Treasury Agent in a crypto trading system. "
            "You are a conservative risk manager.\n\n"
            "Your job: Given the debate outcome (Bull vs Bear scores) "
            "and current equity, determine:\n"
            "- Position size (% of equity to risk)\n"
            "- Leverage (1x-5x)\n"
            "- Stop-loss level (as a price, not %)\n"
            "- Take-profit level (as a price, must be at least 2x the risk)\n\n"
            "Rules:\n"
            "- Higher Bull score relative to Bear = more conviction = larger size\n"
            "- Never risk more than 3% of equity on a single trade\n"
            "- Leverage must be between 1x and 5x\n"
            "- R:R ratio must be at least 2:1\n\n"
            "OUTPUT JSON:\n"
            '{\n'
            '  "risk_pct": 0.01 to 0.03 (e.g. 0.02 = 2%),\n'
            '  "leverage": 1 to 5,\n'
            '  "stop_loss_price": 12345.0,\n'
            '  "take_profit_price": 12500.0,\n'
            '  "note": "brief justification"\n'
            '}'
        )

    def _packet_input(self, packet: SignalPacket) -> dict:
        # Compute a composite conviction score from Bull/Bear debate
        bull_avg = (
            (packet.bull_score_r1 or 0) + (packet.bull_score_r2 or 0)
        ) / max(1, (1 if packet.bull_score_r1 is not None else 0) +
                       (1 if packet.bull_score_r2 is not None else 0))
        bear_avg = (
            (packet.bear_score_r1 or 0) + (packet.bear_score_r2 or 0)
        ) / max(1, (1 if packet.bear_score_r1 is not None else 0) +
                       (1 if packet.bear_score_r2 is not None else 0))
        net = bull_avg - bear_avg  # -10 to +10

        return {
            "symbol": packet.symbol,
            "direction": packet.direction,
            "entry_price": packet.entry_price,
            "current_price": packet.current_price,
            "equity": STARTING_EQUITY,
            "bull_avg_score": round(bull_avg, 1),
            "bear_avg_score": round(bear_avg, 1),
            "net_conviction": round(net, 1),
            "mayne_score": packet.mayne.score,
        }

    def enrich(self, packet: SignalPacket, result: dict) -> SignalPacket:
        packet.risk_pct = result.get("risk_pct", 0.01)
        packet.leverage = result.get("leverage", 1)
        packet.stop_loss = result.get("stop_loss_price")
        packet.take_profit = result.get("take_profit_price")
        packet.treasury_note = result.get("note", "")
        # Position size = equity * risk_pct * leverage
        packet.position_size_usd = (
            STARTING_EQUITY * packet.risk_pct * packet.leverage
        )
        return packet
