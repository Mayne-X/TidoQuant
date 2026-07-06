"""Bear Agent — argues why the trade will FAIL.

Round 1: Read Bull's thesis. Rebut it.
Round 2: Read Bull's defense. Final objection.
"""
from __future__ import annotations

from ..core.signal_packet import SignalPacket
from .base_agent import BaseAgent


class BearAgent(BaseAgent):
    def __init__(self, ollama, round: int = 1):
        super().__init__(ollama)
        self._round = round

    @property
    def name(self) -> str:
        return f"bear_r{self._round}"

    def system_prompt(self) -> str:
        if self._round == 1:
            return (
                "You are the Bear Agent in a dual-strategy crypto trading system. "
                "The strategy is indicated in your input data — SWING or SCALPER.\n\n"
                "Your job: CHALLENGE the proposed trade. Be skeptical.\n\n"
                "Look for:\n"
                "- Hidden traps (mitigated imbalances, fake break of structure)\n"
                "- High funding = crowded trade vulnerable to liquidation cascade\n"
                "- Sweeps on low volume that indicate weakness\n"
                "- For scalpers: limit price not getting filled, time-stop risk, "
                "filter chain rejections that the Bull ignored\n"
                "- Structural weaknesses in the Bull's thesis\n\n"
                "OUTPUT JSON:\n"
                '{\n'
                '  "rebuttal": "main objection to the Bull\'s thesis, referencing specific levels",\n'
                '  "score": 0-10 (how dangerous you think this trade is, 10=very dangerous),\n'
                '  "risks": ["risk1 with specific price level", "risk2", "risk3"],\n'
                '  "invalid_conditions": ["condition that must be false for this trade to work"]\n'
                '}'
            )
        return (
            "You are the Bear Agent (Round 2). The Bull has defended "
            "their position against your initial rebuttal.\n\n"
            "You must deliver your FINAL OBJECTION. If you still think "
            "the trade is dangerous, explain why the Bull's defense "
            "was insufficient.\n\n"
            "Be specific: did the Bull actually address your risks? "
            "Or did they hand-wave?\n\n"
            "OUTPUT JSON:\n"
            '{\n'
            '  "final_objection": "your strongest remaining concern with price context",\n'
            '  "score": 0-10 (updated danger level),\n'
            '  "conceded_points": ["any valid Bull counter-arguments you accept"]\n'
            '}'
        )

    def _packet_input(self, packet: SignalPacket) -> dict:
        base = {
            "symbol": packet.symbol,
            "direction": packet.direction,
            "strategy": packet.strategy_label,
            "entry_price": packet.entry_price,
            "current_price": packet.current_price,
            "price_vs_entry_pct": round((packet.current_price / packet.entry_price - 1) * 100, 2),
        }
        if self._round == 1:
            ctx = {
                "bull_thesis": packet.bull_thesis_r1,
                "bull_arguments": packet.bull_arguments_r1,
                "bull_score": packet.bull_score_r1,
                "mayne_score": packet.mayne.score,
                "mayne_detail": packet.mayne.detail,
                "sentiment_crowd_skew": packet.crowd_skew,
                "funding_rate": packet.funding_rate,
                "macro_regime": packet.macro_regime,
                "researcher_report": packet.researcher_report,
            }
            if packet.strategy == "scalper":
                ctx["filter"] = packet.filter_context
                ctx["scalper"] = packet.scalper_context
            base.update(ctx)
        else:
            base.update({
                "bull_counter_rebuttal": packet.bull_counter_rebuttal,
                "bull_updated_score": packet.bull_score_r2,
                "my_original_rebuttal": packet.bear_rebuttal_r1,
                "my_original_risks": packet.bear_risks_r1,
            })
        return base

    def enrich(self, packet: SignalPacket, result: dict) -> SignalPacket:
        if self._round == 1:
            packet.bear_rebuttal_r1 = result.get("rebuttal", "")
            packet.bear_score_r1 = result.get("score")
            packet.bear_risks_r1 = result.get("risks", [])
        else:
            packet.bear_final_objection = result.get("final_objection", "")
            packet.bear_score_r2 = result.get("score")
        return packet
