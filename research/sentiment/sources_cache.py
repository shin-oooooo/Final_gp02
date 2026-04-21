"""Cache-first headline loader (read committed ``news_fetch_log*.json``).

Added 2026-04-21 so HuggingFace Space deployments can run the sentiment
pipeline **without** live network fetches (RSS / NewsAPI / AKShare /
Crawl4AI). HF Spaces block many news hosts at the IP-range level and
Chromium-based Crawl4AI is difficult to install into the minimal Docker
image, so we ship the committed JSON snapshots and replay them.

Primary cache source (merged, after per-day cap):
    ``<repo>/news_fetch_log.json`` — ``headlines[*] = {text, published, source}``

Optional fallback (pre-merge pool snapshot, more rows):
    ``<repo>/news_fetch_log_premerge.json`` — ``articles[*] = {pool, text, published, source}``

Activation precedence (evaluated in order):
    1. ``LREPORT_NEWS_USE_CACHE=0`` → force-disable (always fetch live).
    2. ``LREPORT_NEWS_USE_CACHE=1`` → force-enable (fail-closed if cache missing).
    3. ``SPACE_ID`` env present (HF Spaces auto-sets this) AND cache file
       exists → auto-enable.
    4. Otherwise → disabled, live fetch proceeds.

Return shape matches ``_fetch_combined_headline_items`` exactly::

    (List[HeadlineFetch], Dict[str, Any], Dict[str, int])

so the caller can branch unconditionally on success.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from research.sentiment.core import HeadlineFetch, _coerce_date

logger = logging.getLogger(__name__)


def _cache_mode_enabled() -> Optional[bool]:
    """Resolve tri-state cache toggle.

    Returns
    -------
    True  — explicit enable (``LREPORT_NEWS_USE_CACHE=1``) OR auto-enable
            (running on HF Space and cache file exists).
    False — explicit disable (``LREPORT_NEWS_USE_CACHE=0``).
    None  — no explicit setting and auto-detect is inconclusive; caller
            should fall through to live fetch.
    """
    raw = (os.environ.get("LREPORT_NEWS_USE_CACHE") or "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    if (os.environ.get("SPACE_ID") or "").strip():
        return True
    return None


def _resolve_cache_path() -> str:
    """Same precedence as ``research.news_fetch_log.default_news_fetch_json_path``."""
    raw = (os.environ.get("LREPORT_NEWS_FETCH_JSON") or "").strip()
    if raw:
        return os.path.normpath(os.path.abspath(raw))
    data_env = (os.environ.get("AIE1902_DATA_JSON") or "").strip()
    if data_env:
        data_dir = os.path.dirname(os.path.abspath(data_env))
        return os.path.normpath(os.path.join(data_dir, "news_fetch_log.json"))
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    base = os.path.dirname(base)
    return os.path.normpath(os.path.join(base, "news_fetch_log.json"))


def _resolve_premerge_path(main_path: str) -> str:
    raw = (os.environ.get("LREPORT_NEWS_PREMERGE_JSON") or "").strip()
    if raw:
        return os.path.normpath(os.path.abspath(raw))
    parent, base = os.path.dirname(main_path), os.path.basename(main_path)
    stem = base[:-5] + "_premerge.json" if base.endswith(".json") else "news_fetch_premerge.json"
    return os.path.normpath(os.path.join(parent or ".", stem))


def _row_to_headline(row: Dict[str, Any]) -> Optional[HeadlineFetch]:
    text = str(row.get("text") or "").strip()
    if not text:
        return None
    pub = _coerce_date(row.get("published"))
    src = str(row.get("source") or "cache")
    return HeadlineFetch(text, pub, src)


def load_cached_headlines(
    *,
    max_items: int,
) -> Optional[Tuple[List[HeadlineFetch], Dict[str, Any], Dict[str, int]]]:
    """Attempt to replay a previously-committed ``news_fetch_log.json``.

    Returns ``None`` when the cache path is missing, unreadable, or empty —
    caller should fall through to the live-fetch path. Returns a tuple of
    ``(items, fetch_meta, pool_sizes)`` shaped identically to the live
    orchestrator's output when the cache is usable.

    ``max_items`` caps the returned list (oldest-first preserved as written).
    """
    mode = _cache_mode_enabled()
    # None = auto-detect was inconclusive (no env toggle, not on HF) → caller
    # should run the live fetch path, same as an explicit disable.
    if mode is not True:
        return None

    cache_path = _resolve_cache_path()
    if not os.path.isfile(cache_path):
        if mode is True:
            logger.warning(
                "[sentiment-cache] LREPORT_NEWS_USE_CACHE requested but cache not found at %s "
                "— falling back to live fetch (may be empty on HF).",
                cache_path,
            )
        return None

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            record = json.load(f)
    except (OSError, ValueError) as exc:
        logger.warning("[sentiment-cache] cannot read %s: %s", cache_path, exc)
        return None

    headlines_raw = list(record.get("headlines") or [])
    if not headlines_raw and mode is not True:
        return None

    items: List[HeadlineFetch] = []
    for row in headlines_raw:
        if not isinstance(row, dict):
            continue
        h = _row_to_headline(row)
        if h is None:
            continue
        items.append(h)
        if max_items and len(items) >= max_items:
            break

    if not items:
        premerge_path = _resolve_premerge_path(cache_path)
        if os.path.isfile(premerge_path):
            try:
                with open(premerge_path, "r", encoding="utf-8") as f:
                    prem = json.load(f)
                for row in list(prem.get("articles") or []):
                    if not isinstance(row, dict):
                        continue
                    h = _row_to_headline(row)
                    if h is None:
                        continue
                    items.append(h)
                    if max_items and len(items) >= max_items:
                        break
            except (OSError, ValueError) as exc:
                logger.debug("[sentiment-cache] premerge read failed: %s", exc)

    if not items:
        return None

    meta_src: Dict[str, Any] = dict(record.get("fetch_meta") or {})
    meta_src["source"] = "news_fetch_log_cache"
    meta_src["cache_path"] = cache_path
    meta_src["cache_updated_at"] = record.get("updated_at")
    meta_src["cache_merged_total_original"] = int(record.get("merged_total") or 0)
    meta_src["cache_items_returned"] = len(items)
    meta_src["premerge_articles_all"] = []
    meta_src["newapi_articles_before_merge"] = []
    meta_src.setdefault("news_uniform_daily_merge", True)
    meta_src.setdefault("newapi_enabled", False)
    meta_src.setdefault("akshare_enabled", False)
    meta_src.setdefault("akshare_en_enabled", False)
    meta_src.setdefault("akshare_cn_enabled", False)
    meta_src.setdefault("crawl4ai_enabled", False)
    dates = [h.published for h in items if isinstance(h.published, date)]
    if dates:
        meta_src.setdefault(
            "news_horizon_days",
            max(1, (max(dates) - min(dates)).days + 1),
        )
    meta_src["rss_dated_entries"] = len(dates)
    meta_src["raw_headline_candidates"] = len(items)
    meta_src["dropped_undated_count"] = sum(
        1 for h in items if not isinstance(h.published, date)
    )

    pool_sizes = dict(record.get("pool_sizes") or {})
    if not pool_sizes:
        from collections import Counter

        c: Counter[str] = Counter()
        for h in items:
            c[str(h.source or "cache")] += 1
        pool_sizes = dict(c)

    logger.info(
        "[sentiment-cache] replaying %d headlines from %s (updated_at=%s)",
        len(items),
        cache_path,
        record.get("updated_at"),
    )
    return items, meta_src, pool_sizes


def cache_mode_should_skip_writeback() -> bool:
    """Whether the caller should refrain from overwriting the cache file.

    When the pipeline replayed from cache we must not rewrite
    ``news_fetch_log.json`` — doing so would flatten the seeded pre-merge
    pool down to whatever the replay surfaced.
    """
    return _cache_mode_enabled() is True or bool((os.environ.get("SPACE_ID") or "").strip())


__all__ = [
    "load_cached_headlines",
    "cache_mode_should_skip_writeback",
]
