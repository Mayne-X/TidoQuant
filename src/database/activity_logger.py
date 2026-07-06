"""Full-activity trace capture for future model fine-tuning.

Every pipeline step, agent call, price tick, and decision is recorded
as structured JSONL in the journal/ directory. This is THE fine-tuning
dataset for training future models on TidoQuant's decision-making logic.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("tidoquant")

_ACTIVITY_LOG_PATH: Optional[Path] = None
_ACTIVITY_LOG_FILE = None


def _ensure_log():
    global _ACTIVITY_LOG_FILE, _ACTIVITY_LOG_PATH
    if _ACTIVITY_LOG_FILE is not None:
        return
    _ACTIVITY_LOG_PATH = Path("journal/activity_log.jsonl")
    _ACTIVITY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ACTIVITY_LOG_FILE = _ACTIVITY_LOG_PATH.open("a", encoding="utf-8")
    log.info("Activity logger opened: %s", _ACTIVITY_LOG_PATH)


@dataclass
class ActivityTrace:
    """One traceable event in the system. Every decision + data point."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str = ""  # pipeline_start | agent_call | price_tick | trade_decision | limit_order
    symbol: str = ""
    direction: str = ""
    strategy: str = ""  # swing | scalper

    # Rich context
    price: Optional[float] = None
    mayne_score: Optional[int] = None
    mayne_detail: Optional[str] = None
    filter_results: Dict[str, Any] = field(default_factory=dict)
    agent_name: Optional[str] = None
    agent_prompt: Optional[str] = None
    agent_response: Optional[str] = None
    agent_latency_ms: Optional[int] = None
    agent_error: Optional[str] = None

    # Trade decision
    trade_id: Optional[int] = None
    manager_decision: Optional[str] = None
    manager_confidence: Optional[int] = None
    limit_price: Optional[float] = None
    order_status: Optional[str] = None

    # Market context snapshot
    funding_rate: Optional[float] = None
    spread_bps: Optional[float] = None
    atr_1m: Optional[float] = None
    volume_usd: Optional[float] = None
    order_book_imbalance: Optional[float] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


def log_activity(trace: ActivityTrace):
    """Write one JSON line to the activity log."""
    try:
        _ensure_log()
        data = asdict(trace)
        # Truncate huge prompt/response fields to avoid bloat
        if data.get("agent_prompt") and len(data["agent_prompt"]) > 10000:
            data["agent_prompt_truncated"] = True
            data["agent_prompt"] = data["agent_prompt"][:10000]
        if data.get("agent_response") and len(data["agent_response"]) > 5000:
            data["agent_response_truncated"] = True
            data["agent_response"] = data["agent_response"][:5000]
        _ACTIVITY_LOG_FILE.write(json.dumps(data, default=str) + "\n")
        _ACTIVITY_LOG_FILE.flush()
    except Exception as exc:
        log.warning("activity log write failed: %s", exc)
