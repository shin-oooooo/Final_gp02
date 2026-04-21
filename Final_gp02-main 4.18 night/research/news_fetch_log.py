"""Write news-fetch statistics (incl. full headlines & S_t distribution) to JSON."""

from __future__ import annotations

import json
import logging
import os
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def default_news_fetch_json_path() -> str:
    """Resolve JSON path for news-fetch statistics.

    Priority:
    1. ``LREPORT_NEWS_FETCH_JSON`` — explicit file path.
    2. Same directory as ``AIE1902_DATA_JSON`` (next to ``data.json``).
    3. Parent of package ``research/`` (repo root) + ``news_fetch_log.json``.
    """
    raw = (os.environ.get("LREPORT_NEWS_FETCH_JSON") or "").strip()
    if raw:
        return os.path.normpath(os.path.abspath(raw))
    data_env = (os.environ.get("AIE1902_DATA_JSON") or "").strip()
    if data_env:
        data_dir = os.path.dirname(os.path.abspath(data_env))
        return os.path.normpath(os.path.join(data_dir, "news_fetch_log.json"))
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.normpath(os.path.join(base, "news_fetch_log.json"))


def default_news_premerge_json_path() -> str:
    """Path for full pre-merge headline dump (sibling of ``news_fetch_log.json``)."""
    raw = (os.environ.get("LREPORT_NEWS_PREMERGE_JSON") or "").strip()
    if raw:
        return os.path.normpath(os.path.abspath(raw))
    main = default_news_fetch_json_path()
    parent, base = os.path.dirname(main), os.path.basename(main)
    if base.endswith(".json"):
        stem = base[:-5] + "_premerge.json"
    else:
        stem = "news_fetch_premerge.json"
    return os.path.normpath(os.path.join(parent or ".", stem))


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, float) and (obj != obj):  # NaN
        return None
    return obj


