"""Mayne Scorer (75% weightage) — gatekeeper of the system.

Multi-timeframe: OTE scored on 1h, 4h, 12h independently, then weighted.
Sweep + FVG scored once on lower TFs.
"""
from __future__ import annotations
from typing import Dict, List, Tuple

from .binance_client import Candle
from .indicators import find_swings, calculate_ote_score, detect_fvg_mitigated, detect_sweep
from .core.signal_packet import MayneResult
from .config import MAYNE_TF_WEIGHTS, MAYNE_CONFLUENCE_BONUS


def score_mayne(
    tf_candles: Dict[str, List[Candle]],
    sweep_candles: List[Candle],
    entry_candles: List[Candle],
    direction: str,
) -> MayneResult:
    score = 0
    ote_pts = sweep_pts = fvg_pts = 0
    swing_high = swing_low = None
    sweep_level = fvg_top = fvg_bottom = None
    tf_scores: Dict[str, int] = {}
    tf_details: List[str] = []
    price = entry_candles[-1].close
    is_long = (direction == "long")

    # 1. Multi-timeframe OTE — scored on each HTF, weighted
    # MAYNE_TF_WEIGHTS is list of (label, weight, limit)
    tf_weights_dict = {t[0]: t[1] for t in MAYNE_TF_WEIGHTS}

    for tf_label, candles in tf_candles.items():
        swings = find_swings(candles)
        pts = 0
        if swings:
            last_swing_type, last_swing_candle = swings[-1]
            if (is_long and last_swing_type == "high") or (not is_long and last_swing_type == "low"):
                high = last_swing_candle.high
                low = last_swing_candle.low
                # Track highest swing for display
                if swing_high is None or high > swing_high:
                    swing_high = high
                if swing_low is None or low < swing_low:
                    swing_low = low
                ote_val = calculate_ote_score(high, low, price, is_long)
                if ote_val > 0:
                    pts = int(ote_val * 25)
                    tf_details.append(f"{tf_label}: OTE {pts}/25")
        tf_scores[tf_label] = pts

    # Weighted OTE sum (max 25)
    weighted_ote = sum(
        pts * tf_weights_dict.get(tf, 0) for tf, pts in tf_scores.items()
    )
    ote_pts = int(weighted_ote)

    # 2. Liquidity Sweep (25 Points)
    local_swings = find_swings(sweep_candles, pivot_depth=2)
    if local_swings:
        level = local_swings[-1][1].low if direction == "long" else local_swings[-1][1].high
        sweep_level = level
        is_high_sweep = (direction == "short")
        if detect_sweep(entry_candles, level, is_high_sweep):
            sweep_pts = 25
            tf_details.append(f"sweep {sweep_pts}/25")

    # 3. Displacement & FVG (25 Points)
    fvgs = detect_fvg_mitigated(entry_candles)
    for fvg in fvgs:
        if not fvg["mitigated"]:
            if (direction == "long" and fvg["type"] == "bullish") or \
               (direction == "short" and fvg["type"] == "bearish"):
                fvg_pts = 25
                fvg_top = fvg["top"]
                fvg_bottom = fvg["bottom"]
                tf_details.append(f"FVG {fvg_pts}/25")
                break

    # Dynamic Confluence Bonus
    confluence_count = 0
    if ote_pts > 0: confluence_count += 1
    if sweep_pts > 0: confluence_count += 1
    if fvg_pts > 0: confluence_count += 1
    
    bonus = 0
    if confluence_count >= 3:
        bonus = MAYNE_CONFLUENCE_BONUS
        tf_details.append(f"confluence bonus {bonus}/15")

    score = ote_pts + sweep_pts + fvg_pts + bonus
    passed = score >= 60

    return MayneResult(
        score=min(90, score),
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
        tf_scores=tf_scores,
        detail=" | ".join(tf_details) if tf_details else "no confluence",
    )
