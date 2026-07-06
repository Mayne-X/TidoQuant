"""Shared state objects passed through the agent pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..filter_chain import FilterResult

if TYPE_CHECKING:
    from ..scalper_mayne import ScalperResult


@dataclass
class MayneResult:
    score: int
    passed_gate: bool
    direction: str
    ote_points: int = 0
    sweep_points: int = 0
    fvg_points: int = 0
    swing_high: Optional[float] = None
    swing_low: Optional[float] = None
    sweep_level: Optional[float] = None
    fvg_top: Optional[float] = None
    fvg_bottom: Optional[float] = None
    tf_scores: dict = field(default_factory=dict)
    detail: str = ""


@dataclass
class SignalPacket:
    symbol: str
    direction: str
    mayne: MayneResult

    entry_price: float
    current_price: float
    tf_candles: dict = field(default_factory=dict)
    sweep_candles: list = field(default_factory=list)
    entry_candles: list = field(default_factory=list)

    # Scalper data
    strategy: str = "swing"
    scalper_result: Optional[ScalperResult] = None
    scalper_lt_candles: dict = field(default_factory=dict)
    scalper_htf_candles: list = field(default_factory=list)
    scalper_sweep_candles: list = field(default_factory=list)
    scalper_entry_candles: list = field(default_factory=list)
    filter_result: Optional[FilterResult] = None
    time_stop_candles: Optional[int] = None

    funding_rate: float = 0.0
    mark_price: float = 0.0
    open_interest: list = field(default_factory=list)
    long_short_ratio: list = field(default_factory=list)

    researcher_report: Optional[str] = None
    news_headlines: List[str] = field(default_factory=list)
    macro_regime: Optional[str] = None
    oi_trend: Optional[str] = None

    sentiment_polarity: Optional[float] = None
    sentiment_summary: Optional[str] = None
    crowd_skew: Optional[str] = None

    bull_thesis_r1: Optional[str] = None
    bull_score_r1: Optional[int] = None
    bull_arguments_r1: List[str] = field(default_factory=list)

    bear_rebuttal_r1: Optional[str] = None
    bear_score_r1: Optional[int] = None
    bear_risks_r1: List[str] = field(default_factory=list)

    bull_counter_rebuttal: Optional[str] = None
    bull_score_r2: Optional[int] = None

    bear_final_objection: Optional[str] = None
    bear_score_r2: Optional[int] = None

    risk_pct: Optional[float] = None
    leverage: Optional[int] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size_usd: Optional[float] = None
    treasury_note: Optional[str] = None

    manager_decision: Optional[str] = None
    manager_confidence: Optional[int] = None
    manager_reasoning: Optional[str] = None

    trade_id: int = -1
    agent_errors: List[str] = field(default_factory=list)
    memory_briefing: Optional[str] = None

    @property
    def total_confidence(self) -> int:
        return self.mayne.score + (self.manager_confidence or 0)

    @property
    def strategy_label(self) -> str:
        return "SCALPER (1m/5m/15m/30m)" if self.strategy == "scalper" else "SWING (1h/4h/12h)"

    @property
    def filter_context(self) -> dict:
        if not self.filter_result:
            return {}
        return {
            "filter_score": self.filter_result.score,
            "filter_passed": self.filter_result.passed,
            "filter_details": self.filter_result.details,
            "reject_reason": self.filter_result.reject_reason,
        }

    @property
    def scalper_context(self) -> dict:
        if not self.scalper_result:
            return {}
        return {
            "scalper_score": self.scalper_result.score,
            "scalper_passed": self.scalper_result.passed_gate,
            "scalper_detail": self.scalper_result.detail,
            "limit_price": self.scalper_result.limit_price,
            "htf_bias_aligned": self.scalper_result.htf_bias_aligned,
            "sweep_detected": self.scalper_result.sweep_detected,
            "fvg_detected": self.scalper_result.fvg_detected,
            "micro_sweep_level": self.scalper_result.micro_sweep_level,
            "tf_scores": self.scalper_result.tf_scores,
        }

    def debate_transcript(self) -> str:
        parts = []
        if self.researcher_report:
            parts.append(f"[RESEARCHER] Macro: {self.macro_regime} | OI: {self.oi_trend}")
            parts.append(f"Report: {self.researcher_report}")
        if self.sentiment_summary:
            parts.append(f"[SENTIMENT] Polarity: {self.sentiment_polarity} | Skew: {self.crowd_skew}")
            parts.append(f"Summary: {self.sentiment_summary}")
        if self.bull_thesis_r1:
            parts.append(f"[BULL R1] Score {self.bull_score_r1}: {self.bull_thesis_r1}")
        if self.bear_rebuttal_r1:
            parts.append(f"[BEAR R1] Score {self.bear_score_r1}: {self.bear_rebuttal_r1}")
        if self.bull_counter_rebuttal:
            parts.append(f"[BULL R2] Score {self.bull_score_r2}: {self.bull_counter_rebuttal}")
        if self.bear_final_objection:
            parts.append(f"[BEAR R2] Score {self.bear_score_r2}: {self.bear_final_objection}")
        if self.treasury_note:
            parts.append(f"[TREASURY] Risk: {self.risk_pct*100}% | Lev: {self.leverage}x | SL: {self.stop_loss} | TP: {self.take_profit}")
            parts.append(f"Note: {self.treasury_note}")
        if self.manager_reasoning:
            parts.append(f"[MANAGER] Decision: {self.manager_decision} | Conf: {self.manager_confidence}/100")
            parts.append(f"Reasoning: {self.manager_reasoning}")
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Full serializable dict for activity logging."""
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "strategy": self.strategy,
            "entry_price": self.entry_price,
            "mayne_score": self.mayne.score,
            "mayne_detail": self.mayne.detail,
            "filter_score": self.filter_result.score if self.filter_result else None,
            "filter_passed": self.filter_result.passed if self.filter_result else None,
            "scalper_score": self.scalper_result.score if self.scalper_result else None,
            "manager_decision": self.manager_decision,
            "manager_confidence": self.manager_confidence,
            "limit_price": self.scalper_result.limit_price if self.scalper_result else None,
        }
