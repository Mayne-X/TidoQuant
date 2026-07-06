"""Static configuration. Everything tunable lives here."""
from __future__ import annotations

import os as _os
from dataclasses import dataclass, field
from typing import Tuple


PAIRS: Tuple[str, ...] = (
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
)

SCAN_INTERVAL_SECONDS: int = 15 * 60

# --- Mayne Scorer Parameters (HTF: 1h/4h/12h) ---
MAYNE_TF_WEIGHTS: Tuple[Tuple[str, float, int], ...] = (
    ("1h", 0.20, 168),
    ("4h", 0.30, 240),
    ("12h", 0.50, 120),
)
MAYNE_PIVOT_DEPTH: int = 3
MAYNE_CONFLUENCE_BONUS: int = 15
SWEEP_TIMEFRAME: str = "15m"
ENTRY_TIMEFRAME: str = "5m"
SWEEP_LOOKBACK: int = 288
ENTRY_LOOKBACK: int = 288

# --- Scalper Mayne Parameters (LTF: 1m/5m/15m/30m + 1h bias) ---
SCALPER_TF_WEIGHTS: Tuple[Tuple[str, float, int], ...] = (
    ("1m", 0.15, 100),
    ("5m", 0.25, 100),
    ("15m", 0.30, 100),
    ("30m", 0.30, 100),
)
SCALPER_HTF_BIAS_TF: str = "1h"
SCALPER_SWEEP_TF: str = "1m"
SCALPER_ENTRY_TF: str = "1m"
SCALPER_PIVOT_DEPTH: int = 2
SCALPER_MIN_CONFIRMATION_CANDLES: int = 3
SCALPER_MAX_SPREAD_BPS: int = 5
SCALPER_MIN_DEPTH_USD: float = 50000.0
SCALPER_TIME_STOP_CANDLES: int = 12
SCALPER_ATR_MULTIPLIER: float = 1.5

# --- Limit Order Engine ---
LIMIT_ORDER_EXPIRY_CANDLES: int = 10
LIMIT_ORDER_MAX_SLIPPAGE_BPS: int = 2

# --- Risk Brackets ---
@dataclass(frozen=True)
class RiskBracket:
    score_min: int
    score_max: int
    risk_pct: float
    leverage: int

RISK_BRACKETS: Tuple[RiskBracket, ...] = (
    RiskBracket(60, 70, 0.01, 2),
    RiskBracket(71, 85, 0.02, 3),
    RiskBracket(86, 100, 0.03, 5),
)

SCALPER_RISK_BRACKETS: Tuple[RiskBracket, ...] = (
    RiskBracket(60, 70, 0.005, 2),
    RiskBracket(71, 85, 0.01, 3),
    RiskBracket(86, 100, 0.015, 4),
)

STARTING_EQUITY: float = 1000.0
MIN_CONFIDENCE: int = 60
MIN_RR_RATIO: float = 2.0
DRAWDOWN_CIRCUIT_BREAKER: float = 0.30
MAX_GROSS_EXPOSURE_PCT: float = 0.50
MAX_PER_PAIR_PCT: float = 0.25

TAKER_FEE: float = 0.0004
MAKER_FEE: float = 0.0002

# --- Ollama ---
OLLAMA_BASE_URL: str = _os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
GEMMA4_MODEL: str = "qwen2.5:7b"
NUM_CTX: int = 131072
OLLAMA_TIMEOUT: int = 180
OLLAMA_TEMPERATURE: float = 0.3

# --- SQLite (ops: trades, agents, snapshots) ---
DB_PATH: str = "journal/tidoquant.db"

# --- TimescaleDB (candles, time-series) ---
TIMESCALE_URL: str = _os.environ.get(
    "TIMESCALE_URL",
    "postgresql://tidoquant:tidoquant@localhost:5432/tidoquant",
)


@dataclass
class RuntimePaths:
    project_root: str
    skills_dir: str
    reports_dir: str
    journal_dir: str
    evolution_skill: str = "skills/trader_evolution.md"
