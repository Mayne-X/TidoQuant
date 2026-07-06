"""Treasury Agent — risk-constrained position sizing and SL/TP placement."""
from __future__ import annotations

from ..config import RISK_BRACKETS, STARTING_EQUITY
from ..core.signal_packet import SignalPacket
from .base_agent import BaseAgent


class TreasuryAgent(BaseAgent):
    name = "treasury"

    def system_prompt(self) -> str:
        return (
            "You are the Treasury Agent — the risk manager in a dual-strategy crypto trading system.\n\n"
            "The strategy is indicated in your input data:\n"
            "- SWING (1h/4h/12h): larger size, wider SL, 1x-5x leverage\n"
            "- SCALPER (1m/5m/15m/30m): smaller size, tighter SL, 2x-4x leverage, time-stop risk\n\n"
            "Your job: Given the debate outcome (Bull vs Bear scores), current equity, "
            "and strategy, determine:\n"
            "- Position size (% of equity to risk on this trade)\n"
            "- Leverage (appropriate for the strategy)\n"
            "- Stop-loss level (as a price, not %)\n"
            "- Take-profit level (as a price, must be at least 2x the risk distance)\n\n"
            "Rules:\n"
            "- SWING: risk_pct 1%-3%, leverage 1x-5x\n"
            "- SCALPER: risk_pct 0.5%-1.5%, leverage 2x-4x\n"
            "- Higher Bull score relative to Bear = more conviction = larger size\n"
            "- R:R ratio must be at least 2:1\n"
            "- If performance_briefing indicates a losing streak or poor asset performance, reduce risk_pct\n"
            "- For scalpers: if a limit_price is provided, use it as the entry (not current_price)\n\n"
            "OUTPUT JSON:\n"
            '{\n'
            '  "risk_pct": 0.005 to 0.03 (e.g. 0.02 = 2% of equity at risk),\n'
            '  "leverage": 1 to 5,\n'
            '  "stop_loss_price": 12345.0,\n'
            '  "take_profit_price": 12500.0,\n'
            '  "note": "brief justification citing key numbers"\n'
            '}'
        )

    def _packet_input(self, packet: SignalPacket) -> dict:
        bull_avg = (
            (packet.bull_score_r1 or 0) + (packet.bull_score_r2 or 0)
        ) / max(1, (1 if packet.bull_score_r1 is not None else 0) +
                       (1 if packet.bull_score_r2 is not None else 0))
        bear_avg = (
            (packet.bear_score_r1 or 0) + (packet.bear_score_r2 or 0)
        ) / max(1, (1 if packet.bear_score_r1 is not None else 0) +
                       (1 if packet.bear_score_r2 is not None else 0))
        net = bull_avg - bear_avg

        entry = packet.scalper_result.limit_price if (packet.strategy == "scalper" and packet.scalper_result and packet.scalper_result.limit_price) else packet.entry_price

        data = {
            "symbol": packet.symbol,
            "direction": packet.direction,
            "strategy": packet.strategy_label,
            "entry_price_for_sizing": entry,
            "current_price": packet.current_price,
            "equity": STARTING_EQUITY,
            "bull_avg_score": round(bull_avg, 1),
            "bear_avg_score": round(bear_avg, 1),
            "net_conviction": round(net, 1),
            "mayne_score": packet.mayne.score,
            "mayne_detail": packet.mayne.detail,
        }
        if packet.strategy == "scalper":
            data["filter"] = packet.filter_context
            data["scalper"] = packet.scalper_context
        if packet.memory_briefing:
            data["performance_briefing"] = packet.memory_briefing
        return data

    def enrich(self, packet: SignalPacket, result: dict) -> SignalPacket:
        packet.risk_pct = result.get("risk_pct", 0.01)
        packet.leverage = result.get("leverage", 1)
        packet.stop_loss = result.get("stop_loss_price")
        packet.take_profit = result.get("take_profit_price")
        packet.treasury_note = result.get("note", "")
        entry = packet.scalper_result.limit_price if (packet.strategy == "scalper" and packet.scalper_result and packet.scalper_result.limit_price) else packet.entry_price
        packet.position_size_usd = (
            STARTING_EQUITY * packet.risk_pct * packet.leverage
        )
        return packet
