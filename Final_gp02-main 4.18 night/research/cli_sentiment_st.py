"""Fetch headlines (RSS + AKShare + Crawl4AI) and compute VADER-based S_t — no web UI.

Run from repository root::

    python -m research.cli_sentiment_st
    python -m research.cli_sentiment_st --data data.json --output st.csv

``--mode partition`` matches :func:`research.pipeline.run_pipeline` live sentiment
(:func:`research.sentiment_proxy.vader_st_series_partition_cumulative_from_detail`).
``--mode daily`` uses per-calendar-day mean compound with ffill/bfill.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from typing import Any, Dict, List, Optional, Tuple, cast

import pandas as pd

from research.schemas import Phase0Input
from research.sentiment_calendar import TEST_WINDOW_MIN_DAYS, parse_iso_date
from research.sentiment_proxy import (
    DEFAULT_MAX_HEADLINES,
    get_sentiment_detail,
    vader_st_series_from_detail,
    vader_st_series_partition_cumulative_from_detail,
)
from research.windowing import (
    resolve_dynamic_train_test_windows,
    resolve_train_test_with_calendar_test_span,
)


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _resolve_windows_from_prices(
    rets_index: pd.DatetimeIndex,
    p0i: Phase0Input,
    detail: Dict[str, Any],
) -> Tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    live = detail.get("source") == "live"
    span = int(detail.get("effective_test_span_days") or 0)
    if live and span >= TEST_WINDOW_MIN_DAYS:
        return resolve_train_test_with_calendar_test_span(
            rets_index,
            template_train_start=p0i.train_start,
            template_train_end=p0i.train_end,
            template_test_start=p0i.test_start,
            template_test_end=p0i.test_end,
            calendar_test_span_days=span,
        )
    return resolve_dynamic_train_test_windows(
        rets_index,
        template_train_start=p0i.train_start,
        template_train_end=p0i.train_end,
        template_test_start=p0i.test_start,
        template_test_end=p0i.test_end,
    )


def _load_returns_index(json_path: str) -> pd.DatetimeIndex:
    from ass1_core import daily_returns, load_bundle

    bundle = load_bundle(json_path)
    close = bundle.close_universe.sort_index()
    p0i = Phase0Input()
    syms = [
        s
        for s in (
            p0i.tech_symbols + p0i.hedge_symbols + p0i.safe_symbols + [p0i.benchmark]
        )
        if s in close.columns
    ]
    if not syms:
        syms = list(close.columns)[:5]
    rets = daily_returns(close[syms]).dropna(how="all")
    return pd.DatetimeIndex(rets.index)


def _calendar_business_index(d0: date, d1: date) -> pd.DatetimeIndex:
    return pd.bdate_range(d0.isoformat(), d1.isoformat())


def main(argv: Optional[List[str]] = None) -> int:
    root = _repo_root()
    default_data = os.path.join(root, "data.json")

    p = argparse.ArgumentParser(description="Crawl/fetch news and compute S_t (VADER).")
    p.add_argument(
        "--data",
        default=default_data,
        help="Path to data.json (for trading calendar & pipeline-style test window).",
    )
    p.add_argument(
        "--no-prices",
        action="store_true",
        help="Ignore data.json; use --test-start/--test-end as calendar bounds for S_t index.",
    )
    p.add_argument(
        "--test-start",
        default="",
        help="With --no-prices: first calendar day of test strip (YYYY-MM-DD).",
    )
    p.add_argument(
        "--test-end",
        default="",
        help="With --no-prices: last calendar day of test strip (YYYY-MM-DD). Default: today.",
    )
    p.add_argument("--fallback", type=float, default=-0.1, help="VADER fallback when no headlines.")
    p.add_argument("--max-headlines", type=int, default=DEFAULT_MAX_HEADLINES)
    p.add_argument(
        "--mode",
        choices=("partition", "daily"),
        default="partition",
        help="partition: same as pipeline; daily: mean compound per day + ffill.",
    )
    p.add_argument("--output", default="", help="Write CSV (date,S_t). Omit to print only summary.")
    p.add_argument("--json-meta", default="", help="Optional path to write fetch metadata JSON.")
    args = p.parse_args(argv)

    detail = get_sentiment_detail(
        fallback=args.fallback,
        max_headlines=args.max_headlines,
        active_symbols=None,
    )

    if args.json_meta:
        meta = {
            "source": detail.get("source"),
            "score": detail.get("score"),
            "vader_avg": detail.get("vader_avg"),
            "n_headlines": detail.get("n_headlines"),
            "crawl4ai_n": detail.get("crawl4ai_n"),
            "effective_test_span_days": detail.get("effective_test_span_days"),
        }
        with open(args.json_meta, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    if args.no_prices:
        t1 = parse_iso_date(args.test_end) or date.today()
        t0 = parse_iso_date(args.test_start)
        if t0 is None:
            span = int(detail.get("effective_test_span_days") or TEST_WINDOW_MIN_DAYS)
            from datetime import timedelta

            t0 = t1 - timedelta(days=max(1, span) - 1)
        idx = _calendar_business_index(t0, t1)
        test_mask_dates = (t0, t1)
        train_msg = "calendar-only index"
    else:
        if not os.path.isfile(args.data):
            print(f"Missing --data file: {args.data}", file=sys.stderr)
            return 2
        try:
            ix = _load_returns_index(args.data)
        except Exception as e:
            print(f"Failed to load returns index from {args.data}: {e}", file=sys.stderr)
            return 2
        p0i = Phase0Input()
        train_start, train_end, test_start, test_end = _resolve_windows_from_prices(ix, p0i, detail)
        test_mask = (ix >= test_start) & (ix <= test_end)
        idx = ix[test_mask]
        test_mask_dates = (test_start.date(), test_end.date())
        train_msg = f"train {train_start.date()}..{train_end.date()}"

    if len(idx) == 0:
        print("Empty index for S_t.", file=sys.stderr)
        return 3

    if args.mode == "partition":
        st = vader_st_series_partition_cumulative_from_detail(
            cast(Dict[str, Any], detail),
            idx,
            test_start_cal=test_mask_dates[0],
            test_end_cal=test_mask_dates[1],
            fallback=float(args.fallback),
        )
    else:
        st = vader_st_series_from_detail(
            cast(Dict[str, Any], detail),
            idx,
            fallback=float(args.fallback),
        )

    print(
        f"source={detail.get('source')}  headlines={detail.get('n_headlines')}  "
        f"crawl4ai_n={detail.get('crawl4ai_n')}  mode={args.mode}"
    )
    if not args.no_prices:
        print(f"windows: {train_msg}  test {test_mask_dates[0]}..{test_mask_dates[1]}  days={len(st)}")
    else:
        print(f"calendar test strip: {test_mask_dates[0]}..{test_mask_dates[1]}  days={len(st)}")
    if len(st):
        print(f"S_t first={st.iloc[0]:+.4f}  last={st.iloc[-1]:+.4f}  min={st.min():+.4f}  max={st.max():+.4f}")

    if args.output:
        out = pd.DataFrame({"date": st.index.strftime("%Y-%m-%d"), "S_t": st.values})
        out.to_csv(args.output, index=False)
        print(f"Wrote {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
