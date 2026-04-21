"""Library-based headline fetchers: AKShare (global wire + CN portals) + Crawl4AI.

Extracted from ``research/sentiment_proxy.py`` (2026-04-21). AKShare and
Crawl4AI both rely on third-party Python packages (``akshare``, ``crawl4ai``)
that are imported lazily inside each fetcher; failure of either surfaces as an
empty list with a warning, never a hard ``ImportError``.

Public entry points (re-exported from ``sentiment_proxy``):
    ``_fetch_akshare_english_headline_items``
    ``_fetch_akshare_cn_headline_items``
    ``_fetch_crawl4ai_headline_items``
"""

from __future__ import annotations

import html
import logging
import os
import re
from datetime import date, datetime, timedelta
from itertools import cycle
from typing import Any, Dict, List, Optional, Sequence, Tuple

from research.crawl4ai_config import CRAWL4AI_TITLE_SEED_TERMS
from research.sentiment.core import (
    HeadlineFetch,
    _akshare_rows_to_items,
    _coerce_date,
    _crawl_result_markdown,
    _parse_loose_date,
    _parse_relative_publication_hint,
    _sort_dated_asc,
    _sort_dated_desc,
)
from research.sentiment.curation import (
    _crawl4ai_markdown_title_acceptable,
    _headline_passes_seed_gate,
    _looks_like_crawl_news_headline,
    _passes_english_wire_headline,
    _seed_gate_enabled_for_all_pools,
)

logger = logging.getLogger(__name__)

def _headline_candidates_from_markdown(
    md: str,
    stamp_fallback: date,
    *,
    per_page_limit: int = 60,
    as_of: Optional[date] = None,
    undated_stamp_dates: Optional[Sequence[date]] = None,
) -> List[HeadlineFetch]:
    """Turn Crawl4AI markdown into dated rows; title-shaped English news only.

    Two-pass strategy
    -----------------
    Pass 1 – structured link extraction (AP News / Guardian style):
        Scan for markdown links ``[label](url)`` where label is a plausible
        news headline.  For each, search the surrounding ±600-char window in
        the raw markdown for an English-format date (which AP News puts in
        nearby image alt-text captions).

    Pass 2 – paragraph fallback (BBC / CNBC / NYT style):
        For any paragraph block (split on 2+ newlines) that was not already
        extracted in pass 1, look for a date in the paragraph and extract
        headline-shaped lines.

    Undated items: receive ``stamp_fallback`` only when no date can be found
    anywhere in the document within the 50-day test window. When
    ``undated_stamp_dates`` is set (non-empty), undated rows cycle those
    calendar days instead (Crawl4AI gap-fill band backup).
    """
    if not md or not str(md).strip():
        return []
    anchor = as_of if as_of is not None else date.today()
    md_raw = html.unescape(str(md))
    out: List[HeadlineFetch] = []
    seen: set = set()
    _rot = cycle([d for d in (undated_stamp_dates or []) if isinstance(d, date)]) if undated_stamp_dates else None

    def _undated_stamp() -> date:
        if _rot is not None:
            return next(_rot)
        return stamp_fallback

    # ── Pass 1: extract (headline, date) from markdown link labels ──────────
    # AP News listing pages pattern:
    #   [ headline text ](https://apnews.com/article/...)
    # Date appears in nearby image alt-text:
    #   ![caption, April 13, 2026. (AP Photo/...)](https://...)
    link_re = re.compile(r'\[([^\]]{15,280})\]\(https?://[^)]+\)')
    last_roll: Optional[date] = None
    for m in link_re.finditer(md_raw):
        label = m.group(1).strip()
        # Skip if label looks like an image alt (contains photo/AP/Reuters credit)
        low_lbl = label.lower()
        if low_lbl.startswith("!"):
            continue
        if any(x in low_lbl for x in ("ap photo", "reuters", "getty", "afp", "http", "\\(", ".jpg", ".png")):
            continue
        text = re.sub(r"[#>*_`\\]+", " ", label)
        text = " ".join(text.split())
        if not _crawl4ai_markdown_title_acceptable(text):
            continue
        k = text.lower()[:140]
        if k in seen:
            continue
        # Search ±600 chars around the match for a date
        window_start = max(0, m.start() - 600)
        window_end = min(len(md_raw), m.end() + 600)
        snippet = md_raw[window_start:window_end]
        d = _parse_loose_date(snippet)
        rel = _parse_relative_publication_hint(text, anchor)
        chosen = d or rel
        pub = chosen or last_roll or _undated_stamp()
        if chosen:
            last_roll = chosen
        seen.add(k)
        out.append(HeadlineFetch(text, pub, "crawl4ai"))
        if len(out) >= per_page_limit:
            return out

    # ── Pass 2: paragraph fallback ──────────────────────────────────────────
    paras = [c.strip() for c in re.split(r"\n{2,}", md_raw) if c.strip()]
    last_seen_date: Optional[date] = None
    last_had_date = False
    for para in paras:
        blob = para[:800]
        d = _parse_loose_date(blob)
        if d is not None:
            last_seen_date = d
            last_had_date = True
        else:
            if not last_had_date:
                last_seen_date = None
            last_had_date = False
        for line in para.split("\n"):
            line = line.strip()
            if len(line) < 15:
                continue
            text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
            text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
            text = re.sub(r"[#>*_`\\]+", " ", text)
            text = " ".join(text.split())
            if not _crawl4ai_markdown_title_acceptable(text):
                continue
            k = text.lower()[:140]
            if k in seen:
                continue
            seen.add(k)
            rel = _parse_relative_publication_hint(text, anchor)
            pub = d or rel or last_seen_date or _undated_stamp()
            out.append(HeadlineFetch(text, pub, "crawl4ai"))
            if len(out) >= per_page_limit:
                return out
    return out


