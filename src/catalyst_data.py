"""Free public sentiment + news layers.

  RSS:  CoinDesk + Cointelegraph feeds (via feedparser)
  Reddit: public JSON endpoints (read-only) for r/bitcoin, r/ethereum,
          r/solana, r/binance, r/ripple — used to compute mention velocity
          on the target pair's name.

If a feed fetch fails (network, 5xx), that layer reports neutral 0 and the
scorer still works. Failure is logged but never fatal.

Anti-rate-limiting for Reddit:
  - Rotating User-Agent pool (Chrome/Firefox/Safari/Edge, Win/Mac/Linux)
  - Browser-like headers (Accept, Accept-Language, etc.)
  - Random sleep 0.5-3s between requests
  - Exponential backoff on 429 (up to 3 retries)
  - One session per call (no cookie persistence that fingerprints)
"""
from __future__ import annotations

import logging
import random
import re
import time
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import feedparser
import requests

from .logger import utc_now


RSS_FEEDS = (
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
)


# Rotating User-Agent pool — real browser strings across OSes.
_USER_AGENTS = [
    # Chrome 120+ Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Chrome macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Safari macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Chrome Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


def _random_headers() -> dict:
    """Return headers mimicking a real browser session."""
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }


def _reddit_request(
    url: str,
    log: logging.Logger,
    retries: int = 3,
) -> Optional[dict]:
    """Send a Reddit GET with rotating UA, random delay, and 429 backoff."""
    for attempt in range(retries):
        # Random sleep before each attempt to avoid pattern detection.
        sleep_sec = random.uniform(0.8, 2.5) * (attempt + 1)
        log.debug(
            "reddit sleeping %.2fs before %s (attempt %d)",
            sleep_sec, url, attempt,
        )
        time.sleep(sleep_sec)

        try:
            resp = requests.get(
                url,
                headers=_random_headers(),
                timeout=12.0,
            )
        except requests.RequestException as exc:
            log.warning("reddit network error: %s", exc)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            continue

        if resp.status_code == 429:
            wait = 2 ** attempt + random.uniform(0.5, 2.0)
            log.warning(
                "reddit 429 rate-limited, backing off %.2fs", wait,
            )
            time.sleep(wait)
            continue

        if resp.status_code == 403:
            # Reddit blocks the IP/range entirely — do not retry.
            log.warning("reddit 403 forbidden on %s", url)
            return None

        if not resp.ok:
            log.warning("reddit %s on %s", resp.status_code, url)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            continue

        try:
            return resp.json()
        except ValueError:
            log.warning("reddit non-json response on %s", url)
            return None

    log.warning("reddit exhausted %d retries for %s", retries, url)
    return None


POSITIVE_WORDS = {
    "etf", "approval", "approve", "approved", "bullish", "rally",
    "breakout", "all-time high", "ath", "inflows", "institutional",
    "accumulate", "accumulation", "adoption", "upgrade", "partnership",
    "launch", "launches", "surge", "soar", "soars", "record",
    "buyback", "halving", "demand", "short squeeze",
}

NEGATIVE_WORDS = {
    "hack", "hacked", "exploit", "exploited", "lawsuit", "ban", "banned",
    "bearish", "crash", "dump", "plunge", "plunges", "fear", "sec",
    "fraud", "scam", "rug", "downgrade", "outflow", "outflows",
    "regulation", "probe", "investigation", "fine", "penalty",
    "delisting", "insolvent", "insolvency", "liquidation",
}


@dataclass
class NewsTone:
    score: float            # -1 .. +1
    positive_hits: int
    negative_hits: int
    article_count: int
    headline_samples: List[str]


@dataclass
class RedditPulse:
    score: float            # -1 .. +1   (mention velocity polarity)
    bull_hits: int
    bear_hits: int
    post_count: int


def _keyword_hits(text: str, vocabulary) -> int:
    text_l = text.lower()
    return sum(1 for w in vocabulary if w in text_l)


def fetch_news_tone(symbol: str, lookback_hours: int = 24) -> NewsTone:
    """Pull recent headlines from RSS, score lexicon-based tone."""
    log = logging.getLogger("tidoquant")
    sym_l = symbol.lower().replace("usdt", "")
    cutoff = utc_now().timestamp() - lookback_hours * 3600

    pos = neg = n = 0
    samples: List[str] = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as exc:
            log.warning("rss fetch failed for %s: %s", url, exc)
            continue
        for entry in feed.entries[:30]:
            published = getattr(entry, "published_parsed", None) or getattr(
                entry, "updated_parsed", None
            )
            if published:
                import calendar
                ts = calendar.timegm(published)
                if ts < cutoff:
                    continue
            title = getattr(entry, "title", "") or ""
            summary = getattr(entry, "summary", "") or ""
            blob = f"{title} {summary}".lower()
            if sym_l not in blob:
                continue
            n += 1
            p_hits = _keyword_hits(blob, POSITIVE_WORDS)
            ne_hits = _keyword_hits(blob, NEGATIVE_WORDS)
            pos += p_hits
            neg += ne_hits
            if len(samples) < 4:
                samples.append(title)

    if n == 0:
        return NewsTone(score=0.0, positive_hits=0,
                        negative_hits=0, article_count=0,
                        headline_samples=[])
    raw = (pos - neg) / max(1, (pos + neg))
    return NewsTone(
        score=max(-1.0, min(1.0, raw)),
        positive_hits=pos,
        negative_hits=neg,
        article_count=n,
        headline_samples=samples,
    )


REDDIT_SUBS = {
    "BTCUSDT": ("bitcoin", "btc"),
    "ETHUSDT": ("ethereum", "eth"),
    "SOLUSDT": ("solana", "sol"),
    "BNBUSDT": ("binance", "bnb"),
    "XRPUSDT": ("ripple", "xrp"),
}

WORD_TOKEN_RE = re.compile(r"\b\w+\b", flags=re.UNICODE)


def fetch_reddit_pulse(
    symbol: str,
    subreddit: Optional[str] = None,
    limit: int = 25,
) -> RedditPulse:
    """Public JSON endpoint: top posts in last 24h for the pair's sub.

    Sentiment polarity is a crude lexicon match on headlines + selftext.
    Anti-rate-limiting: rotating UA, random delay before call, 429 backoff.
    """
    log = logging.getLogger("tidoquant")
    sub, ticker = REDDIT_SUBS.get(
        symbol, (subreddit or "CryptoCurrency", symbol.lower())
    )
    url = f"https://www.reddit.com/r/{sub}/top.json?limit={limit}&t=day"
    data = _reddit_request(url, log)

    if data is None:
        return RedditPulse(score=0.0, bull_hits=0,
                           bear_hits=0, post_count=0)

    children = data.get("data", {}).get("children", [])
    bull = bear = 0
    n = 0
    for child in children:
        d = child.get("data", {})
        title = (d.get("title") or "").lower()
        body = (d.get("selftext") or "").lower()
        blob = f"{title} {body}"
        if ticker not in blob:
            continue
        n += 1
        bull += _keyword_hits(blob, POSITIVE_WORDS)
        bear += _keyword_hits(blob, NEGATIVE_WORDS)

    if n == 0:
        return RedditPulse(score=0.0, bull_hits=0,
                           bear_hits=0, post_count=0)
    raw = (bull - bear) / max(1, (bull + bear))
    return RedditPulse(score=max(-1.0, min(1.0, raw)),
                       bull_hits=bull, bear_hits=bear, post_count=n)


def safe_keyword_match(text: str, vocab) -> Counter:
    return Counter({w: text.lower().count(w) for w in vocab})
