"""Sentiment-subsystem core: shared types, date utilities, VADER analyzer.

Extracted from ``research/sentiment_proxy.py`` (2026-04-21). Holds the
foundational pieces depended on by every other submodule in
``research.sentiment`` — no imports from sibling submodules, so the DAG
stays acyclic (``core → curation → sources_* → pipeline``).

Contents:
    - Module constants: ``DEFAULT_MAX_HEADLINES``, ``MAX_HEADLINES_CAP``.
    - ``_env_truthy`` — env-flag parser shared by all fetchers.
    - ``HeadlineFetch`` — canonical ``NamedTuple`` every fetcher returns.
    - Date coercion / sorting / dedupe helpers.
    - ``_akshare_rows_to_items`` — shared DataFrame → ``HeadlineFetch`` bridge.
    - ``_make_vader_analyzer`` / ``_vader_score`` — VADER wrappers with the
      Iran-US lexicon already injected.
    - Date-text parsers for Crawl4AI markdown ingestion.
    - ``_crawl_result_markdown`` — string extraction from crawl4ai results.
"""

from __future__ import annotations

import html
import logging
import os
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

from research.sentiment.lexicons import _IRAN_US_LEXICON, _MONTH_PREFIX
from research.sentiment_calendar import parse_iso_date

logger = logging.getLogger(__name__)


# 情绪管线合并后参与 VADER 的标题条数上限（Dash / API 默认不传 max_headlines 时使用）。
DEFAULT_MAX_HEADLINES = 120
MAX_HEADLINES_CAP = 400

