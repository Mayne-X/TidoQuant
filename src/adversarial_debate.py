"""Adversarial Debate Matrix.

BULL and BEAR agents review a trade setup.
"""
from typing import List
from .binance_client import Candle
from .indicators import detect_fvg_mitigated

def debate_trade(symbol: str, mayne_score: int, catalyst_score: int, entry_candles: List[Candle]) -> bool:
    # 1. Base Score Check
    if mayne_score + catalyst_score < 60:
        return False
    
    # 2. BEAR AGENT: Challenges
    # - Are all FVG's mitigated?
    fvgs = detect_fvg_mitigated(entry_candles)
    if not fvgs or all(f["mitigated"] for f in fvgs):
        # Bear says: no unmitigated imbalances, potential trap
        return False
        
    # 3. BULL AGENT: Defends
    # - Was the sweep volume high?
    if len(entry_candles) > 5:
        # Simplistic: Sweep candle volume > avg volume of last 5
        sweep_vol = entry_candles[-2].volume
        avg_vol = sum(c.volume for c in entry_candles[-6:-1]) / 5
        if sweep_vol < avg_vol:
            # Bear wins: low volume sweep = weak
            return False
            
    return True
