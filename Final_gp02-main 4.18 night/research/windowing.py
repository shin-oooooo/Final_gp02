"""Dynamic train/test window resolution.

Preserve template trading-day spans from Phase0Input defaults, but slide the
test window so its last day is min(today, last available index day).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional, Tuple

import pandas as pd

from research.sentiment_calendar import clamp_test_span_days


def resolve_dynamic_train_test_windows(
    index: pd.DatetimeIndex,
    *,
    template_train_start: str,
    template_train_end: str,
    template_test_start: str,
    template_test_end: str,
    as_of: Optional[pd.Timestamp] = None,
) -> Tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    """Return (train_start, train_end, test_start, test_end).

    Algorithm
    ---------
    1. Count L_train = trading days in [template_train_start, template_train_end].
    2. Count L_test  = trading days in [template_test_start, template_test_end].
    3. test_end  = min(as_of, index.max())
    4. test window = last L_test trading days on or before test_end.
    5. train window = L_train trading days immediately preceding test_start.
    Falls back to template dates clipped to available data when counts are too small.
    """
    ix = pd.DatetimeIndex(sorted(index.unique()))
    if len(ix) < 5:
        t0 = ix.min() if len(ix) else pd.Timestamp(template_train_start)
        return t0, t0, t0, t0

    as_of = pd.Timestamp(as_of or pd.Timestamp.today().normalize())
    t_tr_s = pd.Timestamp(template_train_start)
    t_tr_e = pd.Timestamp(template_train_end)
    t_te_s = pd.Timestamp(template_test_start)
    t_te_e = pd.Timestamp(template_test_end)

    L_train = int(((ix >= t_tr_s) & (ix <= t_tr_e)).sum())
    L_test = int(((ix >= t_te_s) & (ix <= t_te_e)).sum())

    if L_train < 30 or L_test < 3:
        # Fall back: clip template to data range
        test_end = min(as_of, ix.max(), t_te_e)
        test_start = min(t_te_s, test_end)
        avail_before_test = ix[ix < test_start]
        train_end = avail_before_test.max() if len(avail_before_test) else test_start
        train_start = max(t_tr_s, ix.min())
        return train_start, train_end, test_start, test_end

    cap = min(as_of, ix.max())
    eligible = ix[ix <= cap]
    if len(eligible) < L_test:
        test_ix = eligible
    else:
        test_ix = eligible[-L_test:]
    test_start = test_ix[0]
    test_end = test_ix[-1]

    before_test = ix[ix < test_start]
    if len(before_test) >= L_train:
        train_ix = before_test[-L_train:]
    else:
        train_ix = before_test
    if len(train_ix) == 0:
        return test_start, test_start, test_start, test_end
    return train_ix[0], train_ix[-1], test_start, test_end


def resolve_train_test_with_calendar_test_span(
    index: pd.DatetimeIndex,
    *,
    template_train_start: str,
    template_train_end: str,
    template_test_start: str,
    template_test_end: str,
    calendar_test_span_days: int,
    as_of: Optional[pd.Timestamp] = None,
) -> Tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    """Test = trading days whose calendar dates fall in the last ``calendar_test_span_days`` ending at ``as_of``.

    Train = the same ``L_train`` count as in the template train window, taken from
    trading days strictly before ``test_start``. Falls back to
    :func:`resolve_dynamic_train_test_windows` if the calendar test strip has too
    few trading days.
    """
    ix = pd.DatetimeIndex(sorted(index.unique()))
    if len(ix) < 5:
        return resolve_dynamic_train_test_windows(
            index,
            template_train_start=template_train_start,
            template_train_end=template_train_end,
            template_test_start=template_test_start,
            template_test_end=template_test_end,
            as_of=as_of,
        )

    as_of_ts = pd.Timestamp(as_of or pd.Timestamp.today().normalize())
    cap = min(as_of_ts, ix.max())
    end_d = cap.date()
    span = clamp_test_span_days(max(1, int(calendar_test_span_days)))
    start_d = end_d - timedelta(days=span - 1)

    test_ix = ix[(ix.normalize() >= pd.Timestamp(start_d)) & (ix.normalize() <= cap)]
    if len(test_ix) < 3:
        return resolve_dynamic_train_test_windows(
            index,
            template_train_start=template_train_start,
            template_train_end=template_train_end,
            template_test_start=template_test_start,
            template_test_end=template_test_end,
            as_of=as_of,
        )

    test_start = test_ix[0]
    test_end = test_ix[-1]

    t_tr_s = pd.Timestamp(template_train_start)
    t_tr_e = pd.Timestamp(template_train_end)
    L_train = int(((ix >= t_tr_s) & (ix <= t_tr_e)).sum())

    before_test = ix[ix < test_start]
    if len(before_test) >= L_train and L_train > 0:
        train_ix = before_test[-L_train:]
    else:
        train_ix = before_test
    if len(train_ix) == 0:
        return test_start, test_start, test_start, test_end
    return train_ix[0], train_ix[-1], test_start, test_end


def resolve_regime_break_window(
    index: pd.DatetimeIndex,
    template_break_start: str,
    template_break_end: str,
    test_index: pd.DatetimeIndex,
) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """Slide regime-break regression window to match the tail of the resolved test span."""
    ix = pd.DatetimeIndex(sorted(index.unique()))
    L_brk = int(
        ((ix >= pd.Timestamp(template_break_start)) & (ix <= pd.Timestamp(template_break_end))).sum()
    )
    if L_brk < 3:
        L_brk = min(10, len(test_index))
    te = test_index.sort_values()
    sl = te[-L_brk:] if len(te) >= L_brk else te
    return sl[0], sl[-1]
