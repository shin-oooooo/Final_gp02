"""Per-ticker sentiment scoring + public ``get_sentiment_*`` API.

Extracted from ``research/sentiment_proxy.py`` (2026-04-21). The proxy module
re-exports every name defined here for backward compatibility, so existing
callers can keep importing ``from research.sentiment_proxy import ...``.

Three functions in this file (``_fetch_combined_headline_items``,
``_cap_headlines_per_calendar_day``, ``_vader_score``) live in the proxy and are
imported lazily inside ``_get_sentiment_detail_impl`` to avoid an import cycle
(proxy → scoring → proxy).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from research.sentiment.lexicons import (
    _CONTEXT_DIRECTION_PAIRS,
    _POSITIVE_KEYWORDS,
    _RISK_KEYWORDS,
    _TICKER_KEYWORD_MAP,
)
from research.sentiment_calendar import (
    DEFAULT_TEST_START,
    TEST_WINDOW_MIN_DAYS,
    test_end_for_start,
    today_iso,
)

logger = logging.getLogger(__name__)

# Re-export from the proxy so signatures stay identical (these constants belong
# semantically to the public API surface declared in sentiment_proxy).
from research.sentiment_proxy import DEFAULT_MAX_HEADLINES, MAX_HEADLINES_CAP  # noqa: E402


def _context_direction_score(
    combined: str,
    active_syms: List[str],
) -> Dict[str, float]:
    """Accumulate per-ticker ΔS from context × direction co-occurrence."""
    delta: Dict[str, float] = {s: 0.0 for s in active_syms}
    for ctx, dire, ticker, side, weight in _CONTEXT_DIRECTION_PAIRS:
        if ticker not in delta:
            continue
        if ctx in combined and dire in combined:
            delta[ticker] += weight if side == "bull" else -weight
    return delta


def _ticker_sentiment_analysis(
    headlines: List[str],
    active_symbols: Optional[List[str]] = None,
) -> Tuple[Dict[str, float], float]:
    """
    Per-ticker bearish/bullish keyword scan → per-symbol ΔS and global severity_boost.

    Two layers:
      Layer 1 — exact phrase match from _TICKER_KEYWORD_MAP (specificity).
      Layer 2 — context × direction co-occurrence from _CONTEXT_DIRECTION_PAIRS
                (catches "energy prices soar", "Iran war stokes volatility", etc.)

    Returns:
        ticker_deltas   — {sym: net_ΔS} clipped to [-cap, +cap] per ticker.
        severity_boost  — Composite ∈ [-0.70, +0.25] added to global S:
                          60% weight on worst-hit ticker + 40% mean of negative deltas.
    """
    syms: List[str] = (
        list(active_symbols) if active_symbols is not None
        else list(_TICKER_KEYWORD_MAP.keys())
    )
    if not headlines or not syms:
        return {}, 0.0

    combined = " ".join(headlines).lower()
    ticker_deltas: Dict[str, float] = {}

    # Layer 1: exact phrase match
    for sym in syms:
        cfg = _TICKER_KEYWORD_MAP.get(sym)
        if not cfg:
            ticker_deltas[sym] = 0.0
            continue
        neg = sum(w for kw, w in cfg["bearish"] if kw in combined)
        pos = sum(w for kw, w in cfg["bullish"] if kw in combined)
        ticker_deltas[sym] = float(max(-cfg["cap"], min(cfg["cap"], pos - neg)))

    # Layer 2: context × direction co-occurrence
    ctx_scores = _context_direction_score(combined, syms)
    for sym in syms:
        base = ticker_deltas.get(sym, 0.0)
        extra = ctx_scores.get(sym, 0.0)
        cap = _TICKER_KEYWORD_MAP[sym]["cap"] if sym in _TICKER_KEYWORD_MAP else 0.60
        ticker_deltas[sym] = float(max(-cap, min(cap, base + extra)))

    if not ticker_deltas:
        return {}, 0.0

    vals = list(ticker_deltas.values())
    neg_vals = [v for v in vals if v < 0]
    worst = min(vals)
    mean_neg = sum(neg_vals) / len(neg_vals) if neg_vals else 0.0
    # 60% worst asset + 40% mean of negatives → amplifies sharp single-asset events
    severity_boost = float(max(-0.70, min(0.25, 0.60 * worst + 0.40 * mean_neg)))
    return ticker_deltas, severity_boost


def _risk_keyword_penalty(headlines: List[str]) -> Tuple[float, int, int]:
    """
    Keyword-based tail-risk detector (geopolitical word counts).
    Returns (penalty_float, negative_hits, positive_hits).
    """
    if not headlines:
        return 0.0, 0, 0
    combined = " ".join(headlines).lower()
    neg_hits = sum(1 for kw in _RISK_KEYWORDS if kw.lower() in combined)
    pos_hits = sum(1 for kw in _POSITIVE_KEYWORDS if kw.lower() in combined)
    # Each negative keyword -0.04, each positive +0.02; net capped at [-0.35, +0.15]
    penalty = float(max(-0.35, min(0.15, -0.04 * neg_hits + 0.02 * pos_hits)))
    return penalty, neg_hits, pos_hits


# ── Public API ────────────────────────────────────────────────────────────────
def _get_sentiment_detail_impl(
    fallback: float,
    max_headlines: int,
    active_symbols: Optional[List[str]],
) -> Dict[str, Any]:
    """Core sentiment pipeline; ``max_headlines`` already clamped to [1, MAX_HEADLINES_CAP]."""
    from research.sentiment_proxy import (
        _cap_headlines_per_calendar_day,
        _fetch_combined_headline_items,
        _vader_score,
    )
    items, fetch_meta, pool_sizes = _fetch_combined_headline_items(max_headlines)
    items = [h for h in items if h.text and str(h.text).strip()]
    try:
        pd_cap = int((os.environ.get("NEWS_MAX_HEADLINES_PER_CALENDAR_DAY") or "80").strip())
    except ValueError:
        pd_cap = 80
    if pd_cap > 0:
        items, dropped_pd = _cap_headlines_per_calendar_day(items, pd_cap)
        fetch_meta = dict(fetch_meta)
        fetch_meta["headlines_per_day_cap"] = int(pd_cap)
        fetch_meta["headlines_removed_by_day_cap"] = int(dropped_pd)
    headlines = [h.text for h in items]
    if not headlines:
        logger.info("No dated headlines after fetch — using fallback sentiment %.2f", fallback)
        try:
            from research.news_fetch_log import write_news_fetch_log

            write_news_fetch_log(
                [],
                fetch_meta,
                max_items=max_headlines,
                pool_sizes=pool_sizes,
                sentiment_detail=None,
            )
        except Exception:
            logger.debug("news_fetch_log empty write skipped", exc_info=True)
        return {
            "score": fallback, "vader_avg": fallback, "penalty": 0.0,
            "severity_boost": 0.0, "neg_hits": 0, "pos_hits": 0,
            "n_headlines": 0, "headlines": [], "source": "fallback",
            "ticker_deltas": {},
            "news_horizon_days": fetch_meta.get("news_horizon_days", 1),
            "effective_test_span_days": fetch_meta.get("effective_test_span_days", TEST_WINDOW_MIN_DAYS),
            "news_gap_days": fetch_meta.get("news_gap_days", 1.0),
            "recommended_test_end": fetch_meta.get("recommended_test_end", today_iso()),
            "crawl4ai_n": 0,
            "rss_dated_entries": fetch_meta.get("rss_dated_entries", 0),
            "dropped_undated_count": fetch_meta.get("dropped_undated_count", 0),
            "raw_headline_candidates": fetch_meta.get("raw_headline_candidates", 0),
            "newapi_articles_before_merge": list(fetch_meta.get("newapi_articles_before_merge") or []),
        }

    vader_avg, per_text = _vader_score(headlines)
    for i, row in enumerate(per_text):
        if i < len(items):
            row["published"] = items[i].published.isoformat() if items[i].published else None
            row["source"] = items[i].source
    penalty, neg_hits, pos_hits = _risk_keyword_penalty(headlines)
    ticker_deltas, severity_boost = _ticker_sentiment_analysis(headlines, active_symbols)
    score = float(max(-1.0, min(1.0, vader_avg + penalty + severity_boost)))

    logger.info(
        "Sentiment: vader=%.3f  penalty=%.3f  severity=%.3f  final=%.3f  "
        "neg_kw=%d  pos_kw=%d  tickers=%d  (from %d headlines)",
        vader_avg, penalty, severity_boost, score,
        neg_hits, pos_hits, len(ticker_deltas), len(headlines),
    )
    result = {
        "score":          score,
        "vader_avg":      round(vader_avg, 3),
        "penalty":        round(penalty, 3),
        "severity_boost": round(severity_boost, 3),
        "neg_hits":       neg_hits,
        "pos_hits":       pos_hits,
        "n_headlines":    len(headlines),
        "headlines":      per_text,
        "source":         "live",
        "ticker_deltas":  {k: round(v, 3) for k, v in ticker_deltas.items()},
        "news_horizon_days": int(fetch_meta.get("news_horizon_days", 1)),
        "effective_test_span_days": int(fetch_meta.get("effective_test_span_days", TEST_WINDOW_MIN_DAYS)),
        "news_gap_days": round(float(fetch_meta.get("news_gap_days", 1.0)), 3),
        "recommended_test_end": str(
            fetch_meta.get("recommended_test_end", test_end_for_start(DEFAULT_TEST_START, TEST_WINDOW_MIN_DAYS))
        ),
        "crawl4ai_n": int(fetch_meta.get("crawl4ai_n", 0)),
        "rss_dated_entries": int(fetch_meta.get("rss_dated_entries", 0)),
        "dropped_undated_count": int(fetch_meta.get("dropped_undated_count", 0)),
        "raw_headline_candidates": int(fetch_meta.get("raw_headline_candidates", 0)),
        "newapi_articles_before_merge": list(fetch_meta.get("newapi_articles_before_merge") or []),
    }
    try:
        from research.news_fetch_log import write_news_fetch_log

        write_news_fetch_log(
            items,
            fetch_meta,
            max_items=max_headlines,
            pool_sizes=pool_sizes,
            sentiment_detail=result,
        )
    except Exception as exc:
        logger.warning("news_fetch_log write failed: %s", exc, exc_info=True)
    return result


def get_sentiment_detail(
    fallback: float = 0.0,
    max_headlines: int = DEFAULT_MAX_HEADLINES,
    active_symbols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Full pipeline with detailed breakdown.

    Args:
        fallback:       Score returned when no headlines can be fetched. Default
                        changed from -0.1 to 0.0 in 2026-04 (see ARCHITECTURE.md
                        §7, step 3) so "no news" no longer looks like a mildly
                        bearish signal; `sentiment_resolver._SENTIMENT_NEUTRAL_FALLBACK`
                        matches this value.
        max_headlines:  Max dated headlines after merge (capped at ``MAX_HEADLINES_CAP``).
        active_symbols: Portfolio tickers for per-asset ΔS and severity_boost.
                        None → use all tickers in _TICKER_KEYWORD_MAP.

    Returns dict with keys:
        score           float  — final S = clip(vader_avg + penalty + severity_boost, -1, 1)
        vader_avg       float  — raw VADER compound average
        penalty         float  — risk-keyword adjustment ∈ [-0.35, +0.15]
        severity_boost  float  — per-ticker composite ∈ [-0.70, +0.25]
        neg_hits        int    — bearish keyword count
        pos_hits        int    — bullish keyword count
        n_headlines     int    — headlines processed
        headlines       list   — per-headline {compound, pos, neg, neu, text}
        ticker_deltas   dict   — {sym: net ΔS} for each active/known ticker
        source          str    — "live" | "fallback"
        newapi_articles_before_merge list — NewsAPI 池（合并前）；每项含 ``published``（日历日）与 ``publishedAt``（API 原始时间串）
    """
    mh = int(max(1, min(int(max_headlines), MAX_HEADLINES_CAP)))
    try:
        return _get_sentiment_detail_impl(fallback, mh, active_symbols)
    except Exception as exc:
        logger.warning("get_sentiment_detail failed: %s", exc, exc_info=True)
        return {
            "score": fallback, "vader_avg": fallback, "penalty": 0.0,
            "severity_boost": 0.0, "neg_hits": 0, "pos_hits": 0,
            "n_headlines": 0, "headlines": [], "source": "fallback",
            "ticker_deltas": {},
            "news_horizon_days": 1,
            "effective_test_span_days": TEST_WINDOW_MIN_DAYS,
            "news_gap_days": 1.0,
            "recommended_test_end": today_iso(),
            "crawl4ai_n": 0,
            "rss_dated_entries": 0,
            "dropped_undated_count": 0,
            "raw_headline_candidates": 0,
            "newapi_articles_before_merge": [],
        }


def get_sentiment_score(
    fallback: float = 0.0,
    max_headlines: int = DEFAULT_MAX_HEADLINES,
    active_symbols: Optional[List[str]] = None,
) -> float:
    """Return a sentiment score in [-1, 1]. Fast path, no breakdown.

    Note: ``fallback`` default changed from -0.1 to 0.0 in 2026-04 to match
    ``dash_app.pipeline_exec.sentiment_resolver._SENTIMENT_NEUTRAL_FALLBACK``;
    "no news available" is now a neutral 0.0 rather than a mildly-bearish -0.1.
    """
    detail = get_sentiment_detail(
        fallback=fallback,
        max_headlines=max_headlines,
        active_symbols=active_symbols,
    )
    return detail["score"]

__all__ = [
    "_context_direction_score",
    "_ticker_sentiment_analysis",
    "_risk_keyword_penalty",
    "_get_sentiment_detail_impl",
    "get_sentiment_detail",
    "get_sentiment_score",
]
