"""Headline curation: post-fetch filtering, merging, caps, gap-fill planning.

Extracted from ``research/sentiment_proxy.py`` (2026-04-21). Three layers:
junk regexes (nav/boilerplate blacklists), headline gates (latin/seed/wire/
crawl4ai shape), and combination strategies (oldest-first vs uniform-daily
caps, NewsAPI gap sampling, Crawl4AI gap-fill planning, calendar partition,
final global cap). Re-exported from ``sentiment_proxy`` to preserve the
legacy import surface.
"""

from __future__ import annotations

import logging
import os
import random
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from itertools import cycle
from typing import Any, Dict, List, Optional, Sequence, Tuple

from research.crawl4ai_config import CRAWL4AI_TITLE_SEED_TERMS
from research.sentiment.core import (
    HeadlineFetch,
    _dedupe_prefer_dated,
    _env_truthy,
    _sort_dated_asc,
)
from research.sentiment_calendar import parse_iso_date

logger = logging.getLogger(__name__)

def _seed_gate_enabled_for_all_pools() -> bool:
    """是否对 RSS / NewsAPI / Google News 也应用种子词库闸门（默认启用）。

    可通过 ``NEWS_SEED_GATE_ALL_POOLS=0`` 关闭，退回到"仅 crawl4ai 应用"的旧行为。
    """
    return _env_truthy("NEWS_SEED_GATE_ALL_POOLS", True)


_NAV_JUNK_RE = re.compile(
    r"subscribe|sign\s*in|privacy\s*policy|cookie|newsletter|skip\s*to|"
    r"create\s+(a\s+)?(free\s+)?account|search\s+(the\s+)?ft|search\s+query|"
    r"got\s+a\s+confidential|closed\s+caption|licensing\s*[&]?\s*reprints|"
    r"adchoices|advertisement|download\s+the\s+app|need\s+help\?|"
    r"detected\s+unusual\s+activity|let\s+us\s+know\s+you'?re|"
    r"make\s+it\s+select|markets\s+pre-?markets|^\s*home\s*$|^\s*markets\s*$|"
    r"investing\s+club\s+trust|pro\s+news|full\s+episodes|livestream\s+menu|"
    r"your\s+email\s+address\s+sign\s+up|whistleblowers",
    re.I,
)


# Crawl4AI 初筛：明显导购/生活榜/登录页等（与 :data:`CRAWL4AI_TITLE_SEED_TERMS` 互补）
_CRAWL_CONSUMER_SHOP_RE = re.compile(
    r"^\s*!|"
    r"^best\s|"
    r"\bbest\s+(hoka|anniversary|birthday|gifts?|coffee|vacuum|mortgage|rewards|water|eye|skin|checking|balance|money\s+market)\b|"
    r"\bgifts?\s+for\b|"
    r"\bstrong\s+buy\s*$|"
    r"remote\s+login|anywhere\s+login|customer\s+support|live\s+conferences|"
    r"supportsupport|loginlogin|"
    r"deals\s*&\s*buying|buying\s+guides|federal\s+vs\.?\s*private|"
    r"at\s+your\s+fingertips|bloomberg\.com\s+subscription|get\s+the\s+most\s+important\s+global\s+markets\s+news",
    re.I,
)


# 站内导航/空章节/统计条目/API 异常串 —— 通用 junk 黑名单（对所有 pool 生效）。
# 2026-04 扩充：NewsAPI rate-limit 错误串 + crawl4ai 泄漏的页面导航片段。
_HEADLINE_PAGE_NAV_JUNK_RE = re.compile(
    r"^\s*most\s+active\b|"
    r"^\s*lowest\s+\w+\s+rates?\b|"
    r"^\s*highest\s+\w+\s+rates?\b|"
    r"\btax\s+brackets?\b|"
    r"\bmortgage\s+rates?\b|"
    r"\bpenny\s+stocks?\b|"
    r"\bsec\s*&\s*markets\s+data\b|"
    r"\badministrative\s+law\s+judge\b|"
    r"\bharmed\s+investors?\b|"
    r"\bdistributions?\s+to\s+harmed\b|"
    r"\bbudget\s*&\s*performance\b|"
    r"\bmarket\s+domination\s+overtime\b|"
    r"\bsaving\s+and\s+investing\s+(for|in)\b|"
    r"\binitial\s+decisions?\b|"
    r"\bsec\s+rules?\s+and\s+regulations?\b|"
    r"\bsec\s+actions?\s+against\b|"
    r"\bhow\s+to\s+(file|report|submit|apply|save|invest)\b|"
    r"\bwhistle[- ]?blowers?\b|"
    r"\bfull\s+episodes?\b|"
    r"\bpro\s+news\b|"
    r"\blivestream\s+menu\b|"
    r"\bmarket\s+movers?$|"
    # NewsAPI rate-limit / quota errors
    r"you\s+have\s+made\s+too\s+many\s+requests|"
    r"developer\s+accounts?\s+are\s+limited|"
    r"rate\s+limit\s+exceeded|"
    r"please\s+upgrade\s+to\s+a\s+paid\s+plan|"
    r"api[- ]?key\s+(missing|invalid|expired)|"
    # Static page/table labels
    r"^\s*(sec|fed|irs|fbi|doj|cia|nato)\s+(faqs?|forms?|rules?|data|contacts?)\s*$|"
    r"^\s*markets\s+pre-?markets?\s*$",
    re.I,
)


