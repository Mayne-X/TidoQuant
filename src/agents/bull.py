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
                "You are the Bull Agent in a crypto trading system. "
                "Your job: argue why the price of {symbol} will INCREASE "
                "(for a long) or DECREASE (for a short).\n\n"
                "You have access to:\n"
                "- Trader Mayne technical structure (OTE zone, sweep, FVG)\n"
                "- Macro research context\n"
                "- Social sentiment data\n\n"
                "Build the strongest possible thesis. Be specific about levels.\n\n"
                "OUTPUT JSON:\n"
                '{\n'
                '  "thesis": "one sentence core thesis",\n'
                '  "score": 0-10 (conviction), \n'
                '  "arguments": ["arg1 with specific level", "arg2", "arg3"],\n'
                '  "key_levels": ["support1", "resistance1"]\n'
                '}'
            )
        # Round 2
        return (
            "You are the Bull Agent (Round 2). The Bear Agent has "
            "challenged your thesis. You must DEFEND your position "
            "and counter the Bear's arguments.\n\n"
            "OUTPUT JSON:\n"
            '{\n'
            '  "counter_rebuttal": "your defense against the Bear\'s main point",\n'
            '  "score": 0-10 (updated conviction),\n'
            '  "concessions": ["any valid points the Bear made that you acknowledge"]\n'
            '}'
        )

    def _packet_input(self, packet: SignalPacket) -> dict:
        base = {
            "symbol": packet.symbol,
            "direction": packet.direction,
            "entry_price": packet.entry_price,
            "current_price": packet.current_price,
        }
        if self._round == 1:
            base.update({
                "mayne": {
                    "score": packet.mayne.score,
                    "ote_points": packet.mayne.ote_points,
                    "sweep_points": packet.mayne.sweep_points,
                    "fvg_points": packet.mayne.fvg_points,
                    "detail": packet.mayne.detail,
                },
                "researcher": packet.researcher_report,
                "sentiment": {
                    "polarity": packet.sentiment_polarity,
                    "summary": packet.sentiment_summary,
                    "crowd_skew": packet.crowd_skew,
                },
            })
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
