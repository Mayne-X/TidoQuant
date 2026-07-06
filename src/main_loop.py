"""Main Bot Loop — orchestrates scanning, gating, pipeline, and execution.

Supports dual strategies:
  SWING  — 1h/4h/12h Mayne gate + full agent pipeline
  SCALPER — 1m/5m/15m/30m + 1h bias filter + scalper pipeline
"""
from __future__ import annotations

import logging
import random
import time as ttime
from typing import Dict, List, Optional

from .agents.ollama_client import OllamaClient, OllamaConnectionError
from .binance_client import safe_client, Candle
from .config import PAIRS, SCAN_INTERVAL_SECONDS, STARTING_EQUITY
from .core.pipeline import Pipeline
from .core.signal_packet import SignalPacket
from .database import migrate, snapshot_equity, dashboard_summary
from .mayne_scorer import score_mayne
from .scalper_mayne import score_scalper_mayne
from .filter_chain import FilterChain
from .limit_engine import LimitOrderEngine

log = logging.getLogger("tidoquant")


def _fetch_swing_candles(client, symbol):
    """Fetch HTF candles for swing strategy: 1h/4h/12h + sweep 15m + entry 5m."""
    from .config import MAYNE_TF_WEIGHTS
    tf_candles = {}
    for tf_label, _weight, limit in MAYNE_TF_WEIGHTS:
        tf_candles[tf_label] = client.klines(symbol, tf_label, limit=limit)
    sweep = client.klines(symbol, "15m", limit=144)
    entry = client.klines(symbol, "5m", limit=144)
    return tf_candles, sweep, entry


def _fetch_scalper_candles(client, symbol):
    """Fetch LTF candles for scalper strategy: 1m/5m/15m/30m + 1h bias + 1m entry."""
    from .config import SCALPER_TF_WEIGHTS
    lt_candles = {}
    for tf_label, _weight, limit in SCALPER_TF_WEIGHTS:
        lt_candles[tf_label] = client.klines(symbol, tf_label, limit=limit)
    htf_bias = client.klines(symbol, "1h", limit=100)
    sweep_1m = client.klines(symbol, "1m", limit=100)
    entry_1m = client.klines(symbol, "1m", limit=100)
    return lt_candles, htf_bias, sweep_1m, entry_1m


def run_cycle(client, pipeline: Optional[Pipeline], engine: LimitOrderEngine, filter_chain: FilterChain):
    """One full scan cycle across all symbols."""
    for symbol in PAIRS:
        try:
            _process_symbol(symbol, client, pipeline, engine, filter_chain)
        except Exception as exc:
            log.error("error processing %s: %s", symbol, exc, exc_info=True)
        ttime.sleep(random.uniform(0.3, 1.0))

    # Update positions (SL/TP checks + limit order fills)
    for symbol in PAIRS:
        try:
            entry = client.klines(symbol, "1m", limit=1)
            if entry:
                candle = entry[-1]
                engine.tick(symbol, candle.high, candle.low, candle.close)
        except Exception as exc:
            log.warning("tick update failed for %s: %s", symbol, exc)

    # Log active positions
    if engine._open_positions:
        log.info("--- ACTIVE POSITIONS ---")
        for tid, pos in engine._open_positions.items():
            log.info("Trade %d | %s %s | Entry: %.4f | %s",
                     tid, pos.symbol, pos.direction, pos.entry_price or pos.limit_price, pos.strategy)
    elif engine._orders:
        log.info("--- PENDING LIMIT ORDERS (%d) ---", len(engine._orders))

    # Snapshot
    snapshot_equity(engine.equity)
    summary = dashboard_summary()
    log.info("Cycle done. Equity=$%.2f Trades=%d Wins=%d Losses=%d Exposure=$%.2f",
             engine.equity, summary["total_trades"], summary["wins"],
             summary["losses"], engine.get_gross_exposure())


