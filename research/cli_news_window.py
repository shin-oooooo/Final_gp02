"""Fetch merged headlines and list those in a fixed calendar window + partition segments.

Example (50 inclusive days ending 2026-04-15)::

    python -m research.cli_news_window --anchor 2026-04-15 --span 50 --max-fetch 400
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from research.sentiment_calendar import TEST_WINDOW_MAX_DAYS, TEST_WINDOW_MIN_DAYS, clamp_test_span_days
from research.sentiment_proxy import (
    HeadlineFetch,
    _calendar_segments_partition_by_news_dates,
    _fetch_combined_headline_items,
)


def _window_bounds(anchor: date, span_days: int) -> Tuple[date, date, int]:
    span = clamp_test_span_days(span_days)
    start = anchor - timedelta(days=span - 1)
    return start, anchor, span


def _group_by_day(items: List[HeadlineFetch]) -> Dict[date, List[HeadlineFetch]]:
    g: Dict[date, List[HeadlineFetch]] = defaultdict(list)
    for h in items:
        if h.published is not None:
            g[h.published].append(h)
    return dict(g)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="List headlines in [anchor-(span-1), anchor] after merged fetch.",
    )
    p.add_argument("--anchor", default="2026-04-15", help="Window end (YYYY-MM-DD).")
    p.add_argument(
        "--span",
        type=int,
        default=TEST_WINDOW_MAX_DAYS,
        help=f"Inclusive calendar days (clamped to {TEST_WINDOW_MIN_DAYS}–{TEST_WINDOW_MAX_DAYS}).",
    )
    p.add_argument(
        "--max-fetch",
        type=int,
        default=1200,
        help="Merged fetch cap before window filter (raise for wider 50-day coverage).",
    )
    p.add_argument("--json-out", default="", help="Write full report JSON.")
    args = p.parse_args(argv)

    try:
        anchor = date.fromisoformat(str(args.anchor).strip()[:10])
    except ValueError:
        print("Invalid --anchor date.", file=sys.stderr)
        return 2

    start, end, span_eff = _window_bounds(anchor, args.span)
    max_fetch = max(50, min(int(args.max_fetch), 4000))
    items, meta, _pool = _fetch_combined_headline_items(max_fetch)
    in_win = [h for h in items if h.published is not None and start <= h.published <= end]
    news_days = sorted({h.published for h in in_win if h.published is not None})
    segments = _calendar_segments_partition_by_news_dates(start, end, [d for d in news_days if d])

    print(f"窗口: {start.isoformat()} .. {end.isoformat()}  (含首尾共 {span_eff} 个日历日)")
    print(f"合并抓取: {len(items)} 条 | 窗内: {len(in_win)} 条 | crawl4ai_n={meta.get('crawl4ai_n')}")
    print(f"distinct新闻日: {len(news_days)}")
    print()
    print("---子区间 (与 partition S_t 分段一致) ---")
    if not segments:
        print("(无)")
    else:
        for i, (a, b) in enumerate(segments, 1):
            n = sum(1 for h in in_win if h.published is not None and a <= h.published <= b)
            print(f"  {i}. {a.isoformat()} .. {b.isoformat()}  |窗内条目: {n}")

    print()
    print("--- 窗内新闻 (按日期) ---")
    by_day = _group_by_day(in_win)
    for d in sorted(by_day.keys(), reverse=True):
        rows = sorted(
            by_day[d],
            key=lambda x: (x.published or date.min, x.source, x.text[:60]),
            reverse=True,
        )
        print(f"\n{d.isoformat()} ({len(rows)} 条)")
        for j, h in enumerate(rows, 1):
            t = h.text.replace("\n", " ")[:140]
            print(f"  {j}. [{h.source}] {t}{'…' if len(h.text) > 140 else ''}")

    report: Dict[str, Any] = {
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "span_calendar_days": span_eff,
        "merged_total": len(items),
        "in_window_count": len(in_win),
        "news_days": [d.isoformat() for d in news_days],
        "segments": [[a.isoformat(), b.isoformat()] for a, b in segments],
        "fetch_meta": {
            k: meta[k]
            for k in (
                "crawl4ai_n",
                "geo_rss_n",
                "akshare_enabled",
                "raw_headline_candidates",
            )
            if k in meta
        },
        "headlines": [
            {
                "published": h.published.isoformat() if h.published else None,
                "source": h.source,
                "text": h.text,
            }
            for h in sorted(
                in_win,
                key=lambda x: (x.published or date.min, x.source, x.text[:40]),
                reverse=True,
            )
        ],
    }
    if args.json_out:
        out_path = os.path.abspath(args.json_out)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nWrote {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
