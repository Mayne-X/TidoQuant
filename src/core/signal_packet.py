"""Shared state objects passed through the agent pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MayneResult:
    score: int                          # 0-75
    passed_gate: bool                   # score >= 60
    direction: str                      # "long" | "short"
    ote_points: int = 0
    sweep_points: int = 0
    fvg_points: int = 0
    swing_high: Optional[float] = None
    swing_low: Optional[float] = None
    sweep_level: Optional[float] = None
    fvg_top: Optional[float] = None
    fvg_bottom: Optional[float] = None
    detail: str = ""                    # human-readable summary for LLM context


@dataclass
class SignalPacket:
    symbol: str
    direction: str
    mayne: MayneResult

    entry_price: float
    current_price: float
    htf_candles: list = field(default_factory=list)       # raw klines for agents
    ltf_candles: list = field(default_factory=list)
    entry_candles: list = field(default_factory=list)

    funding_rate: float = 0.0
    mark_price: float = 0.0
    open_interest: list = field(default_factory=list)
    long_short_ratio: list = field(default_factory=list)

    # Populated by Researcher
    researcher_report: Optional[str] = None
    news_headlines: List[str] = field(default_factory=list)
    macro_regime: Optional[str] = None
    oi_trend: Optional[str] = None

    # Populated by Sentiment
    sentiment_polarity: Optional[float] = None
    sentiment_summary: Optional[str] = None
    crowd_skew: Optional[str] = None

    # Populated by Bull (R1)
    bull_thesis_r1: Optional[str] = None
    bull_score_r1: Optional[int] = None
    bull_arguments_r1: List[str] = field(default_factory=list)

    # Populated by Bear (R1)
    bear_rebuttal_r1: Optional[str] = None
    bear_score_r1: Optional[int] = None
    bear_risks_r1: List[str] = field(default_factory=list)

    # Populated by Bull (R2)
    bull_counter_rebuttal: Optional[str] = None
    bull_score_r2: Optional[int] = None

    # Populated by Bear (R2)
    bear_final_objection: Optional[str] = None
    bear_score_r2: Optional[int] = None

    # Populated by Treasury
    risk_pct: Optional[float] = None
    leverage: Optional[int] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size_usd: Optional[float] = None
    treasury_note: Optional[str] = None

    # Populated by Manager
    manager_decision: Optional[str] = None    # "GO" | "NO-GO"
    manager_confidence: Optional[int] = None  # 0-100
    manager_reasoning: Optional[str] = None

    # Internal tracking
    agent_errors: List[str] = field(default_factory=list)

    @property
    def total_confidence(self) -> int:
        return self.mayne.score + (self.mayne.score if self.manager_confidence is None else 0)

    def debate_transcript(self) -> str:
        """Collapse all debate rounds into a single string for DB logging."""
        parts = []
        if self.bull_thesis_r1:
            parts.append(f"[BULL R1] Score {self.bull_score_r1}: {self.bull_thesis_r1}")
        if self.bear_rebuttal_r1:
            parts.append(f"[BEAR R1] Score {self.bear_score_r1}: {self.bear_rebuttal_r1}")
        if self.bull_counter_rebuttal:
            parts.append(f"[BULL R2] Score {self.bull_score_r2}: {self.bull_counter_rebuttal}")
        if self.bear_final_objection:
            parts.append(f"[BEAR R2] Score {self.bear_score_r2}: {self.bear_final_objection}")
        return "\n".join(parts)
