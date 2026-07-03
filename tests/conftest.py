"""Shared mocks and fixtures for all tests."""
from typing import List, Dict
from src.binance_client import Candle


def make_candle(open_t: float, high: float, low: float, close: float,
                volume: float = 1000.0, trades: int = 100,
                open_time_ms: int = 0) -> Candle:
    """Quick Candle factory."""
    return Candle(
        open_time_ms=open_time_ms,
        open=open_t,
        high=high,
        low=low,
        close=close,
        volume=volume,
        close_time_ms=open_time_ms + 3600000,
        quote_volume=volume * (open_t + close) / 2,
        trades=trades,
    )


# ── Trending up candles (long bias) ──────────────────────────
UP_CANDLES_1H: List[Candle] = [
    make_candle(100, 101, 99, 100, open_time_ms=0),
    make_candle(100, 102, 99, 101, open_time_ms=1),
    make_candle(101, 103, 100, 102, open_time_ms=2),
    make_candle(102, 106, 101, 105, open_time_ms=3),
    make_candle(105, 112, 104, 111, open_time_ms=4),    # swing high at 112 (unique)
    make_candle(111, 111, 110, 111, open_time_ms=5),    # high=111 < 112 ✓
    make_candle(111, 111, 109, 110, open_time_ms=6),    # high=111 < 112 ✓
    make_candle(110, 111, 108, 109, open_time_ms=7),
    make_candle(109, 110, 108, 109, open_time_ms=8),
    # Swing high at 112 (idx 4), low at 99
    # OTE zone long: 112 - (112-99)*0.5 = 105.5 to 112 - (112-99)*0.705 = 102.83
    # Price 108 — just above OTE zone
    make_candle(109, 110, 108, 108, open_time_ms=9),
]

# 4h: retraced INTO OTE zone
UP_CANDLES_4H: List[Candle] = [
    make_candle(95, 96, 94, 95, open_time_ms=0),
    make_candle(95, 98, 94, 97, open_time_ms=1),
    make_candle(97, 100, 96, 99, open_time_ms=2),
    make_candle(99, 105, 98, 104, open_time_ms=3),    # swing high at 105 (unique)
    make_candle(104, 104, 103, 104, open_time_ms=4),   # high=104 < 105 ✓
    make_candle(104, 104, 102, 103, open_time_ms=5),
    make_candle(103, 104, 101, 102, open_time_ms=6),
    # Swing high at 105, low at 94
    # OTE zone long: 105 - (105-94)*0.5 = 99.5 to 105 - (105-94)*0.705 = 97.25
    # Price 99 — IN OTE zone!
    make_candle(102, 103, 99, 99, open_time_ms=7),
]

# 12h: retraced INTO OTE zone
UP_CANDLES_12H: List[Candle] = [
    make_candle(90, 91, 89, 90, open_time_ms=0),
    make_candle(90, 93, 89, 92, open_time_ms=1),
    make_candle(92, 95, 91, 94, open_time_ms=2),
    make_candle(94, 100, 93, 99, open_time_ms=3),    # swing high at 100 (unique)
    make_candle(99, 99, 97, 98, open_time_ms=4),      # high=99 < 100 ✓
    make_candle(98, 99, 96, 97, open_time_ms=5),
    make_candle(97, 98, 95, 96, open_time_ms=6),
    # Swing high at 100, low at 89
    # OTE zone long: 100 - (100-89)*0.5 = 94.5 to 100 - (100-89)*0.705 = 92.25
    # Price 92 — IN OTE zone!
    make_candle(96, 97, 92, 92, open_time_ms=7),
]

# ── Candles that retrace INTO OTE zone ──────────────────────
OTE_CANDLES_1H: List[Candle] = [
    make_candle(100, 101, 99, 100, open_time_ms=0),
    make_candle(100, 102, 99, 101, open_time_ms=1),
    make_candle(101, 103, 100, 102, open_time_ms=2),
    make_candle(102, 106, 101, 105, open_time_ms=3),
    make_candle(105, 115, 104, 114, open_time_ms=4),   # swing high at 115 (unique)
    make_candle(114, 114, 113, 114, open_time_ms=5),   # high=114 < 115 ✓
    make_candle(114, 114, 112, 113, open_time_ms=6),
    make_candle(113, 114, 111, 112, open_time_ms=7),
    # Swing high at 115 (idx 4), lows at 99
    # OTE zone long: 115 - (115-99)*0.5 = 107 to 115 - (115-99)*0.705 = 103.72
    # Price 105 — in OTE zone!
    make_candle(112, 113, 105, 105, open_time_ms=8),
]