def _latin_word_count(text: str) -> int:
    """Rough word count on Latin-letter whitespace tokens (drops pure punctuation)."""
    return sum(1 for w in str(text).split() if any(c.isalpha() for c in w))


def _headline_passes_seed_gate(
    text: str,
    *,
    min_words: int = 3,
    require_seed: bool = True,
) -> bool:
    """**通用** headline 筛选闸门：对所有 pool（RSS / NewsAPI / Google News / crawl4ai）生效。

    判定（**按顺序短路**）：

    1. 归一化空白、剔除控制字符；若最终长度 < 14 字符或 Latin-letter 词数 < ``min_words`` → False。
    2. 命中 :data:`_NAV_JUNK_RE` / :data:`_HEADLINE_PAGE_NAV_JUNK_RE` / :data:`_CRAWL_CONSUMER_SHOP_RE` 的
       任一导航/营销/异常串 → False（包括 NewsAPI 的 rate-limit 错误串）。
    3. ``require_seed=True``（默认）时必须至少命中一个 :data:`CRAWL4AI_TITLE_SEED_TERMS`
       子串（忽略大小写）；否则为 False。

    Args:
        text: 原始 headline 文本。
        min_words: Latin-letter 词数最小值，默认 3（保留 "Iran strikes Israel" 这类 3-词突发标题；
            3-词的已知垃圾—— "Budget & Performance" / "Tax brackets and rates" 等——由
            :data:`_HEADLINE_PAGE_NAV_JUNK_RE` 精确剔除，故不影响召回）。
        require_seed: 是否强制命中种子词库；False 时仅做形态与 junk 过滤。

    Returns:
        True → 放行；False → 拒绝。
    """
    if not text:
        return False
    t = " ".join(str(text).split()).strip()
    if len(t) < 14:
        return False
    if _latin_word_count(t) < max(1, int(min_words)):
        return False
    low = t.lower()
    if _NAV_JUNK_RE.search(low):
        return False
    if _HEADLINE_PAGE_NAV_JUNK_RE.search(low):
        return False
    if _CRAWL_CONSUMER_SHOP_RE.search(low):
        return False
    if not require_seed:
        return True
    return any(seed in low for seed in CRAWL4AI_TITLE_SEED_TERMS)


def _crawl4ai_markdown_title_acceptable(text: str) -> bool:
    """Crawl4AI 专用：形态门 + 明显非新闻剔除 + 至少命中一条种子词（:data:`CRAWL4AI_TITLE_SEED_TERMS`）。"""
    if not _looks_like_crawl_news_headline(text):
        return False
    return _headline_passes_seed_gate(text, min_words=3, require_seed=True)


def _cap_headlines_per_calendar_day(
    items: List[HeadlineFetch], per_day: int
) -> Tuple[List[HeadlineFetch], int]:
    """同一 ``published`` 日历日最多保留 ``per_day`` 条（日内 oldest-first：source → text）。"""
    if per_day <= 0 or not items:
        return items, 0
    by_day: Dict[date, List[HeadlineFetch]] = defaultdict(list)
    for h in items:
        if h.published is not None:
            by_day[h.published].append(h)
    trimmed: List[HeadlineFetch] = []
    dropped = 0
    for d in sorted(by_day.keys()):
        rows = sorted(by_day[d], key=lambda x: (x.source, x.text[:80]))[:per_day]
        n = len(by_day[d])
        if n > per_day:
            dropped += n - per_day
        trimmed.extend(rows)
    trimmed.sort(key=lambda h: (h.published or date.min, h.source, h.text[:60]))
    return trimmed, dropped


