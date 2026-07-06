"""Researcher Agent — macro context, news sentiment, OI trends."""
from __future__ import annotations

import json
from ..core.signal_packet import SignalPacket
from .base_agent import BaseAgent


class ResearcherAgent(BaseAgent):
    name = "researcher"

    def system_prompt(self) -> str:
        return (
            "You are the Researcher Agent in a dual-strategy crypto trading system. "
            "The system runs SWING (1h/4h/12h positional) and SCALPER (1m/5m/15m/30m micro) strategies. "
            "You receive raw market data (price, funding, open interest, news, mayne score). "
            "Your job is to provide a concise, objective macro/micro assessment.\n\n"
            "Focus on:\n"
            "- Overall market regime and risk appetite\n"
            "- Open interest trend (rising = momentum, falling = indecision)\n"
            "- Funding rate extremes (contango/backwardation)\n"
            "- Key headlines or events affecting the asset\n\n"
            "Do NOT recommend trades — only provide context.\n\n"
            "OUTPUT JSON:\n"
            '{\n'
            '  "macro_regime": "risk-on" | "risk-off" | "neutral",\n'
            '  "oi_trend": "rising" | "falling" | "flat",\n'
            '  "report": "2-3 sentence assessment of current conditions, mentioning notable volatility or market structure points",\n'
            '  "key_headlines": ["headline1", "headline2"]\n'
            '}'
        )

    def _packet_input(self, packet: SignalPacket) -> dict:
        ctx = {
            "symbol": packet.symbol,
            "direction": packet.direction,
            "strategy": packet.strategy_label,
            "entry_price": packet.entry_price,
            "current_price": packet.current_price,
            "funding_rate": packet.funding_rate,
            "mayne_score": packet.mayne.score,
            "mayne_detail": packet.mayne.detail,
            "open_interest_trend": packet.oi_trend or "unknown",
        }
        if packet.strategy == "scalper":
            ctx["filter"] = packet.filter_context
            ctx["scalper"] = packet.scalper_context
        return ctx

    def enrich(self, packet: SignalPacket, result: dict) -> SignalPacket:
        packet.macro_regime = result.get("macro_regime", "neutral")
        packet.oi_trend = result.get("oi_trend", "flat")
        packet.researcher_report = result.get("report", "")
        packet.news_headlines = result.get("key_headlines", [])
        return packet