def _env_truthy(key: str, default: bool = False) -> bool:
    v = os.environ.get(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


class HeadlineFetch(NamedTuple):
    text: str
    published: Optional[date]
    source: str


def _coerce_date(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        import pandas as pd

        if pd.isna(val):
            return None
    except Exception:
        pass
    s = str(val).strip()
    if not s:
        return None
    d = parse_iso_date(s[:10])
    if d:
        return d
    try:
        import pandas as pd

        ts = pd.to_datetime(s, errors="coerce")
        if ts is pd.NaT:
            return None
        return ts.date()
    except Exception:
        return None


def _pick_date_column(df: Any) -> Optional[str]:
    for c in (
        "发布时间",
        "新闻时间",
        "新闻日期",
        "pub_time",
        "public_time",
        "ctime",
        "datetime",
        "时间",
        "日期",
        "date",
    ):
        if c in getattr(df, "columns", []):
            return c
    return None


def _dedupe_prefer_dated(items: List[HeadlineFetch]) -> List[HeadlineFetch]:
    out_map: Dict[str, HeadlineFetch] = {}
    for it in items:
        k = it.text.lower()[:120]
        if k not in out_map:
            out_map[k] = it
            continue
        old = out_map[k]
        if old.published is None and it.published is not None:
            out_map[k] = it
            continue
        if old.published is not None and it.published is not None and it.published > old.published:
            out_map[k] = it
    return list(out_map.values())


def _sort_dated_asc(items: List[HeadlineFetch]) -> List[HeadlineFetch]:
    return sorted(items, key=lambda x: (x.published or date.min, x.source, x.text[:60]))


def _sort_dated_desc(items: List[HeadlineFetch]) -> List[HeadlineFetch]:
    """Newest calendar date first (late → early); undated last."""
    return sorted(
        items,
        key=lambda x: (x.published or date.min, x.source, x.text[:60]),
        reverse=True,
    )


def _akshare_rows_to_items(
    df: Any,
    text_col: str,
    source: str,
    max_n: int,
    fallback_date: Optional[date] = None,
) -> List[HeadlineFetch]:
    if df is None or df.empty or not text_col:
        return []
    dc = _pick_date_column(df)
    out: List[HeadlineFetch] = []
    for _, row in df.iterrows():
        if len(out) >= max_n:
            break
        try:
            raw_t = row[text_col]
        except Exception:
            continue
        t = str(raw_t).strip() if raw_t is not None else ""
        if not t:
            continue
        pub: Optional[date] = None
        if dc:
            try:
                pub = _coerce_date(row[dc])
            except Exception:
                pub = None
        if pub is None:
            pub = fallback_date
        if pub is None:
            continue
        out.append(HeadlineFetch(t, pub, source))
    return out


def _make_vader_analyzer():
    """Create SentimentIntensityAnalyzer with Iran-US conflict lexicon injected."""
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    sia = SentimentIntensityAnalyzer()
    sia.lexicon.update(_IRAN_US_LEXICON)
    return sia


def _vader_score(texts: List[str]) -> Tuple[float, List[Dict[str, Any]]]:
    """Score texts with VADER + Iran-US lexicon. Returns (avg_compound, per_text_details)."""
    try:
        sia = _make_vader_analyzer()
        details: List[Dict[str, Any]] = []
        for t in texts:
            if not t.strip():
                continue
            sc = sia.polarity_scores(t)
            details.append({
                "text":     t[:120],
                "compound": round(sc["compound"], 3),
                "pos":      round(sc["pos"], 3),
                "neg":      round(sc["neg"], 3),
                "neu":      round(sc["neu"], 3),
            })
        if not details:
            return 0.0, []
        avg = sum(d["compound"] for d in details) / len(details)
        return float(avg), details
    except ImportError:
        logger.warning("vaderSentiment not installed — run: pip install vaderSentiment")
        return 0.0, []
    except Exception as e:
        logger.warning("VADER scoring failed: %s", e)
        return 0.0, []


def _estimate_news_horizon_days(rss_dates: List[date]) -> int:
    """Calendar span (inclusive) from oldest to newest dated RSS item; floor at 1."""
    if len(rss_dates) < 2:
        return 1
    mn, mx = min(rss_dates), max(rss_dates)
    return max(1, (mx - mn).days + 1)


def _parse_relative_publication_hint(text: str, as_of: date) -> Optional[date]:
    """Infer calendar day from common live-hub phrasing (Bloomberg/CNBC style).

    Examples: ``16 hours ago``, ``yesterday``, ``3 days ago``, ``2 weeks ago``.
    """
    if not text or as_of is None:
        return None
    low = str(text).lower()
    if re.search(r"\b(\d{1,3})\s+hours?\s+ago\b", low):
        return as_of
    if re.search(r"\b(just\s+now|moments?\s+ago)\b", low):
        return as_of
    if "yesterday" in low and not re.search(r"\d{1,2}\s+days?\s+ago", low):
        return as_of - timedelta(days=1)
    m = re.search(r"\b(\d{1,2})\s+days?\s+ago\b", low)
    if m:
        n = max(0, min(int(m.group(1)), 180))
        return as_of - timedelta(days=n)
    m = re.search(r"\b(\d{1,2})\s+weeks?\s+ago\b", low)
    if m:
        w = max(0, min(int(m.group(1)), 26))
        return as_of - timedelta(days=7 * w)
    m = re.search(r"\b(\d{1,2})\s+months?\s+ago\b", low)
    if m:
        mo = max(0, min(int(m.group(1)), 12))
        return as_of - timedelta(days=30 * mo)
    return None


def _parse_loose_date(text: str) -> Optional[date]:
    """Best-effort date from a line or snippet (ISO or English ``Month D, YYYY``)."""
    if not text:
        return None
    s = text.strip()[:320]
    m = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m2 = re.search(
        r"\b([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(20\d{2})\b",
        s,
    )
    if m2:
        mon_raw = m2.group(1).lower()[:3]
        if mon_raw in _MONTH_PREFIX:
            mo = _MONTH_PREFIX.index(mon_raw) + 1
            try:
                return date(int(m2.group(3)), mo, int(m2.group(2)))
            except ValueError:
                return None
    return None


def _crawl_result_markdown(res: Any) -> str:
    """Normalize Crawl4AI result markdown (string or MarkdownGenerationResult)."""
    md = getattr(res, "markdown", None)
    if md is None:
        return ""
    raw = getattr(md, "raw_markdown", None)
    if raw is not None and str(raw).strip():
        return str(raw)
    fit = getattr(md, "fit_markdown", None)
    if fit is not None and str(fit).strip():
        return str(fit)
    return str(md) if md is not None else ""


__all__ = [
    "DEFAULT_MAX_HEADLINES",
    "MAX_HEADLINES_CAP",
    "_env_truthy",
    "HeadlineFetch",
    "_coerce_date",
    "_pick_date_column",
    "_dedupe_prefer_dated",
    "_sort_dated_asc",
    "_sort_dated_desc",
    "_akshare_rows_to_items",
    "_make_vader_analyzer",
    "_vader_score",
    "_estimate_news_horizon_days",
    "_parse_relative_publication_hint",
    "_parse_loose_date",
    "_crawl_result_markdown",
]
