"""Manager Agent — final arbiter. Reads all agent outputs, weighs evidence, GO/NO-GO."""
from __future__ import annotations

from ..core.signal_packet import SignalPacket
from .base_agent import BaseAgent


class ManagerAgent(BaseAgent):
    name = "manager"

    def system_prompt(self) -> str:
        return (
            "You are the Manager Agent — the FINAL DECISION-MAKER for TidoQuant.\n\n"
            "You receive complete reports from: Researcher, Sentiment, Bull (R1+R2), "
            "Bear (R1+R2), and Treasury.\n\n"
            "Your job:\n"
            "1. Fact-check each agent's claims against the raw data\n"
            "2. Weigh Bull vs Bear arguments — whose reasoning is stronger?\n"
            "3. Check Treasury's risk calculation — does it respect the bracket?\n"
            "4. Make FINAL DECISION\n\n"
            "Decision logic:\n"
            "- GO: The technical structure is sound, the Bull made stronger arguments,\n"
            "  and the Bear's risks are manageable with the proposed SL.\n"
            "- NO-GO: The Bear raised valid structural concerns that weren't refuted,\n"
            "  or the risk/reward doesn't justify the trade.\n"
            "- Consider performance_briefing: if streak is losing or asset has high loss rate, be significantly more cautious.\n\n"
            "IMPORTANT: Return ONLY a valid JSON object. Do not include any introductory or concluding text. Do not use Markdown code blocks (e.g., no ```json). Your response must start with { and end with }.\n\n"
            "OUTPUT JSON:\n"
            '{\n'
            '  "decision": "GO" | "NO-GO",\n'
            '  "confidence": 0-100,\n'
            '  "reasoning": "step-by-step analysis of each agent output",\n'
            '  "rejected_arguments": ["arguments you dismissed and why"],\n'
            '  "override_note": "any parameter overrides or warnings"\n'
            '}'
        )

    def _packet_input(self, packet: SignalPacket) -> dict:
        data = {
            "symbol": packet.symbol,
            "direction": packet.direction,
            "entry_price": packet.entry_price,
            "current_price": packet.current_price,
            "mayne": {
                "score": packet.mayne.score,
                "detail": packet.mayne.detail,
            },
            "researcher": {
                "report": packet.researcher_report,
                "macro_regime": packet.macro_regime,
                "oi_trend": packet.oi_trend,
            },
            "sentiment": {
                "polarity": packet.sentiment_polarity,
                "summary": packet.sentiment_summary,
                "crowd_skew": packet.crowd_skew,
            },
            "bull": {
                "r1_thesis": packet.bull_thesis_r1,
                "r1_score": packet.bull_score_r1,
                "r1_arguments": packet.bull_arguments_r1,
                "r2_counter_rebuttal": packet.bull_counter_rebuttal,
                "r2_score": packet.bull_score_r2,
            },
            "bear": {
                "r1_rebuttal": packet.bear_rebuttal_r1,
                "r1_score": packet.bear_score_r1,
                "r1_risks": packet.bear_risks_r1,
                "r2_final_objection": packet.bear_final_objection,
                "r2_score": packet.bear_score_r2,
            },
            "treasury": {
                "risk_pct": packet.risk_pct,
                "leverage": packet.leverage,
                "stop_loss": packet.stop_loss,
                "take_profit": packet.take_profit,
                "position_size_usd": packet.position_size_usd,
                "note": packet.treasury_note,
            },
        }
        if packet.memory_briefing:
            data["performance_briefing"] = packet.memory_briefing
        return data

    def enrich(self, packet: SignalPacket, result: dict) -> SignalPacket:
        packet.manager_decision = result.get("decision", "NO-GO")
        packet.manager_confidence = result.get("confidence", 0)
        packet.manager_reasoning = result.get("reasoning", "")
        return packet