def _fetch_crawl4ai_headline_items(
    max_items: int = 40,
    *,
    undated_stamp_dates: Optional[Sequence[date]] = None,
) -> List[HeadlineFetch]:
    """
    Crawl configured hub/archive URLs via Crawl4AI (markdown → headline snippets).

    Disabled if ``CRAWL4AI_ENABLED=0`` or package missing. Requires Playwright
    browsers (``python -m playwright install chromium``).

    Dates: parsed from snippet when possible; else ``today -
    NEWS_CRAWL_STAMP_OFFSET_DAYS`` (default 30) for undated crawl text (~1 month back).
    When ``undated_stamp_dates`` is provided, undated lines use that list in a cycle
    (gap-fill backup for a configured calendar band).
    """
    if os.environ.get("CRAWL4AI_ENABLED", "1").strip().lower() in ("0", "false", "no"):
        return []
    cap = max(0, min(int(max_items), 160))
    if cap == 0:
        return []
    offset = max(0, int(os.environ.get("NEWS_CRAWL_STAMP_OFFSET_DAYS", "30")))
    stamp_fallback = date.today() - timedelta(days=offset)
    max_urls = max(1, min(int(os.environ.get("CRAWL4AI_MAX_URLS", "6")), 40))
    per_url = max(2, min(int(os.environ.get("CRAWL4AI_PER_PAGE_HEADLINES", "60")), 120))
    try:
        from research.integrations import load_external_integrations

        cfg = load_external_integrations()
        urls: List[str] = []
        for u in list(cfg.news_finance_urls) + list(cfg.news_history_finance_urls):
            u = u.strip()
            if u and u not in urls:
                urls.append(u)
        urls = urls[:max_urls]
    except Exception:
        urls = []
    if not urls:
        return []
    out: List[HeadlineFetch] = []
    seen_keys: set = set()
    try:
        import asyncio

        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
        from crawl4ai.cache_context import CacheMode
    except ImportError:
        logger.debug("crawl4ai not installed — skip (pip install crawl4ai playwright)")
        return []
    except Exception as exc:
        # crawl4ai 0.8+ uses PEP 604 ``X | None`` union syntax at module scope,
        # which raises ``TypeError`` on Python < 3.10 during import. Older
        # versions may fail with other errors (missing optional deps, broken
        # install). Either way: downgrade to an empty pool instead of killing
        # the whole sentiment pipeline.
        logger.warning(
            "crawl4ai import failed (%s: %s) — skipping crawl4ai pool. "
            "If you are on Python < 3.10, upgrade Python or `pip install "
            "\"crawl4ai<0.8\"` for legacy compatibility.",
            type(exc).__name__, exc,
        )
        return []

    run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        word_count_threshold=max(8, int(os.environ.get("CRAWL4AI_WORD_COUNT_MIN", "12"))),
        page_timeout=int(os.environ.get("CRAWL4AI_PAGE_TIMEOUT_MS", "120000")),
        magic=True,
        remove_consent_popups=True,
        simulate_user=os.environ.get("CRAWL4AI_SIMULATE_USER", "1").strip().lower()
        not in ("0", "false", "no"),
        verbose=False,
    )

    async def _run() -> None:
        async with AsyncWebCrawler() as crawler:
            for u in urls:
                if len(out) >= cap:
                    break
                try:
                    res = await crawler.arun(url=u, config=run_cfg)
                    md = _crawl_result_markdown(res)
                    if not md or not str(md).strip():
                        continue
                    for h in _headline_candidates_from_markdown(
                        str(md),
                        stamp_fallback,
                        per_page_limit=per_url,
                        as_of=date.today(),
                        undated_stamp_dates=undated_stamp_dates,
                    ):
                        k = h.text.lower()[:140]
                        if k in seen_keys:
                            continue
                        seen_keys.add(k)
                        out.append(h)
                        if len(out) >= cap:
                            break
                except Exception as e:
                    logger.debug("Crawl4AI skip %s: %s", u[:56], e)

    try:
        asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()
    except Exception as e:
        logger.debug("Crawl4AI batch failed: %s", e)
    # oldest-first so early test-window dates are preserved after merge cap
    out_sorted = _sort_dated_asc(out)
    return out_sorted[:cap]


