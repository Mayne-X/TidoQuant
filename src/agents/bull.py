"""Bull Agent — argues why price will move IN the direction of the trade.

Round 1: Construct initial bullish thesis.
Round 2: Defend against Bear's rebuttal.
"""
from __future__ import annotations

from typing import List, Optional

from ..core.signal_packet import SignalPacket
from .base_agent import BaseAgent


class BullAgent(BaseAgent):
    """Bull agent supporting multi-round debate. Pass round=1 or round=2."""

    def __init__(self, ollama, round: int = 1):
        super().__init__(ollama)
        self._round = round

    @property
    def name(self) -> str:
        return f"bull_r{self._round}"

    def system_prompt(self) -> str:
        if self._round == 1:
            return (
                "You are the Bull Agent in a dual-strategy crypto trading system. "
                "The strategy is indicated in your input data — SWING (1h/4h/12h positional) "
                "or SCALPER (1m/5m/15m/30m micro).\n\n"
                "Your job: argue why the price will MOVE IN THE DIRECTION OF THE TRADE.\n\n"
                "Build the strongest possible thesis using:\n"
                "- Mayne technical structure (OTE zone, sweep, FVG, individual TF scores)\n"
                "- For scalpers: filter chain results, micro sweep/FVG levels, limit price\n"
                "- Macro research and market regime context\n"
                "- Social sentiment and crowd positioning\n\n"
                "Be specific about price levels. Reference actual numbers from the data.\n\n"
                "OUTPUT JSON:\n"
                '{\n'
                '  "thesis": "one sentence core thesis explaining WHY price will move in our direction",\n'
                '  "score": 0-10 (conviction level, 10 = highest conviction), \n'
                '  "arguments": ["arg1 with specific price level", "arg2", "arg3"],\n'
                '  "key_levels": ["key support or resistance level for this trade"]\n'
                '}'
            )
        # Round 2
        return (
            "You are the Bull Agent (Round 2) in a dual-strategy crypto trading system. "
            "The Bear Agent has challenged your Round 1 thesis. "
            "You must DEFEND your position and counter the Bear's arguments.\n\n"
            "Consider:\n"
            "- Did the Bear miss any structural advantage?\n"
            "- Is the Bear's risk overstated given the SL placement?\n"
            "- Are there new levels or data that support your case?\n\n"
            "OUTPUT JSON:\n"
            '{\n'
            '  "counter_rebuttal": "your defense against the Bear\'s main objection, referencing specific levels",\n'
            '  "score": 0-10 (updated conviction),\n'
            '  "concessions": ["any valid points the Bear made that you acknowledge"]\n'
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
            base.update({
                "mayne": {
                    "score": packet.mayne.score,
                    "passed": packet.mayne.passed_gate,
                    "ote_points": packet.mayne.ote_points,
                    "sweep_points": packet.mayne.sweep_points,
                    "fvg_points": packet.mayne.fvg_points,
                    "detail": packet.mayne.detail,
                    "tf_scores": packet.mayne.tf_scores,
                },
                "researcher_report": packet.researcher_report,
                "macro_regime": packet.macro_regime,
                "sentiment": {
                    "polarity": packet.sentiment_polarity,
                    "summary": packet.sentiment_summary,
                    "crowd_skew": packet.crowd_skew,
                },
            })
            if packet.strategy == "scalper":
                base["filter"] = packet.filter_context
                base["scalper"] = packet.scalper_context
        else:
            base.update({
                "bear_rebuttal": packet.bear_rebuttal_r1,
                "bear_risks": packet.bear_risks_r1,
                "bear_score": packet.bear_score_r1,
                "my_original_thesis": packet.bull_thesis_r1,
                "my_original_arguments": packet.bull_arguments_r1,
            })
        return base

    def enrich(self, packet: SignalPacket, result: dict) -> SignalPacket:
        if self._round == 1:
            packet.bull_thesis_r1 = result.get("thesis", "")
            packet.bull_score_r1 = result.get("score")
            packet.bull_arguments_r1 = result.get("arguments", [])
        else:
            packet.bull_counter_rebuttal = result.get("counter_rebuttal", "")
            packet.bull_score_r2 = result.get("score")
        return packet