def _process_symbol(symbol: str, client, pipeline: Optional[Pipeline],
                    engine: LimitOrderEngine, filter_chain: FilterChain):
    """Process one symbol: run Mayne gate + scalper gate + pipelines."""
    from .database import insert_placeholder_trade
    from .database.activity_logger import log_activity, ActivityTrace

    # ─── 1. Fetch SWING data ───
    tf_candles, sweep_candles, entry_candles = _fetch_swing_candles(client, symbol)
    if not entry_candles:
        return

    price = entry_candles[-1].close
    mark_info = client.mark_price(symbol)
    fund_info = client.funding_rate(symbol)
    funding_rate = mark_info.get("rate", 0.0)

    # ─── 2. SwING GATE — Mayne ───
    mayne = score_mayne(tf_candles, sweep_candles, entry_candles, "long")
    if not mayne.passed_gate:
        mayne_short = score_mayne(tf_candles, sweep_candles, entry_candles, "short")
        if mayne_short.passed_gate:
            mayne = mayne_short
        else:
            log.info("%s: SWING Mayne long=%d short=%d best=%d — gate missed",
                     symbol, mayne.score, mayne_short.score,
                     max(mayne.score, mayne_short.score))

            # ─── Even if swing misses, try SCALPER ───
            _try_scalper(symbol, client, pipeline, engine, filter_chain,
                         price, funding_rate, mark_info)
            return

    log.info("%s: SWING Mayne %d (%s) — gate passed ✓", symbol, mayne.score, mayne.detail)

    # ─── 3. SWING Pipeline ───
    packet = SignalPacket(
        symbol=symbol,
        direction=mayne.direction,
        mayne=mayne,
        strategy="swing",
        entry_price=price,
        current_price=price,
        tf_candles=tf_candles,
        sweep_candles=sweep_candles,
        entry_candles=entry_candles,
        funding_rate=funding_rate,
        mark_price=mark_info.get("mark", price),
        open_interest=client.open_interest_history(symbol),
        long_short_ratio=client.long_short_account_ratio(symbol),
    )

    if pipeline is not None:
        packet = pipeline.run(packet)
    else:
        packet.manager_decision = "GO"
        packet.manager_confidence = mayne.score
        packet.manager_reasoning = f"Mayne-only. Score {mayne.score}."
        packet.stop_loss = price * 0.98
        packet.take_profit = price * 1.04
        packet.leverage = 2
        packet.position_size_usd = STARTING_EQUITY * 0.01 * 2

    # ─── 4. SWING Execute (limit order) ───
    if packet.manager_decision == "GO":
        engine.open_limit_from_pipeline(
            packet.trade_id, symbol, packet.direction,
            price, mayne,
        )
        log.info("%s: SWING LIMIT PLACED id=%d %s conf=%d",
                 symbol, packet.trade_id, packet.direction,
                 packet.manager_confidence or 0)
    else:
        log.info("%s: SWING NO-GO (conf=%d)", symbol, packet.manager_confidence or 0)

    # Log activity
    log_activity(ActivityTrace(
        event_type="trade_decision",
        symbol=symbol, direction=mayne.direction, strategy="swing",
        price=price, mayne_score=mayne.score, mayne_detail=mayne.detail,
        trade_id=packet.trade_id,
        manager_decision=packet.manager_decision,
        manager_confidence=packet.manager_confidence,
        funding_rate=funding_rate,
    ))

    # ─── Also try scalper on this symbol ───
    _try_scalper(symbol, client, pipeline, engine, filter_chain,
                 price, funding_rate, mark_info)


