"""Abstract base class for all TidoQuant AI agents."""
from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from ..core.signal_packet import SignalPacket
from .ollama_client import OllamaClient


log = logging.getLogger("tidoquant")


class BaseAgent(ABC):
    """Every agent follows the same pattern:
    1. Build a system prompt (role/persona)
    2. Build a user prompt (context from current packet state)
    3. Call Ollama
    4. Parse structured JSON response
    5. Enrich the signal packet
    """

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    @property
    @abstractmethod
    def name(self) -> str:
        """Short agent identifier, e.g. 'researcher'."""
        ...

    @abstractmethod
    def system_prompt(self) -> str:
        """The persona / role definition sent as system message."""
        ...

    def user_prompt(self, packet: SignalPacket) -> str:
        """Build context from the packet. Override per agent."""
        return json.dumps(self._packet_input(packet), indent=2)

    def _packet_input(self, packet: SignalPacket) -> dict:
        """Subset of packet fields relevant to this agent."""
        return {
            "symbol": packet.symbol,
            "direction": packet.direction,
            "entry_price": packet.entry_price,
            "current_price": packet.current_price,
        }

    def run(self, packet: SignalPacket) -> SignalPacket:
        """Execute the agent: build prompts → call Ollama → parse → enrich packet.
        If Ollama fails, logs error, sets agent_error on packet, and returns
        packet unchanged."""
        t0 = time.perf_counter()
        system = self.system_prompt()
        user = self.user_prompt(packet)

        try:
            result = self.ollama.chat(system=system, user=user)
            elapsed = int((time.perf_counter() - t0) * 1000)
            log.info(
                "%s agent responded in %dms (score=%s)",
                self.name, elapsed, result.get("score", "N/A"),
            )
            packet = self.enrich(packet, result)
        except Exception as exc:
            elapsed = int((time.perf_counter() - t0) * 1000)
            log.warning("%s agent failed after %dms: %s", self.name, elapsed, exc)
            packet.agent_errors.append(f"{self.name}: {exc}")

        return packet

    @abstractmethod
    def enrich(self, packet: SignalPacket, result: dict) -> SignalPacket:
        """Parse the Ollama response and write to the packet."""
        ...
