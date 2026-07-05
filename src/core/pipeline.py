"""Pipeline — orchestrates the full agent sequence for a single symbol.

Sequence (executed only if Mayne gate passes):
  Researcher → Sentiment → Bull R1 → Bear R1 → Bull R2 → Bear R2 → Treasury → Manager

Every agent call is logged to the database with full prompt/response/latency.
"""
from __future__ import annotations

import logging
import time
from typing import List

from ..agents.ollama_client import OllamaClient, OllamaConnectionError
from ..agents.researcher import ResearcherAgent
from ..agents.sentiment import SentimentAgent
from ..agents.bull import BullAgent
from ..agents.bear import BearAgent
from ..agents.treasury import TreasuryAgent
from ..agents.manager import ManagerAgent
from ..core.signal_packet import SignalPacket
from ..core.memory import build_performance_briefing
from ..database import (
    insert_placeholder_trade,
    log_agent_call,
    update_trade,
)


log = logging.getLogger("tidoquant")

PIPELINE_TIMEOUT: int = 600  # max seconds for one full pipeline run (accounts for cold model load)


class Pipeline:
    """Sequential agent pipeline. Returns the enriched packet."""

    def __init__(self, ollama: OllamaClient):
        self.agents = [
            ResearcherAgent(ollama),
            SentimentAgent(ollama),
            BullAgent(ollama, round=1),
            BearAgent(ollama, round=1),
            BullAgent(ollama, round=2),
            BearAgent(ollama, round=2),
            TreasuryAgent(ollama),
            ManagerAgent(ollama),
        ]

    def run(self, packet: SignalPacket) -> SignalPacket:
        """Run all agents sequentially. All agent calls are logged to the
        database with full prompt/response/latency. Creates a placeholder
        trade before the pipeline so agent_logs have a valid trade_id.
        After pipeline: if GO the trade is updated with full data and
        status='open'; otherwise status='rejected'."""
        started = time.monotonic()

        # Create placeholder trade so all agent calls are logged against it
        trade_id = insert_placeholder_trade(
            packet.symbol, packet.direction, packet.entry_price,
        )
        packet.trade_id = trade_id
        log.info("pipeline placeholder trade id=%d for %s", trade_id, packet.symbol)

        # Inject performance memory/briefing for agents
        memory_briefing = build_performance_briefing()
        
        for agent in self.agents:
            elapsed = time.monotonic() - started
            if elapsed > PIPELINE_TIMEOUT:
                log.warning(
                    "pipeline timeout after %.0fs for %s, aborting",
                    elapsed, packet.symbol,
                )
                packet.agent_errors.append("pipeline_timeout")
                break

            try:
                # Treasury and Manager receive the memory briefing
                if agent.name in ["treasury", "manager"]:
                    packet.memory_briefing = memory_briefing
                
                packet = agent.run(packet, trade_id=trade_id)
            except Exception as exc:
                log.error("pipeline: %s crashed: %s", agent.name, exc)
                packet.agent_errors.append(f"{agent.name}_crash: {exc}")

        # Update placeholder trade with final pipeline output
        update_trade(trade_id, packet)

        log.info(
            "pipeline complete for %s: manager=%s conf=%d errors=%d "
            "trade_id=%d status=%s",
            packet.symbol,
            packet.manager_decision,
            packet.manager_confidence or 0,
            len(packet.agent_errors),
            trade_id,
            packet.manager_decision or 'rejected',
        )
        return packet

    def health_check(self, ollama: OllamaClient) -> bool:
        """Verify Ollama is reachable before starting a cycle."""
        try:
            return ollama.health()
        except Exception:
            return False
