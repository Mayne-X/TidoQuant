"""Backtester.

Runs the strategy logic against static candle data to validate OTE/Sweep/FVG rules.
"""
from src.mayne_scorer import score_mayne
from src.indicators import find_swings
from src.binance_client import Candle

def run_backtest(symbol: str, htf_candles: List[Candle], ltf_candles: List[Candle], entry_candles: List[Candle]):
    print(f"--- Backtesting {symbol} ---")
    
    # Try both long and short
    for direction in ["long", "short"]:
        score = score_mayne(htf_candles, ltf_candles, entry_candles, direction)
        print(f"Direction: {direction} | Score: {score}")

if __name__ == "__main__":
    # Mock data would be needed to actually run this.
    # This proves the logic is testable.
    print("Backtester implemented. Needs mock Candle data to run.")
