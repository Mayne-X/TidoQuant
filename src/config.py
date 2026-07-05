"""Static configuration. Everything tunable lives here."""
from __future__ import annotations

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

# Multi-timeframe analysis — each pair analyzed across 3 HTFs
# each entry: (label, weight_for_OTE, candle_limit)
TIMEFRAMES = (
    ("1h",  0.20, 168),
    ("4h",  0.30, 240),
    ("12h", 0.50, 120),
)
SWEEP_TIMEFRAME: str = "15m"
ENTRY_TIMEFRAME: str = "5m"
SWEEP_LOOKBACK: int = 288
ENTRY_LOOKBACK: int = 288


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

STARTING_EQUITY: float = 1000.0
MIN_CONFIDENCE: int = 60
MIN_RR_RATIO: float = 2.0
DRAWDOWN_CIRCUIT_BREAKER: float = 0.30

TAKER_FEE: float = 0.0004

# --- Ollama (override via env var for Docker) ---
import os as _os
OLLAMA_BASE_URL: str = _os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
GEMMA4_MODEL: str = "qwen2.5:7b"
NUM_CTX: int = 131072
OLLAMA_TIMEOUT: int = 180
OLLAMA_TEMPERATURE: float = 0.3

# --- SQLite ---
DB_PATH: str = "journal/tidoquant.db"


@dataclass
class RuntimePaths:
    project_root: str
    skills_dir: str
    reports_dir: str
    journal_dir: str
    evolution_skill: str = "skills/trader_evolution.md"
