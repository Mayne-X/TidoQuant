"""Mayne Scorer (75% weightage) — gatekeeper of the system.

Outputs a structured MayneResult. If score < 60, pipeline does NOT start.
"""
from __future__ import annotations
from typing import List

from .binance_client import Candle
from .indicators import find_swings, calculate_ote_score, detect_fvg_mitigated, detect_sweep
from .core.signal_packet import MayneResult


def score_mayne(
    htf_candles: List[Candle],
    ltf_candles: List[Candle],
    entry_candles: List[Candle],
    direction: str,
) -> MayneResult:
    score = 0
    ote_pts = sweep_pts = fvg_pts = 0
    swing_high = swing_low = None
    sweep_level = fvg_top = fvg_bottom = None

    # 1. HTF Trend & OTE (25 Points)
    swings = find_swings(htf_candles)
    if swings:
        last_swing_type, last_swing_candle = swings[-1]
        price = entry_candles[-1].close
        is_long = (direction == "long")

        if (is_long and last_swing_type == "high") or (not is_long and last_swing_type == "low"):
            high = last_swing_candle.high
            low = last_swing_candle.low
            swing_high = high
            swing_low = low
            ote_val = calculate_ote_score(high, low, price, is_long)
            if ote_val > 0:
                ote_pts = int(ote_val * 25)

    # 2. Liquidity Sweep (25 Points)
    local_swings = find_swings(ltf_candles, pivot_depth=2)
    if local_swings:
        level = local_swings[-1][1].low if direction == "long" else local_swings[-1][1].high
        sweep_level = level
        is_high_sweep = (direction == "short")
        if detect_sweep(entry_candles, level, is_high_sweep):
            sweep_pts = 25

    # 3. Displacement & FVG (25 Points)
    fvgs = detect_fvg_mitigated(entry_candles)
    for fvg in fvgs:
        if not fvg["mitigated"]:
            if (direction == "long" and fvg["type"] == "bullish") or \
               (direction == "short" and fvg["type"] == "bearish"):
                fvg_pts = 25
                fvg_top = fvg["top"]
                fvg_bottom = fvg["bottom"]
                break

    score = ote_pts + sweep_pts + fvg_pts
    passed = score >= 60

    detail_lines = []
    if ote_pts > 0:
        detail_lines.append(f"OTE in zone ({ote_pts}/25)")
    if sweep_pts > 0:
        detail_lines.append(f"Sweep confirmed ({sweep_pts}/25)")
    if fvg_pts > 0:
        detail_lines.append(f"Unmitigated FVG ({fvg_pts}/25)")

    return MayneResult(
        score=min(75, score),
        passed_gate=passed,
        direction=direction,
        ote_points=ote_pts,
        sweep_points=sweep_pts,
        fvg_points=fvg_pts,
        swing_high=swing_high,
        swing_low=swing_low,
        sweep_level=sweep_level,
        fvg_top=fvg_top,
        fvg_bottom=fvg_bottom,
        detail=" | ".join(detail_lines) if detail_lines else "no confluence",
    )
