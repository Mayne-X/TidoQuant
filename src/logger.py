"""Logger. Single source for plain UTC-timestamped log lines."""
from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """One logger for the whole bot. UTC timestamps, no color codes."""
    root = logging.getLogger("tidoquant")
    if root.handlers:
        return root
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    )
    # Force UTC in formatter: use time.gmtime
    logging.Formatter.converter = time.gmtime
    root.addHandler(handler)
    root.propagate = False
    return root


def env_log_level() -> int:
    raw = os.environ.get("TIDOQUANT_LOG", "INFO").upper()
    return getattr(logging, raw, logging.INFO)
