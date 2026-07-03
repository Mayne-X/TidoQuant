"""Researcher Agent — macro context, news sentiment, OI trends."""
from __future__ import annotations

import json
from ..core.signal_packet import SignalPacket
from .base_agent import BaseAgent


class ResearcherAgent(BaseAgent):
    name = "researcher"

    def system_prompt(self) -> str:
        return (
            "You are the Researcher Agent in a crypto trading system. "
            "You receive raw market data (price, funding, open interest, news). "
            "Your job is to provide a concise, objective macro assessment. "
            "Do NOT recommend trades — only provide context.\n\n"
            "OUTPUT JSON:\n"
            '{\n'
            '  "macro_regime": "risk-on" | "risk-off" | "neutral",\n'
            '  "oi_trend": "rising" | "falling" | "flat",\n'
            '  "report": "2-3 sentence summary of current market conditions",\n'
            '  "key_headlines": ["headline1", "headline2"]\n'
            '}'
        )

    def _packet_input(self, packet: SignalPacket) -> dict:
        return {
            "symbol": packet.symbol,
            "direction": packet.direction,
            "entry_price": packet.entry_price,
            "current_price": packet.current_price,
            "funding_rate": packet.funding_rate,
            "mayne_detail": packet.mayne.detail,
        }

    def enrich(self, packet: SignalPacket, result: dict) -> SignalPacket:
        packet.macro_regime = result.get("macro_regime", "neutral")
        packet.oi_trend = result.get("oi_trend", "flat")
        packet.researcher_report = result.get("report", "")
        packet.news_headlines = result.get("key_headlines", [])
        return packet