def _latin_letter_count(text: str) -> int:
    return sum(1 for c in text if ("A" <= c <= "Z" or "a" <= c <= "z"))


def _is_mostly_latin_headline(text: str, *, min_letters: int = 18, ratio: float = 0.58) -> bool:
    """Headline is predominantly Latin letters (English / tickers / brands)."""
    t = text.replace(" ", "")
    if not t:
        return False
    letters = _latin_letter_count(text)
    if letters < min_letters:
        return False
    return (letters / max(len(t), 1)) >= ratio


def _passes_english_wire_headline(text: str) -> bool:
    """Looser gate for AKShare global wire titles."""
    t = " ".join(str(text).split()).strip()
    if len(t) < 22 or len(t) > 320:
        return False
    low = t.lower()
    if "http://" in low or "https://" in low or "www." in low:
        return False
    if t.count("|") >= 2:
        return False
    if "![cnbc]" in low or "![ft]" in low or "skip to" in low:
        return False
    if _NAV_JUNK_RE.search(low):
        return False
    if not _is_mostly_latin_headline(t, min_letters=14, ratio=0.45):
        return False
    return True


def _looks_like_crawl_news_headline(text: str) -> bool:
    """Gate for Crawl4AI chunks: title-shaped English news only.

    Relaxed from the original strict version so that AP News / Guardian /
    BBC headline fragments (often 30–200 chars) are not filtered out.
    """
    t = " ".join(str(text).split()).strip()
    if len(t) < 18 or len(t) > 320:
        return False
    low = t.lower()
    if "http://" in low or "https://" in low or "www." in low:
        return False
    if t.count("|") >= 3:
        return False
    if "!(" in t or "](" in t:
        return False
    if _NAV_JUNK_RE.search(low):
        return False
    # Require predominantly Latin text (relaxed: min 10 letters, 45% ratio)
    if not _is_mostly_latin_headline(t, min_letters=10, ratio=0.45):
        return False
    words = [w for w in re.split(r"\s+", t) if w]
    if len(words) < 3:
        return False
    upper_ratio = sum(1 for c in t if c.isupper()) / max(len(t), 1)
    if upper_ratio > 0.50:
        return False
    return True


def _calendar_segments_partition_by_news_dates(
    test_start: date, test_end: date, news_days: List[date]
) -> List[Tuple[date, date]]:
    """Split [test_start, test_end] (inclusive) at each distinct news calendar day.

    First segment runs from test_start through the earliest news day in range; then
    each later segment runs (prev_news_day + 1) through the next news day; finally
    any tail after the last news day through test_end.
    """
    u = sorted({d for d in news_days if test_start <= d <= test_end})
    if not u:
        return [(test_start, test_end)]
    out: List[Tuple[date, date]] = [(test_start, u[0])]
    for i in range(len(u) - 1):
        a = u[i] + timedelta(days=1)
        b = u[i + 1]
        if a <= b:
            out.append((a, b))
    if u[-1] < test_end:
        out.append((u[-1] + timedelta(days=1), test_end))
    return out


def _oldest_first_cap(items: List[HeadlineFetch], max_items: int) -> List[HeadlineFetch]:
    """Select up to ``max_items`` headlines, **oldest calendar date first**.

    Only items whose ``published`` date falls within the test-window upper bound
    (``TEST_WINDOW_MAX_DAYS`` calendar days ending today) are considered.
    This guarantees every selected headline can actually produce an S_t node
    inside the test window.  If no items pass the window filter the full list
    is used as a fallback so the pipeline never returns empty-handed.

    Rationale (per project spec §15):
    - Oldest-first ordering so early test-window dates always get slots.
    - Window filter drops news older than 50 days (TEST_WINDOW_MAX_DAYS).
    - Undated items are excluded before this function is called.
    """
    if max_items <= 0 or not items:
        return []
    from research.sentiment_calendar import TEST_WINDOW_MAX_DAYS
    window_start = date.today() - timedelta(days=TEST_WINDOW_MAX_DAYS - 1)
    in_window = [h for h in items if h.published is not None and h.published >= window_start]
    candidates = in_window if in_window else items
    # sort ascending by date (oldest first)
    sorted_asc = sorted(candidates, key=lambda h: (h.published or date.min, h.source, h.text[:60]))
    return sorted_asc[:max_items]


