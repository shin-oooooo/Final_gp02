"""HTTP-based headline fetchers: RSS feeds + NewsAPI.

Extracted from ``research/sentiment_proxy.py`` (2026-04-21). The two source
families share an HTTP request style (``requests`` / ``feedparser``) and a
common seed-gate / date-parse post-processing pipeline, so they live side by
side.

Public entry points (re-exported from ``sentiment_proxy``):
    ``_fetch_rss_headline_items`` — English market RSS pool.
    ``_fetch_geo_seed_rss_items`` — Google News geo-seed RSS pool.
    ``_fetch_newapi_headline_items`` — NewsAPI everything-endpoint fetcher.
"""

from __future__ import annotations

import logging
import os
import random
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from research.crawl4ai_config import CRAWL4AI_TITLE_SEED_TERMS
from research.sentiment.core import (
    HeadlineFetch,
    _dedupe_prefer_dated,
    _env_truthy,
    _estimate_news_horizon_days,
    _parse_loose_date,
    _parse_relative_publication_hint,
    _sort_dated_asc,
    _sort_dated_desc,
)
from research.sentiment.curation import (
    _HEADLINE_PAGE_NAV_JUNK_RE,
    _NAV_JUNK_RE,
    _headline_passes_seed_gate,
    _latin_word_count,
    _seed_gate_enabled_for_all_pools,
)
from research.sentiment_calendar import (
    DEFAULT_TEST_START,
    TEST_WINDOW_MIN_DAYS,
    calendar_span_earliest_to_asof,
    effective_test_span_days,
    median_consecutive_gap_days,
    parse_iso_date,
    test_end_for_start,
    today_iso,
)

logger = logging.getLogger(__name__)

