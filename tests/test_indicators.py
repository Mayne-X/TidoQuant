"""Test indicators: swing detection, OTE, FVG, sweep."""
import pytest
from src.indicators import find_swings, calculate_ote_score, detect_fvg_mitigated, detect_sweep
from tests.conftest import (
    make_candle, OTE_CANDLES_1H,
    SWEEP_CANDLES_LONG, SWEEP_CANDLES_SHORT,
    SWEEP_ENTRY_LONG, SWEEP_ENTRY_SHORT,
    FVG_CANDLES_BULLISH, FVG_CANDLES_BEARISH, FVG_CANDLES_MITIGATED,
)


class TestSwingDetection:
    def test_detects_swing_high(self):
        c = [
            make_candle(100, 101, 99, 100),
            make_candle(100, 102, 99, 101),
            make_candle(101, 103, 100, 102),
            make_candle(102, 105, 101, 104),  # swing high
            make_candle(104, 104, 103, 103),
            make_candle(103, 104, 102, 103),
            make_candle(103, 103, 102, 102),
        ]
        swings = find_swings(c, pivot_depth=2)
        highs = [s for s in swings if s[0] == "high"]
        assert len(highs) >= 1
        assert highs[0][1].high == 105

    def test_detects_swing_low(self):
        c = [
            make_candle(100, 101, 99, 100),
            make_candle(99, 100, 98, 99),
            make_candle(98, 99, 95, 96),   # swing low
            make_candle(96, 97, 96, 97),
            make_candle(97, 98, 96, 97),
            make_candle(97, 98, 97, 98),
        ]
        swings = find_swings(c, pivot_depth=2)
        lows = [s for s in swings if s[0] == "low"]
        assert len(lows) >= 1
        assert lows[0][1].low == 95


class TestOTE:
    def test_long_in_ote_zone(self):
        """Price retraced into 0.5-0.705 zone from swing high."""
        # Swing high at 110, low at 99, current 102.5
        score = calculate_ote_score(high=110, low=99, price=102.5, is_long=True)
        assert 0 < score <= 1.0

    def test_long_above_ote_zone(self):
        """Price above 0.5 retracement = not in zone."""
        score = calculate_ote_score(high=110, low=100, price=108, is_long=True)
        assert score == 0.0

    def test_long_below_ote_returns_1(self):
        """Price below 0.705 = max score."""
        score = calculate_ote_score(high=110, low=100, price=102, is_long=True)
        assert score == 1.0

    def test_short_in_ote_zone(self):
        score = calculate_ote_score(high=110, low=100, price=107, is_long=False)
        assert 0 < score <= 1.0

    def test_short_above_ote_returns_1(self):
        score = calculate_ote_score(high=110, low=100, price=108, is_long=False)
        assert score == 1.0

    def test_short_below_mid_not_in_zone(self):
        score = calculate_ote_score(high=110, low=100, price=103, is_long=False)
        assert score == 0.0

    def test_zero_range(self):
        score = calculate_ote_score(high=100, low=100, price=100, is_long=True)
        assert score == 0.0

    def test_ote_on_mocked_candles(self):
        """OTE on real candle data with retracement."""
        swings = find_swings(OTE_CANDLES_1H)
        assert len(swings) > 0
        # Should find swing high at 110
        highs = [(t, c) for t, c in swings if t == "high"]
        assert len(highs) > 0
        # Last swing high should have high=110
        high_candle = highs[-1][1]
        score = calculate_ote_score(
            high=high_candle.high,
            low=min(c.low for c in OTE_CANDLES_1H),
            price=OTE_CANDLES_1H[-1].close,
            is_long=True,
        )
        assert score > 0


class TestFVG:
    def test_detects_bullish_fvg(self):
        fvgs = detect_fvg_mitigated(FVG_CANDLES_BULLISH)
        bullish = [f for f in fvgs if f["type"] == "bullish"]
        assert len(bullish) >= 1
        assert not bullish[0]["mitigated"]

    def test_detects_bearish_fvg(self):
        fvgs = detect_fvg_mitigated(FVG_CANDLES_BEARISH)
        bearish = [f for f in fvgs if f["type"] == "bearish"]
        assert len(bearish) >= 1
        assert not bearish[0]["mitigated"]

    def test_fvg_mitigated(self):
        fvgs = detect_fvg_mitigated(FVG_CANDLES_MITIGATED)
        for f in fvgs:
            assert f["mitigated"]

    def test_no_fvg_on_flat(self):
        flat = [make_candle(100, 101, 99, 100) for _ in range(5)]
        fvgs = detect_fvg_mitigated(flat)
        assert len(fvgs) == 0


class TestSweep:
    def test_detects_long_sweep(self):
        """Swing low at 98, price swept to 97 and closed at 99.5."""
        result = detect_sweep(
            SWEEP_ENTRY_LONG,
            swing_level=98,
            is_high_sweep=False,
        )
        assert result

    def test_detects_short_sweep(self):
        result = detect_sweep(
            SWEEP_ENTRY_SHORT,
            swing_level=103,
            is_high_sweep=True,
        )
        assert result

    def test_no_sweep_on_trend(self):
        trending = [
            make_candle(100, 101, 99, 100),
            make_candle(100, 102, 100, 101),
            make_candle(101, 103, 101, 102),  # no sweep
        ]
        result = detect_sweep(trending, swing_level=100, is_high_sweep=False)
        assert not result
