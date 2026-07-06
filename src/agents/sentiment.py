"""Sentiment Agent — crowd positioning, funding rate extremes, social polarity."""
from __future__ import annotations

from ..core.signal_packet import SignalPacket
from .base_agent import BaseAgent


class SentimentAgent(BaseAgent):
    name = "sentiment"

    def system_prompt(self) -> str:
        return (
            "You are the Sentiment Agent in a dual-strategy crypto trading system. "
            "The system runs SWING (1h/4h/12h) and SCALPER (1m/5m/15m/30m) strategies. "
            "You analyze crowd behavior and market sentiment indicators.\n\n"
            "Focus on:\n"
            "- Funding rate extremes (above 0.05% = crowded longs, below -0.05% = crowded shorts)\n"
            "- Long/short ratio skew (above 70% longs = crowded, below 30% = crowded shorts)\n"
            "- Whether the crowd is leaning WITH or AGAINST the proposed trade direction\n"
            "- For scalpers: micro-sentiment shifts on shortest timeframes\n\n"
            "OUTPUT JSON:\n"
            '{\n'
            '  "polarity": -1.0 to 1.0 (negative = bearish crowd, positive = bullish crowd),\n'
            '  "summary": "1-2 sentence description of crowd positioning and whether it supports or opposes the direction",\n'
            '  "crowd_skew": "bullish" | "bearish" | "neutral",\n'
            '  "funding_warning": "none" | "longs_crowded" | "shorts_crowded"\n'
            '}'
        )

    def _packet_input(self, packet: SignalPacket) -> dict:
        ctx = {
            "symbol": packet.symbol,
            "direction": packet.direction,
            "strategy": packet.strategy_label,
            "funding_rate": packet.funding_rate,
            "long_short_ratio": packet.long_short_ratio[-5:] if packet.long_short_ratio else [],
            "entry_price": packet.entry_price,
            "current_price": packet.current_price,
            "price_vs_entry_pct": round((packet.current_price / packet.entry_price - 1) * 100, 2),
        }
        if packet.strategy == "scalper":
            ctx["filter"] = packet.filter_context
            ctx["scalper"] = packet.scalper_context
        return ctx

    def enrich(self, packet: SignalPacket, result: dict) -> SignalPacket:
        packet.sentiment_polarity = result.get("polarity")
        packet.sentiment_summary = result.get("summary", "")
        packet.crowd_skew = result.get("crowd_skew", "neutral")
        return packet
