"""Static configuration. Everything tunable lives here."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


# Top-5 Binance USDT-M perps by volume (locked decision).
PAIRS: Tuple[str, ...] = (
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
)


# Scan cadence (locked decision: every 15 min).
SCAN_INTERVAL_SECONDS: int = 15 * 60


# Timeframes used by the playbook.
HTF_TIMEFRAME: str = "4h"
LTF_TIMEFRAME: str = "15m"
ENTRY_TIMEFRAME: str = "5m"

# How much candle history to pull per fetch (number of bars).
HTF_LOOKBACK: int = 240       # ~40 days of 4H
LTF_LOOKBACK: int = 288       # 3 days of 15m
ENTRY_LOOKBACK: int = 288     # 1 day of 5m


@dataclass(frozen=True)
class RiskBracket:
    score_min: int
    score_max: int
    risk_pct: float          # fraction of equity to risk
    leverage: int


# Leverage bracket from the playbook.
RISK_BRACKETS: Tuple[RiskBracket, ...] = (
    RiskBracket(60, 70, 0.01, 2),
    RiskBracket(71, 85, 0.02, 3),
    RiskBracket(86, 100, 0.03, 5),
)


# Capital & survival rules.
STARTING_EQUITY: float = 100.0
MIN_CONFIDENCE: int = 60       # below this, no trade
MIN_RR_RATIO: float = 2.0      # 2:1 R:R minimum

# Hard circuit breaker: stop opening new trades at –30% drawdown.
DRAWDOWN_CIRCUIT_BREAKER: float = 0.30

# Funding-rate crowding filter (locked decision: option 1).
# If long setup and funding > +FUNDING_EXTREME, deduct points.
# If short setup and funding < -FUNDING_EXTREME, deduct points.
FUNDING_EXTREME: float = 0.0005  # 0.05% per 8h

# OI delta confirmation (locked decision: option 3).
# A genuine displacement should arrive with rising OI.
OI_DELTA_LOOKBACK_CANDLES: int = 8  # last 8 LTF candles
OI_RISE_THRESHOLD: float = 0.005    # +0.5% OI = healthy displacement

# Catalyst score bounds.
SENTIMENT_MAX: float = 12.5
NEWS_MAX: float = 12.5


# Monday's range sweep window (NY time = ET).
# We anchor on UTC; NY = UTC-5 (EST) or UTC-4 (EDT). We use UTC offsets directly.
MONDAY_RANGE_START_HOUR_UTC: int = 5   # 00:00 NY (EST) = 05:00 UTC
MONDAY_RANGE_END_HOUR_UTC: int = 28   # 23:59 NY (EST) Monday = next-day 04:59 UTC


# Fee model — Binance USDT-M perpetual taker.
TAKER_FEE: float = 0.0004   # 4 bps


# Filesystem layout (anchored at project root).
PROJECT_ROOT_MARKER: str = "PYPROJECT_ANCHOR"


@dataclass
class RuntimePaths:
    project_root: str
    skills_dir: str
    reports_dir: str
    journal_dir: str
    evolution_skill: str = "skills/trader_evolution.md"
