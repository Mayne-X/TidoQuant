"""Main Bot Loop.

Orchestrates all components every 15 minutes.
Includes random inter-symbol delays to avoid rate-limit patterns.
"""
import random
import time
import logging
from .config import PAIRS, SCAN_INTERVAL_SECONDS, MIN_CONFIDENCE
from .binance_client import safe_client
from .indicators import find_swings
from .mayne_scorer import score_mayne
from .catalyst_scorer import score_catalyst
from .adversarial_debate import debate_trade
from .finance_manager import calculate_position
from .paper_engine import PaperEngine

def run_loop():
    log = logging.getLogger("tidoquant")
    client = safe_client()
    engine = PaperEngine(journal_path="journal/trades.jsonl")
    
    log.info("Starting bot loop...")
    
    while True:
        if not engine.is_trading_allowed():
            log.warning("Circuit breaker active! Trading paused.")
        else:
            for symbol in PAIRS:
                try:
                    # 1. Fetch Data
                    htf = client.klines(symbol, "4h", limit=100)
                    ltf = client.klines(symbol, "15m", limit=100)
                    entry = client.klines(symbol, "5m", limit=100)

                    # 2. Score
                    mayne = score_mayne(htf, ltf, entry, direction="long")
                    catalyst = score_catalyst(symbol)
                    total = mayne + catalyst

                    # 3. Debate + Execute
                    if total >= MIN_CONFIDENCE and debate_trade(symbol, mayne, catalyst, entry):
                        pos = calculate_position(total, engine.equity)
                        engine.open_position({
                            "symbol": symbol,
                            "direction": "long",
                            "entry": entry[-1].close,
                            "sl": entry[-1].close * 0.98,
                            "tp": entry[-1].close * 1.04,
                            **pos
                        })

                    # 4. Update existing
                    engine.update_price(symbol, entry[-1].close)
                except Exception as exc:
                    log.error("error processing %s: %s", symbol, exc, exc_info=True)

                # Jitter between symbols to de-pattern API calls
                time.sleep(random.uniform(0.3, 1.5))

        log.info("Cycle complete. Sleeping %ds...", SCAN_INTERVAL_SECONDS)
        time.sleep(SCAN_INTERVAL_SECONDS)