# ── English market news (RSS) ─────────────────────────────────────────────────
# BBC Business and NYT Business carry 10–20+ calendar days of history in their
# feeds, which is essential for generating a multi-node S_t time series.
# Reuters and AP Business were removed — both fail with SSL EOF on this host.
_MARKET_RSS_FEEDS: Tuple[Tuple[str, str], ...] = (
    ("https://feeds.bloomberg.com/markets/news.rss", "Bloomberg"),
    ("https://finance.yahoo.com/news/rssindex", "Yahoo Finance"),
    ("https://www.cnbc.com/id/10001147/device/rss/rss.html", "CNBC Markets"),
    ("https://www.ft.com/markets?format=rss", "FT Markets"),
    ("https://feeds.marketwatch.com/marketwatch/topstories/", "MarketWatch"),
    # Sources with deeper date history (10–20 days) — key for multi-node S_t
    ("https://feeds.bbci.co.uk/news/business/rss.xml", "BBC Business"),
    ("https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "NYT Business"),
    ("https://www.theguardian.com/business/rss", "Guardian Business"),
    ("https://feeds.skynews.com/feeds/rss/business.xml", "Sky News Business"),
)


def _rss_entry_date(ent: Any) -> Optional[date]:
    import time as _time
    t = getattr(ent, "published_parsed", None) or getattr(ent, "updated_parsed", None)
    if t and isinstance(t, _time.struct_time):
        return date(t.tm_year, t.tm_mon, t.tm_mday)
    return None


def _rss_http_timeout_sec() -> float:
    """HTTP timeout per RSS GET; ``LREPORT_FAST_NEWS=1`` defaults to 10s if unset."""
    v = os.environ.get("NEWS_RSS_HTTP_TIMEOUT", "").strip()
    if v:
        try:
            return max(3.0, min(60.0, float(v)))
        except ValueError:
            pass
    if _env_truthy("LREPORT_FAST_NEWS", False):
        return 10.0
    return 22.0


def _rss_parallel_enabled() -> bool:
    return _env_truthy("NEWS_RSS_PARALLEL", True)


def _fetch_one_rss_feed(
    url: str,
    label: str,
    per_cap: int,
    headers: Dict[str, str],
    timeout: float,
) -> List[HeadlineFetch]:
    """Single-feed RSS pull (for parallel batch); no cross-feed dedupe."""
    try:
        import feedparser
        import requests
    except ImportError:
        return []
    out: List[HeadlineFetch] = []
    local_seen: set = set()
    apply_gate = _seed_gate_enabled_for_all_pools()
    try:
        r = requests.get(url, timeout=timeout, headers=headers)
        r.raise_for_status()
        parsed = feedparser.parse(r.content)
        entries = list(getattr(parsed, "entries", []) or [])
        entries.sort(
            key=lambda e: _rss_entry_date(e) or date.min,
            reverse=True,
        )
        n_from_feed = 0
        for ent in entries:
            if n_from_feed >= per_cap:
                break
            title = getattr(ent, "title", None)
            if not title:
                continue
            t = str(title).strip()
            if not t:
                continue
            d = _rss_entry_date(ent)
            if d is None:
                continue
            if apply_gate and not _headline_passes_seed_gate(t):
                continue
            key = t.lower()[:160]
            if key in local_seen:
                continue
            local_seen.add(key)
            out.append(HeadlineFetch(t, d, label))
            n_from_feed += 1
    except Exception as e:
        logger.debug("RSS skip %s: %s", url[:48], e)
    return out


def _fetch_rss_from_feed_list(
    feeds: Sequence[Tuple[str, str]],
    max_items: int,
    *,
    seen: Optional[set] = None,
) -> List[HeadlineFetch]:
    """RSS headlines from explicit feed list; dated entries only; optional cross-call dedupe."""
    if max_items <= 0 or not feeds:
        return []
    try:
        import feedparser  # noqa: F401
        import requests  # noqa: F401
    except ImportError:
        logger.warning("feedparser or requests missing — pip install feedparser requests")
        return []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(compatible; LReport-Sentiment/1.0)"
        ),
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    }
    n_feeds = max(1, len(feeds))
    # Allow each feed to contribute more items so that sources with deep history
    # (BBC Business: 15 unique dates, NYT Business: 5+ unique dates) are not
    # throttled before they can add their older headlines.
    per_cap = max(30, min(200, (max_items * 5 + n_feeds - 1) // n_feeds))
    timeout = _rss_http_timeout_sec()
    local_seen: set = seen if seen is not None else set()

    if _rss_parallel_enabled() and len(feeds) > 1:
        chunks: List[HeadlineFetch] = []
        max_workers = min(8, len(feeds))
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = [
                ex.submit(_fetch_one_rss_feed, url, label, per_cap, headers, timeout)
                for url, label in feeds
            ]
            for fut in futs:
                try:
                    chunks.extend(fut.result())
                except Exception as e:
                    logger.debug("RSS batch item failed: %s", e)
        deduped = _dedupe_prefer_dated(chunks)
        dated_only = [h for h in deduped if h.published is not None]
        sorted_d = _sort_dated_desc(dated_only)
        if seen is not None:
            out2: List[HeadlineFetch] = []
            for h in sorted_d:
                k = h.text.lower()[:160]
                if k in seen:
                    continue
                seen.add(k)
                out2.append(h)
                if len(out2) >= max_items:
                    break
            return out2
        return sorted_d[:max_items]

    out: List[HeadlineFetch] = []
    apply_gate = _seed_gate_enabled_for_all_pools()
    for url, label in feeds:
        if len(out) >= max_items:
            break
        try:
            import feedparser
            import requests

            r = requests.get(url, timeout=timeout, headers=headers)
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
            entries = list(getattr(parsed, "entries", []) or [])
            entries.sort(
                key=lambda e: _rss_entry_date(e) or date.min,
                reverse=True,
            )
            n_from_feed = 0
            for ent in entries:
                if len(out) >= max_items or n_from_feed >= per_cap:
                    break
                title = getattr(ent, "title", None)
                if not title:
                    continue
                t = str(title).strip()
                if not t:
                    continue
                d = _rss_entry_date(ent)
                if d is None:
                    continue
                if apply_gate and not _headline_passes_seed_gate(t):
                    continue
                key = t.lower()[:160]
                if key in local_seen:
                    continue
                local_seen.add(key)
                out.append(HeadlineFetch(t, d, label))
                n_from_feed += 1
        except Exception as e:
            logger.debug("RSS skip %s: %s", url[:48], e)

    return out[:max_items]


def _fetch_rss_headline_items(max_items: int, *, seen: Optional[set] = None) -> List[HeadlineFetch]:
    """Broad English market RSS (Reuters, Bloomberg, …)."""
    return _fetch_rss_from_feed_list(_MARKET_RSS_FEEDS, max_items, seen=seen)


def _fetch_geo_seed_rss_items(max_items: int, *, seen: Optional[set] = None) -> List[HeadlineFetch]:
    """Google News RSS aligned with :mod:`research.crawl4ai_config` geo / supply-chain seeds."""
    if max_items <= 0 or not _env_truthy("NEWS_GEO_RSS_ENABLED", True):
        return []
    try:
        from research.crawl4ai_config import geo_google_news_rss_feeds

        feeds = geo_google_news_rss_feeds()
    except Exception as e:
        logger.debug("geo RSS feeds unavailable: %s", e)
        return []
    return _fetch_rss_from_feed_list(feeds, max_items, seen=seen)


def _fetch_newapi_headline_items(
    max_items: int,
    *,
    seen: Optional[set] = None,
    language: str = "en",
    only_days: Optional[List[date]] = None,
    fetch_mode: str = "standard",
    test_start_cal: Optional[date] = None,
    rng: Optional[random.Random] = None,
) -> Tuple[List[HeadlineFetch], Dict[str, Any], List[Dict[str, Any]]]:
    """NewAPI headlines (dated) for historical coverage.

    Enabled when ``NEWSAPI_KEY`` is set. Intended to improve S_t history coverage
    when Crawl4AI archive scraping is unreliable on this host.

    Returns ``(items, meta, premerge_snapshots)`` where ``premerge_snapshots`` matches
    ``fetch_meta['newapi_articles_before_merge']`` (includes NewsAPI ``publishedAt``).
    """
    meta: Dict[str, Any] = {"enabled": False, "n": 0, "error": None}
    empty_snap: List[Dict[str, Any]] = []
    try:
        cap = int(
            (os.environ.get("NEWSAPI_MERGE_BUDGET") or str(max(200, min(1200, int(max_items) * 20)))).strip()
        )
    except ValueError:
        cap = max(200, int(max_items))
    cap = int(max(30, min(cap, 2000)))
    if cap == 0:
        return [], meta, empty_snap
    if not (os.environ.get("NEWSAPI_KEY") or "").strip():
        return [], meta, empty_snap
    if fetch_mode != "interval_vader" and only_days is not None and len(only_days) == 0:
        meta["enabled"] = True
        meta["n"] = 0
        meta["fetch_mode"] = "rss_gap_sample"
        meta["selected_days"] = []
        return [], meta, empty_snap

    # Default query: reuse geo seed bundles (aligned with Phase0.md) + markets
    try:
        from research.crawl4ai_config import GEO_NEWS_QUERY_BUNDLES

        default_q = " OR ".join(f"({q})" for q in GEO_NEWS_QUERY_BUNDLES)
    except Exception:
        default_q = "Missile OR blockade OR ceasefire OR sanctions OR crude oil OR Hormuz OR Iran OR Taiwan OR semiconductor OR export control OR chip ban"
    q = (os.environ.get("NEWSAPI_QUERY") or default_q).strip()
    if not q:
        q = default_q

    to_d = date.today()
    try:
        lb = int((os.environ.get("NEWSAPI_LOOKBACK_DAYS") or "29").strip())
    except ValueError:
        lb = 29
    lb = int(max(1, min(lb, 364)))
    from_d = to_d - timedelta(days=lb)

    try:
        if fetch_mode == "interval_vader":
            from research.news_newapi import fetch_newapi_headlines_interval_vader

            ts0 = test_start_cal or parse_iso_date(DEFAULT_TEST_START)
            if ts0 is None:
                ts0 = parse_iso_date(DEFAULT_TEST_START) or to_d
            if ts0 > to_d:
                ts0 = to_d
            r = rng if rng is not None else random.Random(0)
            rows, meta2 = fetch_newapi_headlines_interval_vader(
                q=q,
                max_items=int(cap),
                test_start=ts0,
                as_of=to_d,
                language=language,
                rng=r,
            )
        else:
            from research.news_newapi import fetch_newapi_headlines

            rows, meta2 = fetch_newapi_headlines(
                q=q,
                max_items=int(cap),
                date_from=from_d,
                date_to=to_d,
                language=language,
                only_days=only_days,
            )
        meta.update(meta2)
        meta["enabled"] = True
    except Exception as exc:
        meta["enabled"] = True
        meta["error"] = repr(exc)
        return [], meta, empty_snap

    out: List[HeadlineFetch] = []
    published_at_by_title_key: Dict[str, str] = {}
    local_seen: set = seen if seen is not None else set()
    apply_gate = _seed_gate_enabled_for_all_pools()
    rejected_gate = 0
    for row in rows:
        title, pub, src = row[0], row[1], row[2]
        pat_raw = str(row[3]).strip() if len(row) > 3 and row[3] is not None else ""
        t = str(title).strip()
        if not t:
            continue
        d = pub if isinstance(pub, date) else None
        if d is None:
            continue
        if apply_gate and not _headline_passes_seed_gate(t):
            # NewsAPI rate-limit / API-key error strings & unrelated navigation chunks are
            # caught here (regex + seed-lexicon gate). See :func:`_headline_passes_seed_gate`.
            rejected_gate += 1
            continue
        k = t.lower()[:160]
        if k in local_seen:
            continue
        local_seen.add(k)
        if pat_raw:
            published_at_by_title_key[k] = pat_raw
        out.append(HeadlineFetch(t, d, src))
        if len(out) >= cap:
            break
    if rejected_gate:
        meta["rejected_by_seed_gate"] = int(rejected_gate)

    out = _sort_dated_desc(out)
    out = out[:cap]
    meta["n"] = len(out)
    snap = [
        {
            "text": h.text,
            "published": h.published.isoformat() if h.published else "",
            "publishedAt": published_at_by_title_key.get(h.text.lower()[:160], ""),
            "source": h.source,
        }
        for h in out
    ]
    return out, meta, snap


__all__ = [
    "_MARKET_RSS_FEEDS",
    "_rss_entry_date",
    "_rss_http_timeout_sec",
    "_rss_parallel_enabled",
    "_fetch_one_rss_feed",
    "_fetch_rss_from_feed_list",
    "_fetch_rss_headline_items",
    "_fetch_geo_seed_rss_items",
    "_fetch_newapi_headline_items",
]
