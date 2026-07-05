"""Shared Ollama HTTP client. Handles JSON-mode chat, context window override,
timeout, and fallback parsing."""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Optional

import requests

from ..config import OLLAMA_BASE_URL, GEMMA4_MODEL, NUM_CTX, OLLAMA_TIMEOUT, OLLAMA_TEMPERATURE


log = logging.getLogger("tidoquant")


class OllamaConnectionError(RuntimeError):
    pass


class OllamaClient:
    """Thin wrapper around Ollama's /api/chat endpoint."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = GEMMA4_MODEL,
        timeout: int = OLLAMA_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = OLLAMA_TEMPERATURE,
        max_tokens: int = 1024,
        retry: bool = True,  # Added retry parameter
    ) -> dict:
        """Send a chat request. Returns parsed JSON dict."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": "json",
            "options": {
                "temperature": temperature,
                "num_ctx": NUM_CTX,
                "num_predict": max_tokens,
            },
            "stream": False,
        }

        t0 = time.perf_counter()
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
        except requests.ConnectionError as exc:
            raise OllamaConnectionError(f"cannot connect to Ollama at {self.base_url}: {exc}") from exc
        except requests.Timeout as exc:
            raise OllamaConnectionError(f"Ollama timeout after {self.timeout}s: {exc}") from exc

        if resp.status_code != 200:
            raise OllamaConnectionError(f"Ollama HTTP {resp.status_code}: {resp.text[:300]}")

        raw = resp.json()
        content: str = raw.get("message", {}).get("content", "")
        
        parsed = _extract_json(content)
        
        # Retry mechanism
        if parsed is None and retry:
            log.warning("Ollama JSON parsing failed. Retrying with stricter constraints...")
            return self.chat(
                system=system,
                user=f"{user}\n\nSTRICT INSTRUCTION: Your previous response was not valid JSON. "
                     "Return ONLY valid JSON. No Markdown formatting, no explanations.",
                temperature=0.1,  # Lower temperature for retry
                retry=False,      # No recursive retry
            )
        
        if parsed is None:
            log.warning("Ollama returned non-json content. Falling back to empty dict.")
            return {}

        return parsed

    def health(self) -> bool:
        """Quick check that Ollama is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code != 200:
                return False
            models = resp.json().get("models", [])
            return any(m["name"].startswith(self.model) for m in models)
        except Exception:
            return False


def _extract_json(text: str):
    """Try parsing JSON from raw text, handling markdown code blocks."""
    if not text:
        return None

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` block
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Try extracting first { ... } block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None
