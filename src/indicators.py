"""Indicator math for the Mayne engine.

Functions here operate on lists of Candle objects and return structural data.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from .binance_client import Candle
from .config import MAYNE_PIVOT_DEPTH


def find_swings(candles: List[Candle], pivot_depth: int = MAYNE_PIVOT_DEPTH) -> List[Tuple[str, Candle]]:
    """Simple fractal swing detector.
    Returns list of ('high'|'low', Candle).
    """
    swings = []
    for i in range(pivot_depth, len(candles) - pivot_depth):
        is_high = all(candles[i].high > candles[j].high for j in range(i - pivot_depth, i + pivot_depth + 1) if i != j)
        is_low = all(candles[i].low < candles[j].low for j in range(i - pivot_depth, i + pivot_depth + 1) if i != j)
        if is_high:
            swings.append(("high", candles[i]))
        elif is_low:
            swings.append(("low", candles[i]))
    return swings


def calculate_ote_score(high: float, low: float, price: float, is_long: bool) -> float:
    """Returns % distance into OTE pocket [0.5, 0.705].
    0.0 = not in zone (or wrong side of midpoint), 1.0 = deep OTE (0.705).
    """
    if high <= low: return 0.0
    mid = (high + low) / 2
    range_val = high - low
    
    if is_long:
        # Discount: price < mid
        if price >= mid: return 0.0
        # OTE pocket: 0.5 to 0.705 Fibonacci retracement
        ote_start = high - range_val * 0.5
        ote_end = high - range_val * 0.705
        if price > ote_start: return 0.0
        if price < ote_end: return 1.0 # Beyond 0.705
        return (ote_start - price) / (ote_start - ote_end)
    else:
        # Premium: price > mid
        if price <= mid: return 0.0
        ote_start = low + range_val * 0.5
        ote_end = low + range_val * 0.705
        if price < ote_start: return 0.0
        if price > ote_end: return 1.0
        return (price - ote_start) / (ote_end - ote_start)


def detect_fvg_mitigated(candles: List[Candle]) -> List[dict]:
    """Detect 3-candle FVG and check if it was mitigated (tapped)."""
    fvgs = []
    for i in range(1, len(candles) - 1):
        # Bullish FVG: c[i-1].low > c[i+1].high
        if candles[i-1].low > candles[i+1].high:
            fvg_top = candles[i-1].low
            fvg_bottom = candles[i+1].high
            
            # Check for mitigation (tap back into zone)
            mitigated = False
            for j in range(i + 2, len(candles)):
                if candles[j].high >= fvg_bottom:
                    mitigated = True
                    break
            
            fvgs.append({
                "type": "bullish",
                "top": fvg_top,
                "bottom": fvg_bottom,
                "mitigated": mitigated
            })
        
        # Bearish FVG: c[i-1].high < c[i+1].low
        elif candles[i-1].high < candles[i+1].low:
            fvg_top = candles[i+1].low
            fvg_bottom = candles[i-1].high
            
            mitigated = False
            for j in range(i + 2, len(candles)):
                if candles[j].low <= fvg_top:
                    mitigated = True
                    break
            
            fvgs.append({
                "type": "bearish",
                "top": fvg_top,
                "bottom": fvg_bottom,
                "mitigated": mitigated
            })
    return fvgs


def detect_sweep(candles: List[Candle], swing_level: float, is_high_sweep: bool) -> bool:
    """Did price sweep the swing_level and close back within?"""
    last = candles[-1]
    # Requires candle to go beyond level, then close back within
    if is_high_sweep:
        return last.high > swing_level and last.close < swing_level
    return last.low < swing_level and last.close > swing_level
