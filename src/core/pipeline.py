"""Pipeline — orchestrates the full agent sequence for a single symbol.

Sequence (executed only if Mayne gate passes):
  Researcher → Sentiment → Bull R1 → Bear R1 → Bull R2 → Bear R2 → Treasury → Manager
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
from ..database import log_agent_call


log = logging.getLogger("tidoquant")

PIPELINE_TIMEOUT: int = 120  # max seconds for one full pipeline run


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
        """Run all agents sequentially. If any agent fails, the pipeline
        continues (agent_error is recorded on the packet). Manager still
        decides with the data available."""
        started = time.monotonic()
        trade_id = -1  # assigned later if manager says GO

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
                packet = agent.run(packet)
            except Exception as exc:
                log.error("pipeline: %s crashed: %s", agent.name, exc)
                packet.agent_errors.append(f"{agent.name}_crash: {exc}")

        log.info(
            "pipeline complete for %s: manager=%s conf=%d errors=%d",
            packet.symbol,
            packet.manager_decision,
            packet.manager_confidence or 0,
            len(packet.agent_errors),
        )
        return packet

    def health_check(self, ollama: OllamaClient) -> bool:
        """Verify Ollama is reachable before starting a cycle."""
        try:
            return ollama.health()
        except Exception:
            return False
