"""
Free RSS news ingestion for the LLM catalyst analyst.

Pulls recent headlines from a handful of well-known, freely accessible market
RSS feeds (no API key) and filters them to a symbol by matching the NSE
symbol or its company name (sourced from the NIFTY 100 universe CSV, so no
separate alias file is needed).

This module is best-effort: any network/parse failure yields an empty list,
which `analyst.py` already treats as "(no headlines available)" — it never
blocks or fails the pipeline closed.
"""

from __future__ import annotations

import logging
from typing import Optional

import feedparser

from app import cache, universe
from app.evidence import content_hash
from config.settings import get_settings

logger = logging.getLogger(__name__)

_RSS_FEEDS = [
    "https://economictimes.indiatimes.com/markets/stocks/news/rssfeeds/2146842.cms",
    "https://www.moneycontrol.com/rss/business.xml",
    "https://www.business-standard.com/rss/markets-106.rss",
]
_MAX_HEADLINES = 8


def _matches(title: str, symbol: str, company_name: Optional[str]) -> bool:
    text = title.lower()
    if symbol.lower() in text:
        return True
    if company_name:
        first_word = company_name.split()[0].strip(".,").lower()
        if len(first_word) > 3 and first_word in text:
            return True
    return False


def _titles_from_feed(feed_url: str, symbol: str, company_name: Optional[str]) -> list[str]:
    try:
        parsed = feedparser.parse(feed_url)
    except Exception as exc:  # noqa: BLE001 - one bad feed must not skip the others
        logger.debug("RSS feed %s failed: %s", feed_url, exc)
        return []
    titles = (
        (getattr(entry, "title", "") or "").strip()
        for entry in getattr(parsed, "entries", [])
    )
    return [title for title in titles if title and _matches(title, symbol, company_name)]


def fetch_headlines(symbol: str) -> list[str]:
    """Best-effort recent headlines for `symbol` from free market RSS feeds."""
    cache_key = content_hash({"symbol": symbol.upper(), "feeds": _RSS_FEEDS})
    cached, _cache_hit = cache.get_value_with_status("news", cache_key)
    if cached is not None:
        return list(cached)
    try:
        company_names = universe.get_symbol_company_names()
    except Exception as exc:  # noqa: BLE001 - alias lookup must never block news fetch
        logger.debug("Could not load company-name aliases: %s", exc)
        company_names = {}
    company_name = company_names.get(symbol.upper())

    matched: list[str] = []
    for feed_url in _RSS_FEEDS:
        matched.extend(_titles_from_feed(feed_url, symbol, company_name))
        if len(matched) >= _MAX_HEADLINES:
            break

    seen: set[str] = set()
    deduped: list[str] = []
    for headline in matched:
        if headline not in seen:
            seen.add(headline)
            deduped.append(headline)
    result = deduped[:_MAX_HEADLINES]
    cache.set_value("news", cache_key, result, get_settings().NEWS_CACHE_MINUTES)
    return result
