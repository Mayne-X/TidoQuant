"""Scalper Filter Chain — 7-step noise reduction before the agent pipeline.

Each filter runs sequentially. If any fails, the signal is REJECTED
before any LLM inference occurs (saves time + compute).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .binance_client import Candle

log = logging.getLogger("tidoquant")


@dataclass
class FilterResult:
    passed: bool
    score: int = 0          # 0-100, percentage of filters passed
    filters: Dict[str, bool] = field(default_factory=dict)
    reject_reason: str = ""


class FilterChain:
    """7-step scalper filter. Returns FilterResult with per-filter status."""

    def __init__(self):
        pass

    def run(
        self,
        symbol: str,
        direction: str,
        lt_candles: Dict[str, List[Candle]],
        htf_candles: List[Candle],
        entry_candles: List[Candle],  # 1m
        funding_rate: float,
        long_short_ratio: Optional[List[Dict]] = None,
        spread_bps: Optional[float] = None,
        depth_usd: Optional[float] = None,
    ) -> FilterResult:
        filters: Dict[str, bool] = {}
        reject = ""

        # ─── 1. HTF Bias Alignment ───
        f1 = self._check_htf_bias(direction, htf_candles, entry_candles)
        filters["htf_bias"] = f1
        if not f1 and not reject:
            reject = "HTF bias mismatch"

        # ─── 2. 1m Liquidity Sweep ───
        f2 = self._check_liquidity_sweep(direction, entry_candles)
        filters["liquidity_sweep"] = f2
        if not f2 and not reject:
            reject = "No recent 1m liquidity sweep"

        # ─── 3. Funding / Crowd ───
        f3 = True
        if abs(funding_rate) >= 0.0005:  # 0.05%
            f3 = False
            if not reject:
                reject = "Funding rate extreme (>0.05%)"
        if long_short_ratio:
            ratios = [float(r.get("longShortRatio", 1.0)) for r in long_short_ratio[-3:]]
            avg_ratio = sum(ratios) / max(len(ratios), 1)
            if avg_ratio > 2.0 or avg_ratio < 0.5:
                f3 = False
                if not reject:
                    reject = "Extreme long/short ratio"
        filters["funding_crowd"] = f3

        # ─── 4. Spread & Depth ───
        f4 = True
        if spread_bps is not None and spread_bps > 5:
            f4 = False
            if not reject:
                reject = "Spread too wide (>5bps)"
        filters["spread_depth"] = f4

        # ─── 5. Volatility Regime ───
        f5 = self._check_volatility_regime(entry_candles)
        filters["vol_regime"] = f5
        if not f5 and not reject:
            reject = "Volatility out of range (dead or chaotic)"

        # ─── 6. Multi-TF Confluence ───
        f6 = self._check_mtf_confluence(direction, lt_candles, entry_candles)
        filters["mtf_confluence"] = f6
        if not f6 and not reject:
            reject = "5m/15m RSI disagrees with direction"

        # ─── 7. Time-of-Day ───
        f7 = self._check_time_of_day()
        filters["time_of_day"] = f7
        if not f7 and not reject:
            reject = "Outside trading hours (low liquidity window)"

        passed_count = sum(1 for v in filters.values() if v)
        total = len(filters)
        score = int((passed_count / total) * 100) if total else 0

        return FilterResult(
            passed=all(filters.values()),
            score=score,
            filters=filters,
            reject_reason=reject,
        )

    # ─── Individual filters ───

    def _check_htf_bias(self, direction: str, htf: List[Candle], entry: List[Candle]) -> bool:
        if not htf or len(htf) < 20:
            return True
        htf_close = htf[-1].close
        price = entry[-1].close if entry else htf_close
        ema20 = sum(c.close for c in htf[-20:]) / 20
        ema50 = sum(c.close for c in htf[-50:]) / 50 if len(htf) >= 50 else ema20
        if direction == "long":
            return price > ema20 and ema20 > ema50 * 0.99
        else:
            return price < ema20 and ema20 < ema50 * 1.01

    def _check_liquidity_sweep(self, direction: str, candles: List[Candle]) -> bool:
        if not candles or len(candles) < 10:
            return True
        recent = candles[-10:]
        highs = [c.high for c in recent]
        lows = [c.low for c in recent]
        avg_range = (sum(highs) / len(highs) - sum(lows) / len(lows))
        if direction == "long":
            sweep_low = min(lows)
            recent_lows = [c.low for c in recent]
            sweep_idx = recent_lows.index(sweep_low)
            if sweep_idx < 3:  # sweep within last 3 candles
                return True  # swept low recently
        else:
            sweep_high = max(highs)
            recent_highs = [c.high for c in recent]
            sweep_idx = recent_highs.index(sweep_high)
            if sweep_idx < 3:
                return True
        return False

    def _check_volatility_regime(self, candles: List[Candle]) -> bool:
        if not candles or len(candles) < 20:
            return True
        atr_values = []
        for i in range(1, len(candles)):
            tr = max(
                candles[i].high - candles[i].low,
                abs(candles[i].high - candles[i-1].close),
                abs(candles[i].low - candles[i-1].close),
            )
            atr_values.append(tr)
        atr14 = sum(atr_values[-14:]) / 14 if len(atr_values) >= 14 else sum(atr_values) / max(len(atr_values), 1)
        atr50 = sum(atr_values[-50:]) / 50 if len(atr_values) >= 50 else atr14
        if atr14 < atr50 * 0.5:
            return False  # dead session
        if atr14 > atr50 * 3.0:
            return False  # chaotic session
        return True

    def _check_mtf_confluence(self, direction: str, lt_candles: Dict[str, List[Candle]], entry: List[Candle]) -> bool:
        confirms = 0
        total = 0
        for tf, candles in lt_candles.items():
            if len(candles) < 14:
                continue
            total += 1
            gains = [c.close - c.open for c in candles[-14:]]
            avg_gain = sum(g for g in gains if g > 0) / 14 if any(g > 0 for g in gains) else 0.001
            avg_loss = abs(sum(g for g in gains if g < 0)) / 14 if any(g < 0 for g in gains) else 0.001
            rs = avg_gain / max(avg_loss, 0.0001)
            rsi = 100 - (100 / (1 + rs))
            if direction == "long" and 30 <= rsi <= 50:
                confirms += 1
            elif direction == "short" and 50 <= rsi <= 70:
                confirms += 1
        return confirms >= total * 0.5 if total > 0 else True

    def _check_time_of_day(self) -> bool:
        from datetime import datetime, timezone
        h = datetime.now(timezone.utc).hour
        return not (0 <= h <= 4)  # exclude 00:00-04:00 UTC