def _st_by_date(vader_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate per-headline VADER compound into daily mean, oldest-first."""
    by_day: Dict[str, List[float]] = defaultdict(list)
    for r in vader_rows:
        pub = str(r.get("published") or "")[:10]
        if not pub:
            continue
        try:
            by_day[pub].append(float(r.get("compound", 0.0)))
        except (TypeError, ValueError):
            pass
    result = []
    for d in sorted(by_day.keys()):
        vals = by_day[d]
        result.append({
            "date": d,
            "mean_compound": round(sum(vals) / len(vals), 4) if vals else 0.0,
            "n_headlines": len(vals),
        })
    return result


def _counter_dict_sorted(c: Counter) -> Dict[str, int]:
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))


def _daily_counts_from_articles(articles: List[Dict[str, Any]]) -> Dict[str, int]:
    c: Counter[str] = Counter()
    for a in articles:
        p = str(a.get("published") or "")[:10]
        if p:
            c[p] += 1
    return dict(sorted(c.items()))


def write_news_fetch_log(
    merged: List[Any],
    fetch_meta: Dict[str, Any],
    *,
    max_items: int,
    pool_sizes: Dict[str, int],
    sentiment_detail: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist full fetch record including headlines, VADER scores, and S_t distribution.

    Parameters
    ----------
    merged:
        List of ``HeadlineFetch`` namedtuples from the fetch pipeline.
    fetch_meta:
        Dict returned by ``_fetch_combined_headline_items``.
    max_items:
        The cap that was requested.
    pool_sizes:
        Raw pool sizes before merging.
    sentiment_detail:
        Optional full output of ``get_sentiment_detail``; used to write
        per-headline VADER scores and the daily S_t distribution.
    """
    path = default_news_fetch_json_path()
    premerge_path = default_news_premerge_json_path()
    premerge_articles: List[Dict[str, Any]] = list(fetch_meta.get("premerge_articles_all") or [])

    by_source: Counter[str] = Counter()
    for h in merged:
        src = getattr(h, "source", None) or "unknown"
        by_source[str(src)] += 1

    by_source_pre: Counter[str] = Counter()
    by_pool_pre: Counter[str] = Counter()
    for a in premerge_articles:
        by_source_pre[str(a.get("source") or "unknown")] += 1
        by_pool_pre[str(a.get("pool") or "unknown")] += 1

    # Full headline list (text + date + source), sorted oldest-first — **merged only**
    headlines_out = []
    for h in merged:
        headlines_out.append({
            "text": str(getattr(h, "text", "") or ""),
            "published": str(getattr(h, "published", "") or ""),
            "source": str(getattr(h, "source", "") or ""),
        })

    # VADER per-headline scores (from sentiment_detail if available)
    vader_rows: List[Dict[str, Any]] = []
    vader_summary: Dict[str, Any] = {}
    if isinstance(sentiment_detail, dict):
        raw_heads = sentiment_detail.get("headlines") or []
        for r in raw_heads:
            vader_rows.append({
                "published": str(r.get("published") or ""),
                "source": str(r.get("source") or ""),
                "compound": round(float(r.get("compound", 0.0)), 3),
                "pos": round(float(r.get("pos", 0.0)), 3),
                "neg": round(float(r.get("neg", 0.0)), 3),
                "neu": round(float(r.get("neu", 0.0)), 3),
                "text": str(r.get("text") or ""),
            })
        vader_summary = {
            "score": sentiment_detail.get("score"),
            "vader_avg": sentiment_detail.get("vader_avg"),
            "penalty": sentiment_detail.get("penalty"),
            "severity_boost": sentiment_detail.get("severity_boost"),
            "neg_hits": sentiment_detail.get("neg_hits"),
            "pos_hits": sentiment_detail.get("pos_hits"),
        }

    # S_t daily distribution (oldest-first, matches test-window ordering)
    st_dist = _st_by_date(vader_rows) if vader_rows else []

    by_day_merged = _daily_counts_from_articles(headlines_out)

    # Merged log: strip bulky pre-merge blobs from fetch_meta on disk
    meta_merged_only = {
        k: v
        for k, v in dict(fetch_meta).items()
        if k not in ("premerge_articles_all", "newapi_articles_before_merge")
    }

    record: Dict[str, Any] = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "output_path": path,
        "premerge_output_path": premerge_path,
        "max_items_requested": int(max_items),
        "merged_total": len(merged),
        "by_source": dict(sorted(by_source.items(), key=lambda kv: (-kv[1], kv[0]))),
        "counts_by_published_day_merged": by_day_merged,
        "pool_sizes": dict(sorted(pool_sizes.items(), key=lambda kv: (-kv[1], kv[0]))),
        "fetch_meta": _json_safe(meta_merged_only),
        # Merged headlines only (post-merge, post per-day cap in sentiment pipeline)
        "headlines": headlines_out,
        "vader_score": _json_safe(vader_summary) if vader_summary else None,
        "vader_headlines": vader_rows,
        "st_by_date": st_dist,
    }

    premerge_record: Dict[str, Any] = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "output_path": premerge_path,
        "merged_log_path": path,
        "max_items_requested": int(max_items),
        "premerge_total": len(premerge_articles),
        "pool_sizes": dict(sorted(pool_sizes.items(), key=lambda kv: (-kv[1], kv[0]))),
        "counts_by_pool": _counter_dict_sorted(by_pool_pre),
        "counts_by_source": _counter_dict_sorted(by_source_pre),
        "counts_by_published_day": _daily_counts_from_articles(premerge_articles),
        "articles": _json_safe(premerge_articles),
    }

    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        logger.info(
            "[news_fetch_log] wrote %s (merged=%d sources=%d st_dates=%d)",
            path, len(merged), len(by_source), len(st_dist),
        )
    except OSError as exc:
        logger.warning(
            "Could not write news fetch log to %s: %s "
            "(set LREPORT_NEWS_FETCH_JSON to a writable path, or check AIE1902_DATA_JSON directory).",
            path,
            exc,
        )
        return

    try:
        p2 = os.path.dirname(premerge_path)
        if p2:
            os.makedirs(p2, exist_ok=True)
        with open(premerge_path, "w", encoding="utf-8") as f:
            json.dump(premerge_record, f, ensure_ascii=False, indent=2)
        logger.info(
            "[news_fetch_log] wrote pre-merge %s (n=%d)",
            premerge_path, len(premerge_articles),
        )
    except OSError as exc:
        logger.warning(
            "Could not write pre-merge news log to %s: %s "
            "(set LREPORT_NEWS_PREMERGE_JSON to a writable path).",
            premerge_path,
            exc,
        )
