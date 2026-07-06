"""Scalper Mayne Scorer — low-timeframe version for 1m/5m/15m/30m.

Adapts the same OTE+Sweep+FVG framework to micro-structure scalping.
Uses 1h as HTF bias filter: only take scalps in dominant HTF direction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .binance_client import Candle
from .config import SCALPER_TF_WEIGHTS, SCALPER_PIVOT_DEPTH

from .indicators import find_swings, calculate_ote_score, detect_fvg_mitigated, detect_sweep


@dataclass
class ScalperResult:
    score: int
    passed_gate: bool
    direction: str
    htf_bias_aligned: bool = False
    sweep_detected: bool = False
    fvg_detected: bool = False
    ote_aligned: bool = False
    micro_sweep_level: Optional[float] = None
    micro_fvg_top: Optional[float] = None
    micro_fvg_bottom: Optional[float] = None
    limit_price: Optional[float] = None
    detail: str = ""
    tf_scores: Dict[str, int] = field(default_factory=dict)


def score_scalper_mayne(
    lt_candles: Dict[str, List[Candle]],   # {"1m": [...], "5m": [...], "15m": [...], "30m": [...]}
    htf_bias_candles: List[Candle],        # 1h candles for bias
    entry_candles: List[Candle],           # 1m candles for entry
    sweep_candles: List[Candle],           # 1m candles for sweep
    direction: str,
) -> ScalperResult:
    is_long = direction == "long"
    price = entry_candles[-1].close if entry_candles else 0.0
    score = 0
    ote_pts = sweep_pts = fvg_pts = 0
    tf_scores: Dict[str, int] = {}
    details: List[str] = []
    sweep_level = fvg_top = fvg_bottom = None
    sweep_detected = False
    fvg_detected = False
    ote_aligned = False
    sweep_pts = 0
    fvg_pts = 0

    # ─── 0. HTF Bias Check (1h) ───
    bias_aligned = True
    if htf_bias_candles and len(htf_bias_candles) >= 20:
        htf_swings = find_swings(htf_bias_candles, pivot_depth=3)
        if htf_swings and len(htf_swings) >= 2:
            last_swing = htf_swings[-1][1]
            if is_long and price < last_swing.open * 0.99:
                bias_aligned = False  # 1h is bearish
            elif not is_long and price > last_swing.open * 1.01:
                bias_aligned = False  # 1h is bullish
    if bias_aligned:
        details.append("HTF bias aligned")
    else:
        details.append("HTF bias MISALIGNED (filtered)")

    # ─── 1. Multi-TF OTE (scored on 1m/5m/15m/30m) ───
    tf_weights = {t[0]: t[1] for t in SCALPER_TF_WEIGHTS}

    for tf_label, candles in lt_candles.items():
        swings = find_swings(candles, pivot_depth=SCALPER_PIVOT_DEPTH)
        pts = 0
        if swings:
            last_type, last_c = swings[-1]
            if (is_long and last_type == "high") or (not is_long and last_type == "low"):
                ote_val = calculate_ote_score(last_c.high, last_c.low, price, is_long)
                if ote_val > 0:
                    pts = int(ote_val * 25)
                    details.append(f"{tf_label}: OTE {pts}/25")
        tf_scores[tf_label] = pts

    weighted = sum(pts * tf_weights.get(tf, 0) for tf, pts in tf_scores.items())
    ote_pts = int(weighted)
    if ote_pts > 0:
        ote_aligned = True

    # ─── 2. Micro Liquidity Sweep (1m candles) ───
    local_swings = find_swings(sweep_candles, pivot_depth=1)
    if local_swings:
        level = local_swings[-1][1].low if is_long else local_swings[-1][1].high
        sweep_level = level
        is_high = direction == "short"
        if detect_sweep(entry_candles, level, is_high):
            sweep_pts = 25
            sweep_detected = True
            details.append(f"micro sweep {sweep_pts}/25 @ {level:.2f}")

    # ─── 3. Micro FVG ───
    fvgs = detect_fvg_mitigated(entry_candles)
    for fvg in fvgs:
        if not fvg["mitigated"]:
            if (is_long and fvg["type"] == "bullish") or \
               (not is_long and fvg["type"] == "bearish"):
                fvg_pts = 25
                fvg_detected = True
                fvg_top = fvg["top"]
                fvg_bottom = fvg["bottom"]
                details.append(f"micro FVG {fvg_pts}/25")
                break

    # ─── Score ───
    if not bias_aligned:
        score = min(50, ote_pts + sweep_pts + fvg_pts)
        passed = False
        details.append("DENIED — HTF bias mismatch")
    else:
        score = ote_pts + sweep_pts + fvg_pts
        passed = score >= 60

    # Limit price: best entry
    limit_price = sweep_level if sweep_level else (price * 0.999 if is_long else price * 1.001)

    return ScalperResult(
        score=min(100, score),
        passed_gate=passed,
        direction=direction,
        htf_bias_aligned=bias_aligned,
        sweep_detected=sweep_detected,
        fvg_detected=fvg_detected,
        ote_aligned=ote_aligned,
        micro_sweep_level=sweep_level,
        micro_fvg_top=fvg_top,
        micro_fvg_bottom=fvg_bottom,
        limit_price=limit_price,
        detail=" | ".join(details) if details else "no scalper confluence",
        tf_scores=tf_scores,
    )