def _pick_text_column(df: Any, preferred: Tuple[str, ...]) -> Optional[str]:
    """First matching column name, else first object/string column."""
    for c in preferred:
        if c in df.columns:
            return c
    for c in df.columns:
        if df[c].dtype == object or str(df[c].dtype).startswith("string"):
            return str(c)
    return str(df.columns[0]) if len(df.columns) else None


def _fetch_akshare_english_headline_items(max_items: int = 30) -> List[HeadlineFetch]:
    """AKShare **English-leaning** global wire (``stock_info_global_em``), title-filtered.

    The feed always returns today's headlines only, so we stamp every row with
    today's date (column index 2 = '发布时间', but all rows share today).
    """
    if max_items <= 0:
        return []
    items: List[HeadlineFetch] = []
    try:
        import akshare as ak

        df_g = ak.stock_info_global_em()
        if df_g is None or df_g.empty:
            return []
        # Column 0 = title (may be garbled encoding); column 2 = publish datetime
        title_col = df_g.columns[0]
        date_col = df_g.columns[2] if len(df_g.columns) > 2 else None
        today_d = date.today()
        apply_gate = _seed_gate_enabled_for_all_pools()
        for _, row in df_g.iterrows():
            t = str(row[title_col]).strip()
            if not t:
                continue
            pub = None
            if date_col:
                pub = _coerce_date(row[date_col])
            if pub is None:
                pub = today_d
            if not _passes_english_wire_headline(t):
                continue
            if apply_gate and not _headline_passes_seed_gate(t):
                continue
            items.append(HeadlineFetch(t, pub, "global_em"))
            if len(items) >= max_items:
                break
    except ImportError:
        logger.warning("akshare not available — returning empty English AKShare headline list.")
    except Exception as e:
        logger.debug("AKShare global_em skipped: %s", e)

    return _sort_dated_desc(items)[:max_items]


def _fetch_akshare_cn_headline_items(max_items: int = 30) -> List[HeadlineFetch]:
    """Chinese AKShare portals only (no global_em). Opt-in via ``AKSHARE_CN_NEWS_ENABLED``."""
    if max_items <= 0:
        return []
    items: List[HeadlineFetch] = []
    try:
        import akshare as ak

        try:
            df = ak.stock_news_em(symbol="000001")
            col = _pick_text_column(df, ("标题", "title", "新闻标题")) if df is not None else None
            if col:
                items.extend(_akshare_rows_to_items(df, col, "eastmoney", max_items // 2))
        except Exception as e:
            logger.debug("stock_news_em skipped: %s", e)

        try:
            qd = date.today()
            today = qd.strftime("%Y%m%d")
            df2 = ak.news_economic_baidu(date=today)
            col2 = _pick_text_column(df2, ("title", "标题", "新闻标题")) if df2 is not None else None
            if col2:
                items.extend(
                    _akshare_rows_to_items(df2, col2, "baidu_econ", max_items // 2, fallback_date=qd)
                )
        except Exception as e:
            logger.debug("news_economic_baidu skipped: %s", e)

        if len(items) < max_items // 2:
            try:
                df_cx = ak.stock_news_main_cx()
                if df_cx is not None and not df_cx.empty:
                    col_cx = _pick_text_column(df_cx, ("summary", "标题", "title", "新闻标题"))
                    if col_cx:
                        take = max_items - len(items)
                        items.extend(_akshare_rows_to_items(df_cx, col_cx, "cailian", max(1, take)))
            except Exception as e:
                logger.debug("stock_news_main_cx skipped: %s", e)

        if len(items) < max_items // 2:
            try:
                df_cctv = ak.news_cctv()
                col_c = _pick_text_column(df_cctv, ("title", "标题", "新闻标题")) if df_cctv is not None else None
                if col_c:
                    take = max_items - len(items)
                    items.extend(_akshare_rows_to_items(df_cctv, col_c, "cctv", max(1, take)))
            except Exception as e:
                logger.debug("news_cctv skipped: %s", e)

    except ImportError:
        logger.warning("akshare not available — returning empty CN AKShare headline list.")
    except Exception as e:
        logger.warning("AKShare CN fetch failed: %s", e)

    return _sort_dated_desc(items)[:max_items]


__all__ = [
    "_headline_candidates_from_markdown",
    "_fetch_crawl4ai_headline_items",
    "_pick_text_column",
    "_fetch_akshare_english_headline_items",
    "_fetch_akshare_cn_headline_items",
]
