"""Binance public REST endpoints. Read-only, no API keys needed.

Endpoints used:
  GET /fapi/v1/klines        -> historical candles (USDT-M perpetuals)
  GET /fapi/v1/fundingRate   -> last funding rate per symbol
  GET /fapi/v1/markPrice     -> mark price (and next funding time)
  GET /futures/data/openInterestHist  -> OI history per symbol
  GET /futures/data/globalLongShortAccountRatio  -> retail long/short ratio
  GET /api/v3/klines         -> spot klines (used as cross-check)

All endpoints are public; rate-limit is generous (~1200 req/min per IP).
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests

from .logger import utc_now


FUTURES_BASE = "https://fapi.binance.com"
DATA_BASE = "https://fapi.binance.com/futures/data"
SPOT_BASE = "https://api.binance.com"


@dataclass
class Candle:
    open_time_ms: int      # ms epoch
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time_ms: int
    quote_volume: float
    trades: int

    @property
    def open_time(self) -> "datetime":  # noqa: F821
        from datetime import datetime, timezone
        return datetime.fromtimestamp(self.open_time_ms / 1000, tz=timezone.utc)


class BinanceError(RuntimeError):
    pass


class BinanceFuturesClient:
    """Thin REST wrapper. Timeouts + 1 retry on transient 429/5xx."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
    ) -> None:
        self._log = logging.getLogger("tidoquant")
        self._session = session or requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self._timeout = timeout

    # -------------------- low-level --------------------
    def _get(self, base: str, path: str, params: Dict) -> Dict:
        url = f"{base}{path}"
        last_err: Optional[Exception] = None
        for attempt in range(3):
            try:
                resp = self._session.get(
                    url, params=params, timeout=self._timeout
                )
                if resp.status_code == 429 or resp.status_code >= 500:
                    self._log.warning(
                        "binance transient %s on %s, retry %s",
                        resp.status_code, path, attempt,
                    )
                    time.sleep(0.6 * (attempt + 1))
                    last_err = BinanceError(f"HTTP {resp.status_code}")
                    continue
                if not resp.ok:
                    raise BinanceError(
                        f"binance HTTP {resp.status_code} on {path}: "
                        f"{resp.text[:200]}"
                    )
                return resp.json()
            except requests.RequestException as exc:
                last_err = exc
                time.sleep(0.6 * (attempt + 1))
        raise BinanceError(f"binance gave up on {path}: {last_err}")

    # -------------------- klines --------------------
    def klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 200,
        base: str = FUTURES_BASE,
    ) -> List[Candle]:
        """Fetch klines as Candle objects. Newest last."""
        raw = self._get(
            base,
            "/api/v3/klines" if base == SPOT_BASE else "/fapi/v1/klines",
            {"symbol": symbol, "interval": interval, "limit": limit},
        )
        out: List[Candle] = []
        for row in raw:
            out.append(
                Candle(
                    open_time_ms=int(row[0]),
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                    close_time_ms=int(row[6]),
                    quote_volume=float(row[7]),
                    trades=int(row[8]),
                )
            )
        return out

    # -------------------- funding + mark --------------------
    def funding_rate(self, symbol: str) -> Dict:
        # /fapi/v1/fundingRate returns most recent funding record.
        rows = self._get(
            FUTURES_BASE,
            "/fapi/v1/fundingRate",
            {"symbol": symbol, "limit": 1},
        )
        if not rows:
            return {"rate": 0.0, "time": 0}
        return {
            "rate": float(rows[-1]["fundingRate"]),
            "time": int(rows[-1]["fundingTime"]),
        }

    def mark_price(self, symbol: str) -> Dict:
        row = self._get(
            FUTURES_BASE,
            "/fapi/v1/premiumIndex",
            {"symbol": symbol},
        )
        return {
            "mark": float(row.get("markPrice", 0.0)),
            "index": float(row.get("indexPrice", 0.0)),
            "next_funding_time": int(row.get("nextFundingTime", 0)),
            "rate": float(row.get("lastFundingRate", 0.0)),
        }

    # -------------------- OI --------------------
    def open_interest_history(
        self, symbol: str, period: str = "5m", limit: int = 30
    ) -> List[Dict]:
        """OI-hist endpoints. Returns list of {sumOpenInterest,
        sumOpenInterestValue, timestamp}."""
        rows = self._get(
            DATA_BASE,
            "/openInterestHist",
            {
                "symbol": symbol,
                "period": period,
                "limit": limit,
            },
        )
        return rows or []

    # -------------------- long/short account ratio --------------------
    def long_short_account_ratio(
        self, symbol: str, period: str = "15m", limit: int = 30
    ) -> List[Dict]:
        rows = self._get(
            DATA_BASE,
            "/globalLongShortAccountRatio",
            {
                "symbol": symbol,
                "period": period,
                "limit": limit,
            },
        )
        return rows or []

    # -------------------- helper: server time --------------------
    def server_time_ms(self) -> int:
        raw = self._get(FUTURES_BASE, "/fapi/v1/time", {})
        return int(raw.get("serverTime", 0))


def safe_client() -> BinanceFuturesClient:
    """Default client factory used everywhere."""
    return BinanceFuturesClient()
