"""
Sentiment Proxy — LLM-free automatic sentiment scoring (thin re-export shim).

Since 2026-04-21 the implementation lives under the ``research.sentiment``
package (``core``, ``curation``, ``sources_http``, ``sources_crawl``,
``pipeline``, ``scoring``, ``series``, ``lexicons``). This module keeps the
historical import surface intact so every legacy call site —

    from research.sentiment_proxy import get_sentiment_detail, HeadlineFetch
    from research.sentiment_proxy import _fetch_combined_headline_items
    from research.sentiment_proxy import vader_st_series_kernel_smoothed_from_detail

— continues to work without modification.

Scoring formula (unchanged):
    S = clip(vader_avg + penalty + severity_boost, -1, 1)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── Lexicon data tables ───────────────────────────────────────────────────────
from research.sentiment.lexicons import (  # noqa: F401
    _CONTEXT_DIRECTION_PAIRS,
    _IRAN_US_LEXICON,
    _MONTH_PREFIX,
    _POSITIVE_KEYWORDS,
    _RISK_KEYWORDS,
    _TICKER_KEYWORD_MAP,
)

# ── Core: types / date utils / VADER / date hints / crawl markdown ────────────
from research.sentiment.core import (  # noqa: F401
    DEFAULT_MAX_HEADLINES,
    HeadlineFetch,
    MAX_HEADLINES_CAP,
    _akshare_rows_to_items,
    _coerce_date,
    _crawl_result_markdown,
    _dedupe_prefer_dated,
    _env_truthy,
    _estimate_news_horizon_days,
    _make_vader_analyzer,
    _parse_loose_date,
    _parse_relative_publication_hint,
    _pick_date_column,
    _sort_dated_asc,
    _sort_dated_desc,
    _vader_score,
)

# ── Curation: junk regex / gates / cap / merge / gap-fill planning ────────────
from research.sentiment.curation import (  # noqa: F401
    _HEADLINE_PAGE_NAV_JUNK_RE,
    _NAV_JUNK_RE,
    _CRAWL_CONSUMER_SHOP_RE,
    _calendar_segments_partition_by_news_dates,
    _cap_headlines_per_calendar_day,
    _count_headlines_by_day_in_range,
    _crawl4ai_gap_fill_plan,
    _crawl4ai_gap_fill_window,
    _crawl4ai_markdown_title_acceptable,
    _finalize_headline_cap,
    _headline_passes_seed_gate,
    _is_mostly_latin_headline,
    _iter_inclusive_calendar_days,
    _latin_letter_count,
    _latin_word_count,
    _looks_like_crawl_news_headline,
    _merge_cap_fn,
    _merge_headline_lists,
    _oldest_first_cap,
    _passes_english_wire_headline,
    _seed_gate_enabled_for_all_pools,
    _select_newapi_gap_days,
    _uniform_daily_cap,
)

# ── HTTP sources (RSS + NewsAPI) ──────────────────────────────────────────────
from research.sentiment.sources_http import (  # noqa: F401
    _MARKET_RSS_FEEDS,
    _fetch_geo_seed_rss_items,
    _fetch_newapi_headline_items,
    _fetch_one_rss_feed,
    _fetch_rss_from_feed_list,
    _fetch_rss_headline_items,
    _rss_entry_date,
    _rss_http_timeout_sec,
    _rss_parallel_enabled,
)

# ── Library sources (AKShare + Crawl4AI) ──────────────────────────────────────
from research.sentiment.sources_crawl import (  # noqa: F401
    _fetch_akshare_cn_headline_items,
    _fetch_akshare_english_headline_items,
    _fetch_crawl4ai_headline_items,
    _headline_candidates_from_markdown,
    _pick_text_column,
)

# ── Orchestrator ──────────────────────────────────────────────────────────────
from research.sentiment.pipeline import (  # noqa: F401
    _build_premerge_snapshot_rows,
    _fetch_combined_headline_items,
    _fetch_crawl4ai_pool_with_dedupe,
    _fetch_newapi_pool,
    _finalize_combined_headline_meta,
    _resolve_crawl4ai_quotas,
)

# ── Public sentiment API ──────────────────────────────────────────────────────
from research.sentiment.scoring import (  # noqa: F401
    _context_direction_score,
    _get_sentiment_detail_impl,
    _risk_keyword_penalty,
    _ticker_sentiment_analysis,
    get_sentiment_detail,
    get_sentiment_score,
)

# ── S_t time-series builders ──────────────────────────────────────────────────
from research.sentiment.series import (  # noqa: F401
    _KernelSmoothParams,
    _aggregate_headline_compounds_per_day,
    _normalize_kernel_smooth_params,
    _robust_daily_compound,
    vader_st_series_from_detail,
    vader_st_series_kernel_smoothed_from_detail,
    vader_st_series_partition_cumulative_from_detail,
    )
