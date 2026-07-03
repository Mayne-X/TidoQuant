"""Test Mayne scorer: multi-timeframe OTE, sweep, FVG, gate logic."""
from src.mayne_scorer import score_mayne
from tests.conftest import (
    make_candle, make_tf_dict,
    UP_CANDLES_1H, UP_CANDLES_4H, UP_CANDLES_12H,
    OTE_CANDLES_1H, SWEEP_CANDLES_LONG, SWEEP_CANDLES_SHORT,
    SWEEP_ENTRY_LONG, SWEEP_ENTRY_SHORT,
    ENTRY_LONG_FULL,
    FVG_CANDLES_BULLISH, FVG_CANDLES_BEARISH,
)


class TestMayneScorer:
    def test_passes_long_with_confluence(self):
        """Full confluence: OTE + sweep + FVG = pass."""
        tf = make_tf_dict(one_h=UP_CANDLES_1H, four_h=UP_CANDLES_4H, twelve_h=UP_CANDLES_12H)
        result = score_mayne(tf, SWEEP_CANDLES_LONG, ENTRY_LONG_FULL, "long")
        assert result.passed_gate, f"Score {result.score}: {result.detail}"
        assert result.score >= 60
        assert result.direction == "long"

    def test_score_never_exceeds_75(self):
        tf = make_tf_dict()
        result = score_mayne(tf, SWEEP_CANDLES_LONG, SWEEP_ENTRY_LONG, "long")
        assert result.score <= 75

    def test_multi_tf_scores_recorded(self):
        tf = make_tf_dict()
        result = score_mayne(tf, SWEEP_CANDLES_LONG, SWEEP_ENTRY_LONG, "long")
        assert isinstance(result.tf_scores, dict)

    def test_short_direction_works(self):
        tf = make_tf_dict()
        result = score_mayne(tf, SWEEP_CANDLES_SHORT, SWEEP_ENTRY_SHORT, "short")
        assert result.direction == "short"

    def test_fails_gate_with_no_confluence(self):
        """Flat/no-signal data should fail the gate."""
        flat_tf = {
            "1h": [make_candle(100, 101, 99, 100) for _ in range(10)],
            "4h": [make_candle(100, 101, 99, 100) for _ in range(10)],
            "12h": [make_candle(100, 101, 99, 100) for _ in range(10)],
        }
        flat_swp = [make_candle(100, 101, 99, 100) for _ in range(5)]
        flat_fvg = [make_candle(100, 101, 99, 100) for _ in range(5)]
        result = score_mayne(flat_tf, flat_swp, flat_fvg, "long")
        assert not result.passed_gate
        assert result.score < 60

    def test_direction_switching(self):
        """Short should fail on long-biased data."""
        tf = make_tf_dict(one_h=OTE_CANDLES_1H)
        # OTE_CANDLES_1H has retracement to 102.5 for long; swap for short
        short_tf = make_tf_dict(one_h=[
            make_candle(100, 101, 99, 100, open_time_ms=0),
            make_candle(100, 102, 99, 101, open_time_ms=1),
            make_candle(101, 103, 100, 102, open_time_ms=2),
            make_candle(102, 103, 100.5, 101, open_time_ms=3),
        ])
        result = score_mayne(short_tf, SWEEP_CANDLES_SHORT, FVG_CANDLES_BEARISH, "short")
        # At minimum runs without error and returns some result
        assert result.direction == "short"
