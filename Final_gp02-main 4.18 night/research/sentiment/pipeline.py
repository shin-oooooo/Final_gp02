"""Headline-fetch orchestrator: combine all source pools into one prioritized list.

Extracted from ``research/sentiment_proxy.py`` (2026-04-21). This is the top of
the fetch DAG — every dependency resolves downward into ``sources_http`` /
``sources_crawl`` / ``curation`` / ``core``. Nothing in the subsystem depends
back on this module.

Public entry point (re-exported from ``sentiment_proxy``):
    ``_fetch_combined_headline_items`` — the single call used by
    ``get_sentiment_detail`` to assemble a merged, deduped, capped pool.
"""

from __future__ import annotations

import logging
import os
import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from research.sentiment.core import (
    DEFAULT_MAX_HEADLINES,
    HeadlineFetch,
    _env_truthy,
)
from research.sentiment.curation import (
    _count_headlines_by_day_in_range,
    _crawl4ai_gap_fill_plan,
    _crawl4ai_gap_fill_window,
    _finalize_headline_cap,
    _merge_headline_lists,
    _select_newapi_gap_days,
)
from research.sentiment.sources_cache import load_cached_headlines
from research.sentiment.sources_crawl import (
    _fetch_akshare_cn_headline_items,
    _fetch_akshare_english_headline_items,
    _fetch_crawl4ai_headline_items,
)
from research.sentiment.sources_http import (
    _fetch_geo_seed_rss_items,
    _fetch_newapi_headline_items,
    _fetch_rss_headline_items,
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

def _fetch_newapi_pool(
    *,
    base_meta: Dict[str, Any],
    rss_seen: set,
    rss_items: List[HeadlineFetch],
    geo_rss: List[HeadlineFetch],
    max_items: int,
) -> Tuple[List[HeadlineFetch], List[Dict[str, Any]]]:
    """Resolve fetch strategy + call ``_fetch_newapi_headline_items``.

    Returns ``(newapi_items, newapi_premerge)``. Mutates ``base_meta`` with
    keys: ``newapi_n``, ``newapi_meta``, ``newapi_articles_before_merge``,
    ``newapi_fetch_strategy``, ``newapi_gap_sample_days`` (gap-sample mode),
    ``newapi_interval_test_start`` (interval-vader mode). On any exception the
    pool falls back to empty + records ``error`` in ``newapi_meta``.
    """
    newapi_items: List[HeadlineFetch] = []
    newapi_meta: Dict[str, Any] = {}
    newapi_premerge: List[Dict[str, Any]] = []
    if not (base_meta["newapi_enabled"] and _env_truthy("NEWS_NEWAPI_ENABLED", True)):
        base_meta["newapi_n"] = 0
        base_meta["newapi_articles_before_merge"] = []
        return newapi_items, newapi_premerge
    try:
        try:
            lb_n = int((os.environ.get("NEWSAPI_LOOKBACK_DAYS") or "29").strip())
        except ValueError:
            lb_n = 29
        lb_n = int(max(1, min(lb_n, 364)))
        to_n = date.today()
        from_n = to_n - timedelta(days=lb_n)
        strat = (os.environ.get("NEWSAPI_FETCH_STRATEGY") or "rss_gap_sample").strip().lower()
        only_days_arg: Optional[List[date]] = None
        interval_rng: Optional[random.Random] = None
        interval_test_start: Optional[date] = None
        if strat in ("full", "full_range", "all_days"):
            only_days_arg = None
            base_meta["newapi_fetch_strategy"] = "full_range"
        elif strat in ("interval_vader", "vader_interval", "test_interval_vader"):
            seed_iv = (os.environ.get("NEWSAPI_RANDOM_SEED") or "").strip() or to_n.isoformat()
            interval_rng = random.Random(sum(ord(c) for c in seed_iv) % (2**31))
            interval_test_start = parse_iso_date(
                (os.environ.get("LREPORT_SENTIMENT_TEST_START") or "").strip() or DEFAULT_TEST_START
            )
            base_meta["newapi_fetch_strategy"] = "interval_vader"
            base_meta["newapi_interval_test_start"] = (
                interval_test_start.isoformat() if interval_test_start else None
            )
        else:
            try:
                gap_min = int((os.environ.get("NEWSAPI_GAP_MIN_RSS_COUNT") or "1").strip())
            except ValueError:
                gap_min = 1
            gap_min = int(max(0, gap_min))
            try:
                gap_sample_k = int((os.environ.get("NEWSAPI_GAP_SAMPLE_MAX_DAYS") or "10").strip())
            except ValueError:
                gap_sample_k = 10
            seed_s = (os.environ.get("NEWSAPI_RANDOM_SEED") or "").strip() or to_n.isoformat()
            rng = random.Random(sum(ord(c) for c in seed_s) % (2**31))
            day_counts = _count_headlines_by_day_in_range(
                list(geo_rss) + list(rss_items), from_n, to_n
            )
            only_days_arg = _select_newapi_gap_days(
                from_n, to_n, day_counts,
                min_count=gap_min, max_days=gap_sample_k, rng=rng,
            )
            base_meta["newapi_fetch_strategy"] = "rss_gap_sample"
            base_meta["newapi_gap_sample_days"] = [d.isoformat() for d in only_days_arg]
            base_meta["newapi_gap_min_rss_count"] = gap_min
        budget = max(200, min(1200, max(30, max_items * 25)))
        if strat in ("interval_vader", "vader_interval", "test_interval_vader"):
            newapi_items, newapi_meta, newapi_premerge = _fetch_newapi_headline_items(
                budget,
                seen=rss_seen,
                language=str(os.environ.get("NEWSAPI_LANGUAGE") or "en").strip() or "en",
                fetch_mode="interval_vader",
                test_start_cal=interval_test_start,
                rng=interval_rng,
            )
        else:
            newapi_items, newapi_meta, newapi_premerge = _fetch_newapi_headline_items(
                budget,
                seen=rss_seen,
                language=str(os.environ.get("NEWSAPI_LANGUAGE") or "en").strip() or "en",
                only_days=only_days_arg,
            )
    except Exception as exc:
        newapi_items, newapi_meta, newapi_premerge = [], {"enabled": True, "error": repr(exc)}, []
    base_meta["newapi_n"] = len(newapi_items)
    if newapi_meta:
        base_meta["newapi_meta"] = newapi_meta
    base_meta["newapi_articles_before_merge"] = list(newapi_premerge or [])
    return newapi_items, newapi_premerge


def _resolve_crawl4ai_quotas(
    *,
    base_meta: Dict[str, Any],
    max_items: int,
) -> Tuple[bool, int, int]:
    """Resolve ``(crawl_enabled, crawl_quota, primary_quota)`` from env + record on meta.

    Reads ``CRAWL4AI_ENABLED`` and ``CRAWL4AI_QUOTA_RATIO`` (clamped [0, 0.80]).
    Mutates ``base_meta`` with ``crawl4ai_enabled``, ``crawl4ai_quota``, ``primary_quota``.
    """
    crawl_enabled = os.environ.get("CRAWL4AI_ENABLED", "1").strip().lower() not in ("0", "false", "no")
    try:
        q_ratio = float(os.environ.get("CRAWL4AI_QUOTA_RATIO", "0.30"))
    except ValueError:
        q_ratio = 0.30
    q_ratio = float(max(0.0, min(0.80, q_ratio)))
    crawl_quota = int(max(0, min(max_items, round(max_items * q_ratio))))
    primary_quota = int(max(0, max_items - crawl_quota))
    base_meta["crawl4ai_enabled"] = bool(crawl_enabled)
    base_meta["crawl4ai_quota"] = int(crawl_quota)
    base_meta["primary_quota"] = int(primary_quota)
    return crawl_enabled, crawl_quota, primary_quota


def _fetch_crawl4ai_pool_with_dedupe(
    *,
    base_meta: Dict[str, Any],
    merged_primary: List[HeadlineFetch],
    crawl_enabled: bool,
    crawl_quota: int,
) -> Tuple[List[HeadlineFetch], List[HeadlineFetch], int]:
    """Run the gap-fill plan, fetch Crawl4AI pool, dedupe vs ``merged_primary``.

    Returns ``(crawl_used, crawl_pool, raw_n_extra)``. ``raw_n_extra`` is the
    number of *raw* items pulled from Crawl4AI (added to caller's ``raw_n``).
    Mutates ``base_meta`` with: ``crawl4ai_gap_*``, ``crawl4ai_budget``, ``crawl4ai_n``.
    """
    gap_tr, gap_stamp_dates, gap_sparse, _, gap_band_total = _crawl4ai_gap_fill_plan(merged_primary)
    gw = _crawl4ai_gap_fill_window()
    base_meta["crawl4ai_gap_fill_triggered"] = bool(gap_tr)
    base_meta["crawl4ai_gap_band_primary_total"] = int(gap_band_total)
    base_meta["crawl4ai_gap_sparse_day_count"] = len(gap_sparse)
    if gw:
        base_meta["crawl4ai_gap_fill_window"] = [gw[0].isoformat(), gw[1].isoformat()]
    if gap_sparse:
        base_meta["crawl4ai_gap_sparse_days"] = [d.isoformat() for d in gap_sparse[:40]]
        if len(gap_sparse) > 40:
            base_meta["crawl4ai_gap_sparse_days_truncated"] = True

    crawl_used: List[HeadlineFetch] = []
    crawl_pool: List[HeadlineFetch] = []
    if crawl_enabled and crawl_quota > 0:
        crawl_budget = max(
            crawl_quota,
            min(
                int(os.environ.get("CRAWL4AI_MAX_ITEMS", str(max(16, crawl_quota * 3)))),
                160,
            ),
        )
        if gap_tr:
            try:
                extra_b = int((os.environ.get("CRAWL4AI_GAP_FILL_EXTRA_BUDGET") or "32").strip())
            except ValueError:
                extra_b = 32
            extra_b = int(max(0, min(extra_b, 80)))
            crawl_budget = min(160, crawl_budget + extra_b)
            base_meta["crawl4ai_gap_fill_extra_budget"] = int(extra_b)
        base_meta["crawl4ai_budget"] = int(crawl_budget)
        crawl_pool = _fetch_crawl4ai_headline_items(
            crawl_budget,
            undated_stamp_dates=(gap_stamp_dates if gap_tr and gap_stamp_dates else None),
        )
        pri_keys = {h.text.lower()[:120] for h in merged_primary}
        for h in crawl_pool:
            k = h.text.lower()[:120]
            if k in pri_keys:
                continue
            pri_keys.add(k)
            crawl_used.append(h)
            if len(crawl_used) >= crawl_quota:
                break
        if not crawl_used:
            try:
                from research.integrations import load_external_integrations

                cfg = load_external_integrations()
                if cfg.news_finance_urls or cfg.news_history_finance_urls:
                    logger.warning(
                        "[sentiment] Crawl4AI returned no usable dated headlines "
                        "(strict headline filter / install: python -m playwright install chromium)."
                    )
            except Exception:
                pass
    base_meta["crawl4ai_n"] = len(crawl_used)
    return crawl_used, crawl_pool, len(crawl_pool)


def _build_premerge_snapshot_rows(
    *,
    geo_rss: List[HeadlineFetch],
    rss_items: List[HeadlineFetch],
    newapi_items: List[HeadlineFetch],
    newapi_premerge: List[Dict[str, Any]],
    ak_en: List[HeadlineFetch],
    ak_cn: List[HeadlineFetch],
    crawl_pool: List[HeadlineFetch],
) -> List[Dict[str, Any]]:
    """Flatten all per-pool ``HeadlineFetch`` lists into the pre-merge snapshot.

    NewsAPI uses the richer ``newapi_premerge`` rows when present (preserves
    the source-API metadata), otherwise falls back to the merged-row shape.
    """
    rows: List[Dict[str, Any]] = []

    def _append(hs: List[HeadlineFetch], pool: str) -> None:
        for h in hs:
            rows.append(
                {
                    "pool": pool,
                    "text": h.text,
                    "published": h.published.isoformat() if h.published else "",
                    "source": h.source,
                }
            )

    _append(geo_rss, "geo_rss")
    _append(rss_items, "rss_primary")
    if newapi_premerge:
        for row in newapi_premerge:
            m = dict(row)
            m["pool"] = "newapi"
            rows.append(m)
    else:
        _append(newapi_items, "newapi")
    _append(ak_en, "akshare_en")
    _append(ak_cn, "akshare_cn")
    _append(crawl_pool, "crawl4ai_pool")
    return rows


def _finalize_combined_headline_meta(
    *,
    base_meta: Dict[str, Any],
    merged: List[HeadlineFetch],
    dropped: int,
    raw_n: int,
) -> None:
    """Compute horizon/span/gap from the merged headlines and update ``base_meta``."""
    all_dates = [h.published for h in merged if h.published is not None]
    as_of_d = date.today()
    if all_dates:
        horizon_raw = calendar_span_earliest_to_asof(min(all_dates), as_of_d)
    else:
        horizon_raw = 1
    span = effective_test_span_days(horizon_raw)
    gap = median_consecutive_gap_days(all_dates) if len(all_dates) >= 2 else 1.0
    base_meta.update(
        {
            "news_horizon_days": horizon_raw,
            "effective_test_span_days": span,
            "recommended_test_end": today_iso(),
            "news_gap_days": float(gap),
            "rss_dated_entries": len(all_dates),
            "dropped_undated_count": dropped,
            "raw_headline_candidates": raw_n,
        }
    )


def _fetch_combined_headline_items(
    max_items: int = DEFAULT_MAX_HEADLINES,
) -> Tuple[List[HeadlineFetch], Dict[str, Any], Dict[str, int]]:
    """
    **Priority**: English market RSS, then Google News geo seeds, then AKShare (EN/CN per flags)
    fill ``max_items`` first — each pool collected **newest-first**; merged globally **newest-first**.
    Crawl4AI (**title-shaped English only**) tops up any remainder, also **newest-first**.

    ``AKSHARE_NEWS_ENABLED=0`` disables all AKShare. Sub-switches:
    ``AKSHARE_EN_NEWS_ENABLED`` (default on), ``AKSHARE_CN_NEWS_ENABLED`` (default off).
    """
    base_meta: Dict[str, Any] = {
        "news_horizon_days": 1,
        "effective_test_span_days": effective_test_span_days(1),
        "news_gap_days": 1.0,
        "recommended_test_end": test_end_for_start(DEFAULT_TEST_START, effective_test_span_days(1)),
        "crawl4ai_n": 0,
        "rss_dated_entries": 0,
        "dropped_undated_count": 0,
        "raw_headline_candidates": 0,
        "akshare_enabled": _env_truthy("AKSHARE_NEWS_ENABLED", True),
        "akshare_en_enabled": False,
        "akshare_cn_enabled": False,
        "geo_rss_n": 0,
        "newapi_enabled": bool((os.environ.get("NEWSAPI_KEY") or "").strip()),
        "newapi_n": 0,
        "newapi_articles_before_merge": [],
        "news_uniform_daily_merge": _env_truthy("NEWS_UNIFORM_DAILY_MERGE", True),
    }
    if max_items <= 0:
        try:
            from research.news_fetch_log import write_news_fetch_log

            write_news_fetch_log([], base_meta, max_items=0, pool_sizes={})
        except Exception as exc:
            logger.warning("news fetch log not written: %s", exc, exc_info=True)
        return [], base_meta, {}

    # ── Cache-first path (HF Space / CRAWL4AI_ENABLED=0 deployments) ─────────
    # When running on HuggingFace Spaces or any environment where live news
    # fetch is unreliable (IP-blocked news hosts, Playwright/Chromium not
    # installable), replay the committed ``news_fetch_log.json`` instead.
    # See ``research.sentiment.sources_cache`` for activation rules.
    cached = load_cached_headlines(max_items=max_items)
    if cached is not None:
        cached_items, cached_meta, cached_pool_sizes = cached
        base_meta.update(cached_meta)
        logger.info(
            "[sentiment] fetch replayed from cache: headlines=%d (source=%s)",
            len(cached_items),
            base_meta.get("source"),
        )
        return cached_items, base_meta, cached_pool_sizes

    ak_master = _env_truthy("AKSHARE_NEWS_ENABLED", True)
    use_ak_en = ak_master and _env_truthy("AKSHARE_EN_NEWS_ENABLED", True)
    use_ak_cn = ak_master and _env_truthy("AKSHARE_CN_NEWS_ENABLED", False)
    base_meta["akshare_en_enabled"] = use_ak_en
    base_meta["akshare_cn_enabled"] = use_ak_cn

    _fast = _env_truthy("LREPORT_FAST_NEWS", False)
    # Larger budget so date-rich feeds (BBC, NYT) can contribute all their items
    rss_budget = max(max_items * (4 if _fast else 8), 300 if _fast else 600)
    rss_seen: set = set()
    _geo_default = str(max(12, max_items // 4) if _fast else max(20, max_items // 3))
    geo_cap = max(
        0,
        min(int(os.environ.get("NEWS_GEO_RSS_CAP", _geo_default)), 120),
    )
    rss_items = _fetch_rss_headline_items(rss_budget, seen=rss_seen)
    geo_rss = _fetch_geo_seed_rss_items(geo_cap, seen=rss_seen)
    base_meta["geo_rss_n"] = len(geo_rss)

    newapi_items, newapi_premerge = _fetch_newapi_pool(
        base_meta=base_meta, rss_seen=rss_seen,
        rss_items=rss_items, geo_rss=geo_rss, max_items=max_items,
    )
    ak_en: List[HeadlineFetch] = []
    ak_cn: List[HeadlineFetch] = []
    if use_ak_en:
        ak_en = _fetch_akshare_english_headline_items(
            max(6, max_items // 3) if _fast else max(8, max_items // 2)
        )
    if use_ak_cn:
        ak_cn = _fetch_akshare_cn_headline_items(max(8, max_items // 3))

    # Geo → RSS → NewAPI: seed/geo and wire RSS win dedupe; NewsAPI fills RSS-sparse days only.
    pools: List[List[HeadlineFetch]] = []
    pools.extend([geo_rss, rss_items])
    if newapi_items:
        pools.append(newapi_items)
    if ak_en:
        pools.append(ak_en)
    if ak_cn:
        pools.append(ak_cn)

    # ── Crawl4AI integration strategy ─────────────────────────────────────────
    # 1) Always reserve a quota for Crawl4AI so history URLs can contribute
    #    dated headlines across the full 30–50 day test window.
    # 2) Always merge Crawl4AI results (not only as a top-up when primary pools are short).
    crawl_enabled, crawl_quota, primary_quota = _resolve_crawl4ai_quotas(
        base_meta=base_meta, max_items=max_items,
    )
    merged_primary, dropped, raw_n = _merge_headline_lists(pools, max_items=primary_quota)
    crawl_used, crawl_pool, crawl_raw_extra = _fetch_crawl4ai_pool_with_dedupe(
        base_meta=base_meta, merged_primary=merged_primary,
        crawl_enabled=crawl_enabled, crawl_quota=crawl_quota,
    )
    raw_n += crawl_raw_extra

    base_meta["premerge_articles_all"] = _build_premerge_snapshot_rows(
        geo_rss=geo_rss, rss_items=rss_items,
        newapi_items=newapi_items, newapi_premerge=newapi_premerge,
        ak_en=ak_en, ak_cn=ak_cn, crawl_pool=crawl_pool,
    )

    merged = _finalize_headline_cap(merged_primary + crawl_used, max_items)
    _finalize_combined_headline_meta(base_meta=base_meta, merged=merged, dropped=dropped, raw_n=raw_n)
    logger.info(
        "[sentiment] fetch dated_headlines=%d dropped_undated=%d raw_candidates=%d crawl4ai=%d",
        len(merged),
        dropped,
        raw_n,
        base_meta["crawl4ai_n"],
    )
    pool_sizes: Dict[str, int] = {
        "newapi": len(newapi_items),
        "rss_primary": len(rss_items),
        "geo_rss": len(geo_rss),
        "akshare_en": len(ak_en),
        "akshare_cn": len(ak_cn),
        "crawl4ai_merged": int(base_meta.get("crawl4ai_n") or 0),
    }
    return merged, base_meta, pool_sizes


__all__ = [
    "_fetch_newapi_pool",
    "_resolve_crawl4ai_quotas",
    "_fetch_crawl4ai_pool_with_dedupe",
    "_build_premerge_snapshot_rows",
    "_finalize_combined_headline_meta",
    "_fetch_combined_headline_items",
]
