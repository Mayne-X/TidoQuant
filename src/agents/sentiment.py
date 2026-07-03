"""Sentiment Agent — crowd positioning, funding rate extremes, social polarity."""
from __future__ import annotations

from ..core.signal_packet import SignalPacket
from .base_agent import BaseAgent


class SentimentAgent(BaseAgent):
    name = "sentiment"

    def system_prompt(self) -> str:
        return (
            "You are the Sentiment Agent in a crypto trading system. "
            "You analyze crowd behavior and market sentiment indicators.\n\n"
            "Focus on:\n"
            "- Funding rate extremes (above 0.05% = crowded long)\n"
            "- Long/short ratio skew (above 70% = crowded)\n"
            "- General market fear/greed context\n\n"
            "OUTPUT JSON:\n"
            '{\n'
            '  "polarity": -1.0 to 1.0 (negative = bearish crowd, positive = bullish crowd),\n'
            '  "summary": "1-2 sentence description of crowd positioning",\n'
            '  "crowd_skew": "bullish" | "bearish" | "neutral",\n'
            '  "funding_warning": "none" | "longs_crowded" | "shorts_crowded"\n'
            '}'
        )

    def _packet_input(self, packet: SignalPacket) -> dict:
        return {
            "symbol": packet.symbol,
            "direction": packet.direction,
            "funding_rate": packet.funding_rate,
            "long_short_ratio": packet.long_short_ratio[-5:] if packet.long_short_ratio else [],
            "entry_price": packet.entry_price,
            "current_price": packet.current_price,
        }

    def enrich(self, packet: SignalPacket, result: dict) -> SignalPacket:
        packet.sentiment_polarity = result.get("polarity")
        packet.sentiment_summary = result.get("summary", "")
        packet.crowd_skew = result.get("crowd_skew", "neutral")
        return packet