def _uniform_daily_cap(items: List[HeadlineFetch], max_items: int) -> List[HeadlineFetch]:
    """Select up to ``max_items`` headlines with **round-robin across calendar days** (oldest days first).

    Within each day, items are consumed in deterministic ``(source, text)`` order.
    Spreads selection across dates so merge/final caps do not collapse into only
    the earliest few calendar days when many headlines share those dates.
    """
    if max_items <= 0 or not items:
        return []
    from research.sentiment_calendar import TEST_WINDOW_MAX_DAYS

    window_start = date.today() - timedelta(days=TEST_WINDOW_MAX_DAYS - 1)
    candidates = [h for h in items if h.published is not None and h.published >= window_start]
    if not candidates:
        candidates = [h for h in items if h.published is not None]
    if not candidates:
        return []
    by_day: Dict[date, List[HeadlineFetch]] = defaultdict(list)
    for h in candidates:
        by_day[h.published].append(h)
    for d in by_day:
        by_day[d].sort(key=lambda x: (x.source, x.text[:60]))
    days = sorted(by_day.keys())
    ptr: Dict[date, int] = {d: 0 for d in days}
    out: List[HeadlineFetch] = []
    while len(out) < max_items:
        progressed = False
        for d in days:
            if len(out) >= max_items:
                break
            i = ptr[d]
            bucket = by_day[d]
            if i < len(bucket):
                out.append(bucket[i])
                ptr[d] = i + 1
                progressed = True
        if not progressed:
            break
    return out


def _merge_cap_fn():
    """Resolve merge/final cap strategy: uniform round-robin per day vs oldest-first."""
    return _uniform_daily_cap if _env_truthy("NEWS_UNIFORM_DAILY_MERGE", True) else _oldest_first_cap


def _count_headlines_by_day_in_range(
    items: Sequence[HeadlineFetch], d0: date, d1: date
) -> Dict[date, int]:
    """Count dated headlines per calendar day within ``[d0, d1]`` (inclusive)."""
    c: Counter[date] = Counter()
    for h in items:
        p = h.published
        if p is None or p < d0 or p > d1:
            continue
        c[p] += 1
    return dict(c)


def _iter_inclusive_calendar_days(d0: date, d1: date) -> List[date]:
    if d0 > d1:
        d0, d1 = d1, d0
    out: List[date] = []
    cur = d0
    while cur <= d1:
        out.append(cur)
        cur += timedelta(days=1)
    return out


def _crawl4ai_gap_fill_window() -> Optional[Tuple[date, date]]:
    """Inclusive calendar band for Crawl4AI backup fill (disabled via ``CRAWL4AI_GAP_FILL_ENABLED=0``)."""
    if not _env_truthy("CRAWL4AI_GAP_FILL_ENABLED", True):
        return None
    ds = (os.environ.get("CRAWL4AI_GAP_FILL_START") or "2026-03-17").strip()[:10]
    de = (os.environ.get("CRAWL4AI_GAP_FILL_END") or "2026-04-01").strip()[:10]
    d0 = parse_iso_date(ds)
    d1 = parse_iso_date(de)
    if d0 is None or d1 is None:
        return None
    if d0 > d1:
        d0, d1 = d1, d0
    return d0, d1


def _crawl4ai_gap_fill_plan(
    primary: Sequence[HeadlineFetch],
) -> Tuple[bool, List[date], List[date], Dict[date, int], int]:
    """If primary news is thin on ``[gap_start, gap_end]``, return trigger + stamp cycle + sparse + counts + band_total."""
    win = _crawl4ai_gap_fill_window()
    if not win:
        return False, [], [], {}, 0
    g0, g1 = win
    try:
        min_per = int((os.environ.get("CRAWL4AI_GAP_FILL_MIN_PER_DAY") or "2").strip())
    except ValueError:
        min_per = 2
    min_per = int(max(1, min_per))
    try:
        min_band = int((os.environ.get("CRAWL4AI_GAP_FILL_MIN_BAND_TOTAL") or "24").strip())
    except ValueError:
        min_band = 24
    min_band = int(max(1, min_band))
    days = _iter_inclusive_calendar_days(g0, g1)
    counts = _count_headlines_by_day_in_range(list(primary), g0, g1)
    sparse = [d for d in days if int(counts.get(d, 0)) < min_per]
    band_total = sum(int(counts.get(d, 0)) for d in days)
    triggered = bool(sparse) or band_total < min_band
    if not triggered:
        return False, [], sparse, counts, band_total
    stamp_dates = sparse if sparse else days
    return True, stamp_dates, sparse, counts, band_total


