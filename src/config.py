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

HTF_TIMEFRAME: str = "4h"
LTF_TIMEFRAME: str = "15m"
ENTRY_TIMEFRAME: str = "5m"

HTF_LOOKBACK: int = 240
LTF_LOOKBACK: int = 288
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

STARTING_EQUITY: float = 100.0
MIN_CONFIDENCE: int = 60
MIN_RR_RATIO: float = 2.0
DRAWDOWN_CIRCUIT_BREAKER: float = 0.30

TAKER_FEE: float = 0.0004

# --- Ollama (override via env var for Docker) ---
import os as _os
OLLAMA_BASE_URL: str = _os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
GEMMA4_MODEL: str = "gemma4"
NUM_CTX: int = 131072
OLLAMA_TIMEOUT: int = 45
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
