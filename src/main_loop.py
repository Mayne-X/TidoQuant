"""Main Bot Loop — orchestrates scanning, gating, pipeline, and execution."""
from __future__ import annotations

import logging
import random
import time

from .agents.ollama_client import OllamaClient, OllamaConnectionError
from .binance_client import safe_client
from .config import PAIRS, SCAN_INTERVAL_SECONDS, STARTING_EQUITY, TIMEFRAMES
from .core.pipeline import Pipeline
from .core.signal_packet import SignalPacket
from .database import (
    dashboard_summary,
    migrate,
    snapshot_equity,
)
from .mayne_scorer import score_mayne
from .paper_engine import PaperEngine

log = logging.getLogger("tidoquant")


def _fetch_tf_candles(client, symbol):
    """Fetch all 3 HTF candle sets + sweep + entry in parallel-ish."""
    tf_candles = {}
    for tf_label, _weight, limit in TIMEFRAMES:
        tf_candles[tf_label] = client.klines(symbol, tf_label, limit=limit)
    sweep = client.klines(symbol, "15m", limit=144)    # ~36h of 15m
    entry = client.klines(symbol, "5m", limit=144)     # ~12h of 5m
    return tf_candles, sweep, entry


def run_loop():
    migrate()
    client = safe_client()
    engine = PaperEngine()

    ollama = OllamaClient()
    pipeline = None
    try:
        if ollama.health():
            pipeline = Pipeline(ollama)
            log.info("Ollama connected — multi-agent pipeline active")
        else:
            log.warning("Ollama not reachable — Mayne-only mode")
    except OllamaConnectionError:
        log.warning("Ollama connection failed — Mayne-only mode")

    log.info("TidoQuant v2 starting (multi-timeframe: 1h/4h/12h)...")

    while True:
        if not engine.is_trading_allowed():
            log.warning("Circuit breaker active! Trading paused.")
        else:
            for symbol in PAIRS:
                try:
                    tf_candles, sweep_candles, entry_candles = _fetch_tf_candles(client, symbol)
                    if not entry_candles:
                        continue

                    price = entry_candles[-1].close
                    mark_info = client.mark_price(symbol)
                    fund_info = client.funding_rate(symbol)

                    # 1. GATEKEEPER — Mayne on multi-timeframe
                    mayne = score_mayne(tf_candles, sweep_candles, entry_candles, "long")

                    if not mayne.passed_gate:
                        mayne_short = score_mayne(tf_candles, sweep_candles, entry_candles, "short")
                        if mayne_short.passed_gate:
                            mayne = mayne_short
                        else:
                            log.info(
                                "%s: Mayne long=%d short=%d best=%d — gate missed (need ≥60)",
                                symbol, mayne.score, mayne_short.score,
                                max(mayne.score, mayne_short.score),
                            )
                            continue

                    log.info(
                        "%s: Mayne score %d (%s) — gate passed",
                        symbol, mayne.score, mayne.detail,
                    )

                    # 2. Build signal packet
                    packet = SignalPacket(
                        symbol=symbol,
                        direction=mayne.direction,
                        mayne=mayne,
                        entry_price=price,
                        current_price=price,
                        tf_candles=tf_candles,
                        sweep_candles=sweep_candles,
                        entry_candles=entry_candles,
                        funding_rate=mark_info.get("rate", 0.0),
                        mark_price=mark_info.get("mark", price),
                        open_interest=client.open_interest_history(symbol),
                        long_short_ratio=client.long_short_account_ratio(symbol),
                    )

                    # 3. If pipeline is active, run it
                    if pipeline is not None:
                        packet = pipeline.run(packet)
                    else:
                        packet.manager_decision = "GO"
                        packet.manager_confidence = mayne.score
                        packet.manager_reasoning = (
                            f"Mayne-only mode (Ollama unavailable). Score {mayne.score}."
                        )
                        packet.stop_loss = price * 0.98
                        packet.take_profit = price * 1.04
                        packet.leverage = 2
                        packet.position_size_usd = STARTING_EQUITY * 0.01 * 2

                    # 4. Execute if manager approves
                    if packet.manager_decision == "GO":
                        engine.open_position(packet, packet.trade_id)
                        log.info(
                            "%s: TRADE OPENED id=%d direction=%s size=$%.2f "
                            "SL=%.2f TP=%.2f (manager conf=%d)",
                            symbol, trade_id, packet.direction,
                            packet.position_size_usd or 0,
                            packet.stop_loss or 0, packet.take_profit or 0,
                            packet.manager_confidence or 0,
                        )
                    else:
                        log.info(
                            "%s: NO-GO (manager confidence=%d)",
                            symbol, packet.manager_confidence or 0,
                        )

                except Exception as exc:
                    log.error("error processing %s: %s", symbol, exc, exc_info=True)

                time.sleep(random.uniform(0.3, 1.5))

            # Update open positions
            for symbol in PAIRS:
                try:
                    entry = client.klines(symbol, "5m", limit=1)
                    if entry:
                        engine.update_positions(symbol, entry[-1].close)
                except Exception as exc:
                    log.warning("update price failed for %s: %s", symbol, exc)

            # Snapshot equity
            eq = engine.equity
            snapshot_equity(eq)
            summary = dashboard_summary()
            log.info(
                "Cycle complete. Equity=$%.2f Trades=%d Wins=%d Losses=%d",
                eq, summary["total_trades"], summary["wins"], summary["losses"],
            )

        time.sleep(SCAN_INTERVAL_SECONDS)