def _select_newapi_gap_days(
    d0: date,
    d1: date,
    counts: Dict[date, int],
    *,
    min_count: int,
    max_days: int,
    rng: random.Random,
) -> List[date]:
    """Calendar days in ``[d0,d1]`` with RSS+geo count ``< min_count``; sample up to ``max_days``."""
    if max_days <= 0:
        return []
    days: List[date] = []
    cur = d0
    while cur <= d1:
        if int(counts.get(cur, 0)) < int(max(0, min_count)):
            days.append(cur)
        cur += timedelta(days=1)
    if not days:
        return []
    k = min(int(max(1, max_days)), len(days))
    return sorted(rng.sample(days, k=k))


def _merge_headline_lists(
    pools: List[List[HeadlineFetch]], max_items: int
) -> Tuple[List[HeadlineFetch], int, int]:
    """Merge pools, drop undated, dedup, then cap **oldest-first within test window**.

    Pool order matters for priority: geo-seed pool is passed before generic RSS
    so that seed-related items survive dedup when text is identical across feeds.
    """
    flat: List[HeadlineFetch] = []
    for p in pools:
        flat.extend(p)
    raw_n = len(flat)
    deduped = _dedupe_prefer_dated(flat)
    dated_only = [h for h in deduped if h.published is not None]
    dropped_undated = len(deduped) - len(dated_only)
    out = _merge_cap_fn()(dated_only, max_items)
    return out, dropped_undated, raw_n


def _finalize_headline_cap(items: List[HeadlineFetch], max_items: int) -> List[HeadlineFetch]:
    """Final cap: oldest-first (keeps early test-window dates for S_t segmentation).

    ``NEWS_PREFER_HISTORY_BAND=1`` enables a legacy band selector instead
    (prefers headlines whose age lies near NEWS_HISTORY_TARGET_DAYS ± tolerance).
    """
    if max_items <= 0 or not items:
        return []
    if not _env_truthy("NEWS_PREFER_HISTORY_BAND", False):
        return _merge_cap_fn()(items, max_items)
    target = int(os.environ.get("NEWS_HISTORY_TARGET_DAYS", "30"))
    tol = int(os.environ.get("NEWS_HISTORY_TOLERANCE_DAYS", "21"))
    today = date.today()
    band: List[HeadlineFetch] = []
    rest: List[HeadlineFetch] = []
    for h in items:
        pub_d = h.published
        if pub_d is None:
            rest.append(h)
            continue
        age = (today - pub_d).days
        if target - tol <= age <= target + tol:
            band.append(h)
        else:
            rest.append(h)
    # Within band and rest, still oldest-first
    cap_fn = _merge_cap_fn()
    ordered = cap_fn(band, max_items) + cap_fn(rest, max_items)
    return cap_fn(ordered, max_items)


__all__ = (
    "_seed_gate_enabled_for_all_pools",
    "_NAV_JUNK_RE", "_CRAWL_CONSUMER_SHOP_RE", "_HEADLINE_PAGE_NAV_JUNK_RE",
    "_latin_word_count", "_headline_passes_seed_gate",
    "_crawl4ai_markdown_title_acceptable", "_cap_headlines_per_calendar_day",
    "_latin_letter_count", "_is_mostly_latin_headline",
    "_passes_english_wire_headline", "_looks_like_crawl_news_headline",
    "_calendar_segments_partition_by_news_dates",
    "_oldest_first_cap", "_uniform_daily_cap", "_merge_cap_fn",
    "_count_headlines_by_day_in_range", "_iter_inclusive_calendar_days",
    "_crawl4ai_gap_fill_window", "_crawl4ai_gap_fill_plan",
    "_select_newapi_gap_days",
    "_merge_headline_lists", "_finalize_headline_cap",
)