# ── Sweep candles (enough for pivot_depth=2) ────────────────
SWEEP_CANDLES_LONG: List[Candle] = [
    make_candle(100, 101, 99, 100, open_time_ms=0),
    make_candle(100, 101, 99, 100, open_time_ms=1),
    make_candle(100, 101, 98, 100, open_time_ms=2),     # swing low at 98 (index 2)
    make_candle(100, 102, 99, 101, open_time_ms=3),
    make_candle(101, 102, 100, 101, open_time_ms=4),
    make_candle(101, 102, 100, 101, open_time_ms=5),
]
# Entry candles that sweep the 98 level:
SWEEP_ENTRY_LONG: List[Candle] = [
    make_candle(101, 102, 100.5, 101, open_time_ms=0),
    make_candle(101, 102, 97, 99.5, open_time_ms=1),   # low=97 < 98, close=99.5 > 98 ✓
]

# Entry candles with BOTH a sweep AND an unmitigated bullish FVG
# FVG at indices 0-2 (c[0].low=100 > c[2].high=99 → gap 99-100)
# Later candles must NOT touch the gap (high < 99)
# Sweep on last candle (low=97 < 98, close=98.5 > 98)
ENTRY_LONG_FULL: List[Candle] = [
    make_candle(100, 102, 100, 101, open_time_ms=0),      # i-1, low=100 — FVG top
    make_candle(99, 101, 98, 100, open_time_ms=1),        # i
    make_candle(100, 99, 98.5, 99, open_time_ms=2),       # i+1, high=99 — FVG bottom
    make_candle(99, 98.9, 98, 98.5, open_time_ms=3),      # high=98.9 < 99, not touching gap
    make_candle(98.5, 98.8, 98, 98.3, open_time_ms=4),    # high=98.8 < 99, not touching gap
    make_candle(98.3, 98.9, 97, 98.5, open_time_ms=5),    # sweep: low=97 < 98, close=98.5 > 98 ✓
]

SWEEP_CANDLES_SHORT: List[Candle] = [
    make_candle(100, 101, 99, 100, open_time_ms=0),
    make_candle(100, 102, 99, 101, open_time_ms=1),
    make_candle(101, 103, 100, 102, open_time_ms=2),   # swing high at 103 (index 2)
    make_candle(102, 103, 101, 102, open_time_ms=3),
    make_candle(102, 103, 101, 102, open_time_ms=4),
    make_candle(102, 103, 101, 102, open_time_ms=5),
]
# Entry candles that sweep the 103 level:
SWEEP_ENTRY_SHORT: List[Candle] = [
    make_candle(102, 103, 101, 102, open_time_ms=0),
    make_candle(102, 105, 101, 101.5, open_time_ms=1),  # high=105 > 103, close=101.5 < 103 ✓
]

# ── FVG candles ─────────────────────────────────────────────
# Bullish FVG: c[i-1].low > c[i+1].high (gap up after a down candle)
FVG_CANDLES_BULLISH: List[Candle] = [
    make_candle(100, 102, 99, 101, open_time_ms=0),      # i-1, low=99
    make_candle(97, 100, 96, 98, open_time_ms=1),        # i, gaps down
    make_candle(98, 98.5, 97.5, 98, open_time_ms=2),     # i+1, high=98.5 < low=99 → gap!
]

# Bearish FVG: c[i-1].high < c[i+1].low (gap down after an up candle)
FVG_CANDLES_BEARISH: List[Candle] = [
    make_candle(100, 101, 99, 100, open_time_ms=0),      # i-1, high=101
    make_candle(102, 103, 101, 102, open_time_ms=1),     # i, gaps up
    make_candle(102.5, 104, 102, 103, open_time_ms=2),   # i+1, low=102 > high=101 → gap!
]

# Mitigated: subsequent candle taps into the gap
FVG_CANDLES_MITIGATED: List[Candle] = [
    make_candle(100, 102, 99, 101, open_time_ms=0),      # i-1, low=99
    make_candle(97, 100, 96, 98, open_time_ms=1),        # i
    make_candle(98, 98.5, 97.5, 98, open_time_ms=2),     # i+1, gap between 98.5 and 99
    make_candle(98.5, 99.5, 98, 99, open_time_ms=3),     # taps into gap (high=99.5, low=98)
]

# ── Multi-TF dict ──────────────────────────────────────────
def make_tf_dict(one_h=UP_CANDLES_1H, four_h=UP_CANDLES_4H, twelve_h=UP_CANDLES_12H) -> Dict[str, List[Candle]]:
    return {"1h": one_h, "4h": four_h, "12h": twelve_h}
