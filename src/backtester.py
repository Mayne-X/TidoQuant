"""Backtester.

Runs the strategy logic against static candle data to validate OTE/Sweep/FVG rules.
"""
from typing import Dict, List

from .mayne_scorer import score_mayne
from .indicators import find_swings
from .binance_client import Candle


def run_backtest(symbol: str, tf_candles: Dict[str, List[Candle]], sweep_candles: List[Candle],
                 entry_candles: List[Candle]):
    print(f"--- Backtesting {symbol} ---")

    for direction in ["long", "short"]:
        result = score_mayne(tf_candles, sweep_candles, entry_candles, direction)
        print(f"Direction: {direction} | Score: {result.score} | {result.detail}")

if __name__ == "__main__":
    print("Backtester implemented. Needs mock Candle data to run.")
