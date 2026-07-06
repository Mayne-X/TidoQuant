"""Manager Agent — final arbiter. Reads all agent outputs, weighs evidence, GO/NO-GO."""
from __future__ import annotations

from ..core.signal_packet import SignalPacket
from .base_agent import BaseAgent


class ManagerAgent(BaseAgent):
    name = "manager"

    def system_prompt(self) -> str:
        return (
            "You are the Manager Agent — the FINAL DECISION-MAKER for TidoQuant.\n"
            "You oversee a dual-strategy system: SWING (1h/4h/12h positional) "
            "and SCALPER (1m/5m/15m/30m micro).\n\n"
            "You receive complete reports from all 8 agents and the performance memory briefing.\n\n"
            "Your job:\n"
            "1. Confirm the strategy context (swing vs scalper) and evaluate whether the "
            "technical setup matches the strategy's timeframe\n"
            "2. Fact-check each agent's claims against the raw data provided\n"
            "3. Weigh Bull vs Bear arguments — whose reasoning is more specific and evidence-based?\n"
            "4. Check Treasury's risk calculation — does it respect the strategy's risk brackets?\n"
            "5. For scalpers: verify that the filter chain passed, scalper Mayne score is adequate, "
            "and the limit price is reasonable\n"
            "6. Make FINAL DECISION\n\n"
            "Decision logic:\n"
            "- GO: Technical structure is sound, Bull made stronger arguments, "
            "Bear's risks are manageable with the proposed SL, Treasury sizing is appropriate\n"
            "- NO-GO: Bear raised valid structural concerns not refuted, R:R doesn't justify, "
            "or performance_briefing shows high loss rate on this asset\n"
            "- Consider performance_briefing: losing streak → more cautious; "
            "asset with >60% loss rate → significantly reduce confidence\n\n"
            "IMPORTANT: Return ONLY a valid JSON object. No markdown, no code fences. Start with { end with }.\n\n"
            "OUTPUT JSON:\n"
            '{\n'
            '  "decision": "GO" | "NO-GO",\n'
            '  "confidence": 0-100,\n'
            '  "reasoning": "step-by-step analysis citing specific agent outputs and numbers",\n'
            '  "rejected_arguments": ["arguments you dismissed and why"],\n'
            '  "override_note": "any parameter overrides or warnings for the execution engine"\n'
            '}'
        )

    def _packet_input(self, packet: SignalPacket) -> dict:
        entry = packet.scalper_result.limit_price if (packet.strategy == "scalper" and packet.scalper_result and packet.scalper_result.limit_price) else packet.entry_price

        data = {
            "symbol": packet.symbol,
            "direction": packet.direction,
            "strategy": packet.strategy_label,
            "entry_price": entry,
            "current_price": packet.current_price,
            "price_slippage_pct": round((packet.current_price / entry - 1) * 100, 2) if entry else 0,
            "mayne": {
                "score": packet.mayne.score,
                "passed_gate": packet.mayne.passed_gate,
                "detail": packet.mayne.detail,
                "tf_scores": packet.mayne.tf_scores,
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
        if packet.strategy == "scalper":
            data["filter"] = packet.filter_context
            data["scalper"] = packet.scalper_context
            if packet.time_stop_candles:
                data["time_stop_candles"] = packet.time_stop_candles
        if packet.memory_briefing:
            data["performance_briefing"] = packet.memory_briefing
        return data

    def enrich(self, packet: SignalPacket, result: dict) -> SignalPacket:
        packet.manager_decision = result.get("decision", "NO-GO")
        packet.manager_confidence = result.get("confidence", 0)
        packet.manager_reasoning = result.get("reasoning", "")
        return packet
