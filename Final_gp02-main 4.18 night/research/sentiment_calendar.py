"""
Test-window and news-horizon helpers.

``effective_test_span_days`` clamps calendar test length to
``[TEST_WINDOW_MIN_DAYS, TEST_WINDOW_MAX_DAYS]`` (default 30–50), using the span from
the earliest *dated* fetched headline through as-of when available.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional, Union

# Calendar test-window length bounds (inclusive span passed to windowing / live news T).
TEST_WINDOW_MIN_DAYS = 30
TEST_WINDOW_MAX_DAYS = 50

# Authoritative defaults (aligned with Phase0Input once schemas import these).
DEFAULT_TEST_START = "2026-02-01"


def clamp_test_span_days(n: int) -> int:
    """Clamp calendar test span to [TEST_WINDOW_MIN_DAYS, TEST_WINDOW_MAX_DAYS]."""
    return max(TEST_WINDOW_MIN_DAYS, min(TEST_WINDOW_MAX_DAYS, int(n)))


def effective_test_span_days(news_horizon_days: int) -> int:
    """Horizon from news metadata, clamped to [min, max]; horizon ≥ 1 before clamp."""
    h = max(1, int(news_horizon_days))
    return clamp_test_span_days(h)


def calendar_span_earliest_to_asof(earliest: date, as_of: date) -> int:
    """Inclusive calendar days from earliest dated headline through as_of (local 'today').

    Returns span clamped to [TEST_WINDOW_MIN_DAYS, TEST_WINDOW_MAX_DAYS].
    """
    if earliest > as_of:
        earliest, as_of = as_of, earliest
    span = (as_of - earliest).days + 1
    span = max(1, int(span))
    return clamp_test_span_days(span)


def test_end_for_start(test_start_iso: str, span_calendar_days: int) -> str:
    """Inclusive end date: day 1 = test_start, span_calendar_days total calendar days."""
    t0 = datetime.strptime(test_start_iso[:10], "%Y-%m-%d").date()
    t1 = t0 + timedelta(days=max(1, int(span_calendar_days)) - 1)
    return t1.isoformat()


def default_test_end() -> str:
    """Legacy: fixed min-span calendar days from DEFAULT_TEST_START (sentiment UI / T display only)."""
    return test_end_for_start(DEFAULT_TEST_START, TEST_WINDOW_MIN_DAYS)


def today_iso() -> str:
    """Calendar today (local) as YYYY-MM-DD — authoritative default for Phase0 test_end."""
    return date.today().isoformat()


def parse_iso_date(s: Optional[Union[str, date, datetime]]) -> Optional[date]:
    if s is None:
        return None
    if isinstance(s, date) and not isinstance(s, datetime):
        return s
    if isinstance(s, datetime):
        return s.date()
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def median_consecutive_gap_days(dates: List[date]) -> float:
    """
    news_gap_days = max(1, median gap in days between consecutive sorted unique dates).
    """
    if len(dates) < 2:
        return 1.0
    u = sorted(set(dates))
    gaps = [(u[i + 1] - u[i]).days for i in range(len(u) - 1)]
    gaps = [g for g in gaps if g >= 0]
    if not gaps:
        return 1.0
    gaps.sort()
    mid = len(gaps) // 2
    med = float(gaps[mid] if len(gaps) % 2 else (gaps[mid - 1] + gaps[mid]) / 2)
    return float(max(1.0, med))