def _try_scalper(symbol: str, client, pipeline: Optional[Pipeline],
                 engine: LimitOrderEngine, filter_chain: FilterChain,
                 price: float, funding_rate: float, mark_info: dict):
    """Attempt scalper strategy on this symbol."""
    from .database import insert_placeholder_trade
    from .database.activity_logger import log_activity, ActivityTrace

    try:
        lt_candles, htf_bias, sweep_1m, entry_1m = _fetch_scalper_candles(client, symbol)
        if not entry_1m or not lt_candles:
            return

        price_1m = entry_1m[-1].close

        # ─── Filter Chain ───
        filter_result = filter_chain.run(
            symbol=symbol,
            direction="long",
            lt_candles=lt_candles,
            htf_candles=htf_bias,
            entry_candles=entry_1m,
            funding_rate=funding_rate,
        )

        if not filter_result.passed:
            log.info("%s: SCALPER filter rejected (%s) score=%d",
                     symbol, filter_result.reject_reason, filter_result.score)
            log_activity(ActivityTrace(
                event_type="filter_rejected",
                symbol=symbol, direction="", strategy="scalper",
                price=price_1m,
                filter_results=filter_result.filters,
            ))
            return

        # ─── Scalper Mayne ───
        scalp = score_scalper_mayne(lt_candles, htf_bias, entry_1m, sweep_1m, "long")
        if not scalp.passed_gate:
            scalp_short = score_scalper_mayne(lt_candles, htf_bias, entry_1m, sweep_1m, "short")
            if scalp_short.passed_gate:
                scalp = scalp_short
            else:
                log.info("%s: SCALPER Mayne long=%d short=%d — gate missed",
                         symbol, scalp.score, scalp_short.score)
                return

        log.info("%s: SCALPER Mayne %d (%s) — gate passed ✓",
                 symbol, scalp.score, scalp.detail)

        # ─── Scalper Pipeline (abbreviated) ───
        trade_id = insert_placeholder_trade(symbol, scalp.direction, price_1m)

        packet = SignalPacket(
            symbol=symbol,
            direction=scalp.direction,
            mayne=score_mayne({}, [], entry_1m, scalp.direction),  # minimal Mayne
            strategy="scalper",
            entry_price=price_1m,
            current_price=price_1m,
            scalper_result=scalp,
            scalper_lt_candles=lt_candles,
            scalper_htf_candles=htf_bias,
            scalper_sweep_candles=sweep_1m,
            scalper_entry_candles=entry_1m,
            filter_result=filter_result,
            time_stop_candles=12,  # auto-close after 12 candles
            trade_id=trade_id,
        )

        if pipeline is not None:
            # Reuse same pipeline — agents will get scalper context
            packet = pipeline.run(packet)
        else:
            packet.manager_decision = "GO"
            packet.manager_confidence = scalp.score

        # ─── Execute scalper (limit order) ───
        if packet.manager_decision == "GO":
            limit_price = scalp.limit_price or (price_1m * 0.999 if scalp.direction == "long" else price_1m * 1.001)
            sl = limit_price * 0.99 if scalp.direction == "long" else limit_price * 1.01
            tp = limit_price * 1.015 if scalp.direction == "long" else limit_price * 0.985
            engine.place_limit_order(
                trade_id=trade_id,
                symbol=symbol,
                direction=scalp.direction,
                limit_price=limit_price,
                stop_loss=sl,
                take_profit=tp,
                position_size=STARTING_EQUITY * 0.005,
                leverage=2,
                strategy="scalper",
                time_stop_candles=12,
            )
            log.info("%s: SCALPER LIMIT id=%d @ %.4f sl=%.4f tp=%.4f",
                     symbol, trade_id, limit_price, sl, tp)

        # Log scalper activity
        log_activity(ActivityTrace(
            event_type="scalper_signal",
            symbol=symbol, direction=scalp.direction, strategy="scalper",
            price=price_1m, mayne_score=scalp.score, mayne_detail=scalp.detail,
            filter_results=filter_result.filters,
            trade_id=trade_id,
            manager_decision=packet.manager_decision,
            manager_confidence=packet.manager_confidence,
            limit_price=scalp.limit_price,
            funding_rate=funding_rate,
        ))

        # Update trade in DB
        from .database import update_trade
        update_trade(trade_id, packet)

    except Exception as exc:
        log.warning("scalper error for %s: %s", symbol, exc)


def run_loop():
    migrate()
    client = safe_client()
    engine = LimitOrderEngine()
    filter_chain = FilterChain()

    ollama = OllamaClient()
    pipeline = None
    try:
        if ollama.health():
            pipeline = Pipeline(ollama)
            log.info("Ollama connected — dual-strategy pipeline active")
        else:
            log.warning("Ollama not reachable — Mayne-only mode")
    except OllamaConnectionError:
        log.warning("Ollama connection failed — Mayne-only mode")

    log.info("TidoQuant v3 starting (swing: 1h/4h/12h + scalper: 1m/5m/15m/30m)...")

    while True:
        if not engine.is_trading_allowed():
            log.warning("CIRCUIT BREAKER ACTIVE! equity=%.2f", engine.equity)
        else:
            run_cycle(client, pipeline, engine, filter_chain)

        ttime.sleep(SCAN_INTERVAL_SECONDS)
