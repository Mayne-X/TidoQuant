"""Mayne Scorer (75% weightage).

Calculates confidence based on HTF structure, sweep, and displacement/FVG.
"""
from __future__ import annotations
from typing import List
from .binance_client import Candle
from .indicators import find_swings, calculate_ote_score, detect_fvg_mitigated, detect_sweep

def score_mayne(htf_candles: List[Candle], ltf_candles: List[Candle], entry_candles: List[Candle], direction: str) -> int:
    score = 0
    
    # 1. HTF Trend & OTE (25 Points)
    swings = find_swings(htf_candles)
    if swings:
        last_swing_type, last_swing_candle = swings[-1]
        price = entry_candles[-1].close
        
        is_long = (direction == "long")
        # Ensure we are in discount for long, premium for short
        if (is_long and last_swing_type == "high") or (not is_long and last_swing_type == "low"):
            # Use major swing range for OTE
            high = last_swing_candle.high if last_swing_type == "high" else entry_candles[0].high # Simplified
            low = last_swing_candle.low if last_swing_type == "low" else entry_candles[0].low
            
            ote_score = calculate_ote_score(high, low, price, is_long)
            score += int(ote_score * 25)
    
    # 2. Liquidity Sweep (25 Points)
    # Check if price swept a recent local swing in LTF
    local_swings = find_swings(ltf_candles, pivot_depth=2)
    if local_swings:
        level = local_swings[-1][1].low if direction == "long" else local_swings[-1][1].high
        is_high_sweep = (direction == "short")
        if detect_sweep(entry_candles, level, is_high_sweep):
            score += 25
    
    # 3. Displacement & FVG (25 Points)
    fvgs = detect_fvg_mitigated(entry_candles)
    # Only points if UNMITIGATED
    for fvg in fvgs:
        if not fvg["mitigated"]:
            if (direction == "long" and fvg["type"] == "bullish") or \
               (direction == "short" and fvg["type"] == "bearish"):
                score += 25
                break # Only need one strong FVG
        
    return min(75, score)
