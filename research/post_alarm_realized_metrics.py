"""Post-alarm realized return features: crash definition, cross-section chaos, tail thickening.

不使用组合权重：逐标的计算，再用横截面统计量汇总。
大跌定义：训练窗内估计的逐标的 3 日复合收益下分位阈值（默认 5%）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def _compound_h_day(s: pd.Series, h: int = 3) -> float:
    """Compound return over the first h rows of series s (length >= h)."""
    v = s.to_numpy(dtype=float)[:h]
    if v.size < h or not np.all(np.isfinite(v)):
        return float("nan")
    out = 1.0
    for x in v:
        out *= 1.0 + float(x)
    return float(out - 1.0)


def _rolling_three_day_compound_series(s: pd.Series) -> np.ndarray:
    """Aligned so out[t] = compound return over days t, t+1, t+2 (same index as s)."""
    v = s.dropna().astype(float).to_numpy()
    n = len(v)
    if n < 3:
        return np.array([])
    a, b, c = v[:-2], v[1:-1], v[2:]
    return (1.0 + a) * (1.0 + b) * (1.0 + c) - 1.0


def _rolling_h_day_compound_series(s: pd.Series, h: int) -> np.ndarray:
    """Aligned so out[t] = compound return over days t..t+h-1 (same index as s.dropna())."""
    v = s.dropna().astype(float).to_numpy()
    n = len(v)
    hh = int(max(1, h))
    if n < hh:
        return np.array([])
    out = np.ones(n - hh + 1, dtype=float)
    for k in range(hh):
        out *= 1.0 + v[k : k + (n - hh + 1)]
    return out - 1.0


def _excess_kurtosis(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 8:
        return float("nan")
    m = float(np.mean(x))
    d = x - m
    v = float(np.var(d, ddof=1))
    if v < 1e-18:
        return float("nan")
    m4 = float(np.mean(d**4))
    return float(m4 / (v * v) - 3.0)


def train_per_symbol_crash_thresholds(
    r_train: pd.DataFrame,
    symbols: List[str],
    lower_q: float = 0.05,
    *,
    h: int = 3,
) -> Dict[str, float]:
    """Lower-q quantile of rolling h-day compound returns, estimated on train only per symbol."""
    qmap: Dict[str, float] = {}
    q = float(np.clip(lower_q, 0.01, 0.25))
    hh = int(max(1, h))
    for sym in symbols:
        if sym not in r_train.columns:
            continue
        Rh = _rolling_h_day_compound_series(r_train[sym], hh)
        if Rh.size == 0:
            qmap[sym] = float("-inf")
            continue
        qmap[sym] = float(np.quantile(Rh, q))
    return qmap


def crash_definition_label(lower_q: float) -> str:
    p = int(round(float(lower_q) * 100))
    return (
        f"大跌（逐标的）：告警后连续 3 个交易日的复合收益 R^(3)=∏(1+r_{{t+k}})-1 "
        f"低于该标的在**训练窗**上滚动三日复合收益的 **{p}%** 分位；阈值与测试窗实现收益独立估计。"
    )


def crash_definition_label_h(lower_q: float, h: int) -> str:
    p = int(round(float(lower_q) * 100))
    hh = int(max(1, h))
    return (
        f"大跌（逐标的）：告警后连续 {hh} 个交易日的复合收益 R^({hh})=∏(1+r_{{t+k}})-1 "
        f"低于该标的在**训练窗**上滚动 {hh} 日复合收益的 **{p}%** 分位；阈值与测试窗实现收益独立估计。"
    )


def _tail_thresholds_from_pool(pool: np.ndarray, pct_high_to_low: int) -> Tuple[float, float]:
    """Given percentile defined on sorting from high->low (e.g., 90%), return (q_left, q_right)."""
    p = float(np.clip(int(pct_high_to_low), 50, 99)) / 100.0
    q_left = float(np.quantile(pool, 1.0 - p))
    q_right = float(np.quantile(pool, p))
    return q_left, q_right


def compute_train_baselines(
    *,
    rets: pd.DataFrame,
    r_train: pd.DataFrame,
    symbols: List[str],
    h: int,
    train_tail_days: int,
    crash_q_pct_high_to_low: int,
    std_q_pct: int,
    tail_q_pct: int,
) -> Dict[str, Any]:
    """Compute baselines from train rolling sequences, then take configured percentiles."""
    syms = [s for s in symbols if s in r_train.columns and s in rets.columns]
    hh = int(max(1, h))
    # Crash thresholds per symbol from train rolling Rh distribution (left tail)
    p = float(np.clip(int(crash_q_pct_high_to_low), 50, 99)) / 100.0
    lower_q = 1.0 - p
    crash_thr = train_per_symbol_crash_thresholds(r_train, syms, lower_q=lower_q, h=hh)

    # Tail thresholds from pooled train daily returns (last train_tail_days)
    train_pool = _pre_test_daily_pool(rets, r_train.index, syms, tail_days=int(train_tail_days))
    if train_pool.size >= 30:
        q_left, q_right = _tail_thresholds_from_pool(train_pool, int(tail_q_pct))
    else:
        q_left, q_right = float("nan"), float("nan")

    # Rolling baselines across train index: for each start t, use next h days (t..t+h-1)
    train_ix = r_train.index
    series_std: List[float] = []
    series_crash_ratio: List[float] = []
    series_tail_ratio: List[float] = []
    if len(train_ix) >= hh + 2 and syms:
        for t0 in range(0, len(train_ix) - hh):
            post_ix = train_ix[t0 : t0 + hh]
            # R^h per symbol
            Rh_vals: List[float] = []
            crash_hits = 0
            for sym in syms:
                s_post = rets.loc[post_ix, sym].astype(float)
                Rh = _compound_h_day(s_post, h=hh)
                if np.isfinite(Rh):
                    Rh_vals.append(Rh)
                thr = crash_thr.get(sym)
                if thr is not None and np.isfinite(Rh) and np.isfinite(float(thr)) and Rh < float(thr):
                    crash_hits += 1
            arr = np.asarray(Rh_vals, dtype=float)
            arr = arr[np.isfinite(arr)]
            if arr.size > 1:
                series_std.append(float(np.std(arr, ddof=1)))
            if syms:
                series_crash_ratio.append(float(crash_hits / max(len(syms), 1)))

            # Tail ratio: pooled daily returns across assets over the same h days
            if train_pool.size >= 30 and np.isfinite(q_left) and np.isfinite(q_right):
                block = rets.loc[post_ix, syms].to_numpy(dtype=float).ravel()
                block = block[np.isfinite(block)]
                if block.size:
                    frac_l = float(np.mean(block < q_left))
                    frac_r = float(np.mean(block > q_right))
                    series_tail_ratio.append(float(frac_l + frac_r))

    def _q(series: List[float], pct: int) -> float:
        a = np.asarray(series, dtype=float)
        a = a[np.isfinite(a)]
        if a.size < 8:
            return float("nan")
        return float(np.quantile(a, float(np.clip(int(pct), 50, 99)) / 100.0))

    return {
        "horizon_trading_days": hh,
        "train_tail_days": int(train_tail_days),
        "crash_q_pct_high_to_low": int(crash_q_pct_high_to_low),
        "std_q_pct": int(std_q_pct),
        "tail_q_pct": int(tail_q_pct),
        "crash_thresholds_Rh": crash_thr,
        "tail_left_thr": q_left,
        "tail_right_thr": q_right,
        "baseline_std_thr": _q(series_std, int(std_q_pct)),
        "baseline_crash_ratio_thr": _q(series_crash_ratio, int(std_q_pct)),  # reuse std_q_pct for ratio threshold
        "baseline_tail_ratio_thr": _q(series_tail_ratio, int(tail_q_pct)),
    }


def compute_post_window_metrics(
    *,
    rets: pd.DataFrame,
    test_ix: pd.DatetimeIndex,
    symbols: List[str],
    t0_row: Optional[int],
    h: int,
    crash_thresholds: Dict[str, float],
    tail_left_thr: float,
    tail_right_thr: float,
) -> Optional[Dict[str, Any]]:
    """Compute fixed-h post-window realized metrics after t0 (t0+1..t0+h)."""
    if t0_row is None:
        return None
    t0 = int(t0_row)
    hh = int(max(1, h))
    if t0 + hh >= len(test_ix):
        return {"error": "insufficient_post_rows", "t0_row": t0, "horizon_trading_days": hh}
    post_ix = test_ix[t0 + 1 : t0 + 1 + hh]
    syms = [s for s in symbols if s in rets.columns]

    per_sym_Rh: Dict[str, float] = {}
    per_sym_crash: Dict[str, bool] = {}
    for sym in syms:
        s_post = rets.loc[post_ix, sym].astype(float)
        Rh = _compound_h_day(s_post, h=hh)
        per_sym_Rh[sym] = float(Rh)
        thr = crash_thresholds.get(sym, float("nan"))
        per_sym_crash[sym] = bool(np.isfinite(Rh) and np.isfinite(thr) and Rh < float(thr))

    # cross-section std of Rh
    arr = np.asarray(list(per_sym_Rh.values()), dtype=float)
    arr = arr[np.isfinite(arr)]
    cs_std = float(np.std(arr, ddof=1)) if arr.size > 1 else float("nan")
    crash_ratio = float(np.mean([1.0 if per_sym_crash[s] else 0.0 for s in per_sym_crash])) if per_sym_crash else float("nan")

    # 5xN tail flags (daily, per asset) + per-symbol daily returns（用于 UI 侧搜索重绑定）
    tail_flags: List[List[int]] = []
    per_symbol_daily: Dict[str, List[float]] = {sym: [] for sym in syms}
    for d in post_ix:
        row = []
        for sym in syms:
            try:
                r = float(rets.loc[d, sym])
            except Exception:
                r = float("nan")
            per_symbol_daily[sym].append(float(r))
            hit = int(np.isfinite(r) and np.isfinite(tail_left_thr) and np.isfinite(tail_right_thr) and (r < tail_left_thr or r > tail_right_thr))
            row.append(hit)
        tail_flags.append(row)
    # pooled
    if np.isfinite(tail_left_thr) and np.isfinite(tail_right_thr) and syms:
        block = rets.loc[post_ix, syms].to_numpy(dtype=float).ravel()
        block = block[np.isfinite(block)]
        tail_ratio = float(np.mean((block < tail_left_thr) | (block > tail_right_thr))) if block.size else float("nan")
        left_ratio = float(np.mean(block < tail_left_thr)) if block.size else float("nan")
        right_ratio = float(np.mean(block > tail_right_thr)) if block.size else float("nan")
    else:
        tail_ratio, left_ratio, right_ratio = float("nan"), float("nan"), float("nan")

    return {
        "t0_row": t0,
        "t0_date": str(test_ix[t0].date()),
        "post_dates": [str(d.date()) for d in post_ix],
        "symbols": syms,
        "per_symbol_Rh": per_sym_Rh,
        "per_symbol_crash": per_sym_crash,
        "per_symbol_daily_returns": per_symbol_daily,
        "cross_section_std_Rh": cs_std,
        "crash_ratio": crash_ratio,
        "tail_flags_5xN": tail_flags,
        "tail_ratio": tail_ratio,
        "tail_left_ratio": left_ratio,
        "tail_right_ratio": right_ratio,
        "tail_left_thr": float(tail_left_thr) if np.isfinite(tail_left_thr) else None,
        "tail_right_thr": float(tail_right_thr) if np.isfinite(tail_right_thr) else None,
        "horizon_trading_days": hh,
    }


def _pre_test_daily_pool(
    rets: pd.DataFrame,
    train_ix: pd.DatetimeIndex,
    symbols: List[str],
    tail_days: int = 60,
) -> np.ndarray:
    """Pooled daily simple returns over last `tail_days` of train (all syms)."""
    if len(train_ix) == 0:
        return np.array([])
    tail_ix = train_ix[-min(tail_days, len(train_ix)) :]
    cols = [s for s in symbols if s in rets.columns]
    if not cols:
        return np.array([])
    block = rets.loc[tail_ix, cols].to_numpy(dtype=float).ravel()
    return block[np.isfinite(block)]


def panel_metrics_at_test_row(
    rets: pd.DataFrame,
    test_ix: pd.DatetimeIndex,
    symbols: List[str],
    t0_row: Optional[int],
    q_train: Dict[str, float],
    train_daily_pool: np.ndarray,
    h: int = 3,
) -> Optional[Dict[str, Any]]:
    """Chaos + tail metrics for h days after alarm row t0 (no portfolio weights)."""
    if t0_row is None:
        return None
    t0 = int(t0_row)
    if t0 + h >= len(test_ix):
        return {"error": "insufficient_post_rows", "t0_row": t0}

    post_ix = test_ix[t0 + 1 : t0 + 1 + h]
    per_sym: List[Dict[str, Any]] = []
    R3_list: List[float] = []
    daily_post: List[float] = []

    for sym in symbols:
        if sym not in rets.columns:
            continue
        s_post = rets.loc[post_ix, sym].astype(float)
        R3 = _compound_h_day(s_post, h=h)
        thr = float(q_train.get(sym, float("nan")))
        crash = bool(np.isfinite(R3) and np.isfinite(thr) and R3 < thr)
        # pre-alarm sigma: std of daily returns on test window strictly before t0, up to 20 days
        t_pre_start = max(0, t0 - 20)
        pre_ix = test_ix[t_pre_start:t0]
        pre_r = rets.loc[pre_ix, sym].dropna().astype(float) if len(pre_ix) else pd.Series(dtype=float)
        sig_pre = float(pre_r.std(ddof=1)) if len(pre_r) > 2 else float("nan")
        r1 = float(s_post.iloc[0]) if len(s_post) > 0 else float("nan")
        r2 = float(s_post.iloc[1]) if len(s_post) > 1 else float("nan")
        r3 = float(s_post.iloc[2]) if len(s_post) > 2 else float("nan")
        row_d = {
            "symbol": sym,
            "r_day1": r1,
            "r_day2": r2,
            "r_day3": r3,
            "R3_compound": R3,
            "train_q_threshold_R3": thr,
            "crash_hit": crash,
            "direction_R3_sign": int(np.sign(R3)) if np.isfinite(R3) else 0,
            "sigma_pre_20d_test": sig_pre,
        }
        per_sym.append(row_d)
        if np.isfinite(R3):
            R3_list.append(R3)
        for k in range(len(s_post)):
            daily_post.append(float(s_post.iloc[k]))

    arr = np.asarray(R3_list, dtype=float)
    arr = arr[np.isfinite(arr)]
    n_sym = len(arr)
    frac_down = float(np.mean(arr < 0.0)) if n_sym else float("nan")
    n_crash = int(sum(1 for r in per_sym if r.get("crash_hit")))
    frac_crash = float(n_crash / max(len(per_sym), 1)) if per_sym else float("nan")

    chaos = {
        "n_symbols_in_panel": len(per_sym),
        "frac_R3_negative": frac_down,
        "n_crash_hits": n_crash,
        "frac_crash_vs_train_q": frac_crash,
        "cross_section_std_R3": float(np.std(arr, ddof=1)) if arr.size > 1 else float("nan"),
        "mean_R3": float(np.mean(arr)) if arr.size else float("nan"),
        "median_R3": float(np.median(arr)) if arr.size else float("nan"),
        "min_R3": float(np.min(arr)) if arr.size else float("nan"),
        "max_R3": float(np.max(arr)) if arr.size else float("nan"),
    }

    post_pool = np.asarray(daily_post, dtype=float)
    post_pool = post_pool[np.isfinite(post_pool)]

    tail: Dict[str, Any] = {}
    if train_daily_pool.size >= 30 and post_pool.size >= 3:
        q05_pre = float(np.quantile(train_daily_pool, 0.05))
        q95_pre = float(np.quantile(train_daily_pool, 0.95))
        tail["train_tail_pool_n"] = int(train_daily_pool.size)
        tail["post_daily_pool_n"] = int(post_pool.size)
        tail["frac_post_daily_below_train_pooled_q05"] = float(
            np.mean(post_pool < q05_pre)
        )
        tail["frac_post_daily_above_train_pooled_q95"] = float(
            np.mean(post_pool > q95_pre)
        )
        tail["excess_kurtosis_train_tail_pooled_daily"] = _excess_kurtosis(train_daily_pool)
        tail["excess_kurtosis_post_h_daily_pooled"] = _excess_kurtosis(post_pool)
        tail["tail_thicken_vs_train"] = bool(
            np.isfinite(tail["excess_kurtosis_train_tail_pooled_daily"])
            and np.isfinite(tail["excess_kurtosis_post_h_daily_pooled"])
            and tail["excess_kurtosis_post_h_daily_pooled"]
            > tail["excess_kurtosis_train_tail_pooled_daily"] + 0.5
        )
    else:
        tail["note"] = "训练尾池或后窗样本不足，跳过尾部加厚对比。"

    return {
        "t0_row": t0,
        "t0_date": str(test_ix[t0].date()),
        "post_dates": [str(d.date()) for d in post_ix],
        "horizon_trading_days": h,
        "per_symbol": per_sym,
        "chaos_cross_section": chaos,
        "tail_pooled": tail,
    }


def build_post_alarm_realized_bundle(
    rets: pd.DataFrame,
    r_train: pd.DataFrame,
    test_ix: pd.DatetimeIndex,
    symbols: List[str],
    alarm_jsd: Optional[int],
    alarm_cos: Optional[int],
    lower_q: float = 0.05,
    tail_pre_days: int = 60,
) -> Dict[str, Any]:
    syms = [s for s in symbols if s in rets.columns]
    q_train = train_per_symbol_crash_thresholds(r_train, syms, lower_q=lower_q)
    train_pool = _pre_test_daily_pool(rets, r_train.index, syms, tail_days=tail_pre_days)
    label = crash_definition_label(lower_q)
    out: Dict[str, Any] = {
        "research_crash_definition_label": label,
        "research_post_jsd_realized": panel_metrics_at_test_row(
            rets, test_ix, syms, alarm_jsd, q_train, train_pool, h=3
        ),
        "research_post_cos_realized": panel_metrics_at_test_row(
            rets, test_ix, syms, alarm_cos, q_train, train_pool, h=3
        ),
    }
    return out


def build_fig41_verify_bundle(
    *,
    rets: pd.DataFrame,
    r_train: pd.DataFrame,
    test_ix: pd.DatetimeIndex,
    symbols: List[str],
    t0_row: Optional[int],
    focus_symbol: Optional[str],
    h: int = 5,
    crash_desc_rank_pct: int = 90,
    std_quantile_pct: int = 90,
    tail_quantile_pct: int = 90,
    train_tail_days: int = 60,
) -> Dict[str, Any]:
    """
    Fig4.1 固定 5 日窗预警成功验证（不展示 lead/t_ref/t_alarm；仅输出成功/较成功/失败）。

    分位定义：
    - crash_desc_rank_pct=90 表示“收益从高到低排序的 90%” → 左尾 10% 分位（阈值更严格）。
    - std/tail 分位为训练窗滚动序列的上分位阈值（越大越严格）。
    """
    hh = int(max(1, h))
    syms = [s for s in symbols if s in rets.columns]
    focus = focus_symbol if (focus_symbol in syms) else (syms[0] if syms else None)

    baselines = compute_train_baselines(
        rets=rets,
        r_train=r_train,
        symbols=syms,
        h=hh,
        train_tail_days=int(train_tail_days),
        crash_q_pct_high_to_low=int(crash_desc_rank_pct),
        std_q_pct=int(std_quantile_pct),
        tail_q_pct=int(tail_quantile_pct),
    )
    crash_thr = baselines.get("crash_thresholds_Rh") or {}
    ql = float(baselines.get("tail_left_thr")) if baselines.get("tail_left_thr") is not None else float("nan")
    qr = float(baselines.get("tail_right_thr")) if baselines.get("tail_right_thr") is not None else float("nan")

    post = compute_post_window_metrics(
        rets=rets,
        test_ix=test_ix,
        symbols=syms,
        t0_row=t0_row,
        h=hh,
        crash_thresholds=crash_thr,
        tail_left_thr=ql,
        tail_right_thr=qr,
    )
    if not isinstance(post, dict) or post.get("error"):
        return {
            "error": post.get("error") if isinstance(post, dict) else "missing_post",
            "focus_symbol": focus,
            "horizon_trading_days": hh,
        }

    # Focus symbol: R^(h) crash status vs per-symbol crash threshold
    focus_Rh = None
    focus_crash_thr = None
    focus_is_crash = None
    try:
        if focus and isinstance(post.get("per_symbol_Rh"), dict):
            focus_Rh = float(post["per_symbol_Rh"].get(focus))
        if focus:
            focus_crash_thr = float(crash_thr.get(focus))
        if focus_Rh is not None and focus_crash_thr is not None:
            if np.isfinite(float(focus_Rh)) and np.isfinite(float(focus_crash_thr)):
                focus_is_crash = bool(float(focus_Rh) < float(focus_crash_thr))
    except Exception:
        pass

    # Focus-symbol daily returns (t0+1..t0+h)
    focus_daily: List[float] = []
    focus_tail_left: List[int] = []
    focus_tail_right: List[int] = []
    if focus and post.get("post_dates"):
        # reconstruct timestamps from ISO strings
        for ds in (post.get("post_dates") or []):
            try:
                d = pd.Timestamp(ds)
                r = float(rets.loc[d, focus])
            except Exception:
                r = float("nan")
            focus_daily.append(float(r))
            focus_tail_left.append(int(np.isfinite(r) and np.isfinite(ql) and r < ql))
            focus_tail_right.append(int(np.isfinite(r) and np.isfinite(qr) and r > qr))

    # Focus-symbol tail ratios across the fixed 5-day window
    n_days = max(1, len(focus_daily))
    focus_tail_left_ratio = float(sum(focus_tail_left) / n_days) if focus_tail_left else float("nan")
    focus_tail_right_ratio = float(sum(focus_tail_right) / n_days) if focus_tail_right else float("nan")

    # Cross-section std on each time "face" k=1..h using compound R^(k) from t0+1..t0+k
    cs_std_by_k: List[float] = []
    if isinstance(post.get("post_dates"), list) and syms:
        post_dates = [pd.Timestamp(x) for x in (post.get("post_dates") or [])]
        for k in range(1, hh + 1):
            ix_k = post_dates[:k]
            Rh_vals: List[float] = []
            for sym in syms:
                try:
                    s_post = rets.loc[ix_k, sym].astype(float)
                except Exception:
                    continue
                Rh = _compound_h_day(s_post, h=k)
                if np.isfinite(Rh):
                    Rh_vals.append(float(Rh))
            arr = np.asarray(Rh_vals, dtype=float)
            arr = arr[np.isfinite(arr)]
            cs_std_by_k.append(float(np.std(arr, ddof=1)) if arr.size > 1 else float("nan"))

    # 3-dim traffic-light verdict
    std_val = post.get("cross_section_std_Rh")
    crash_ratio = post.get("crash_ratio")
    tail_ratio = post.get("tail_ratio")
    std_thr = baselines.get("baseline_std_thr")
    crash_ratio_thr = baselines.get("baseline_crash_ratio_thr")
    tail_ratio_thr = baselines.get("baseline_tail_ratio_thr")

    def _hit(v, thr) -> Optional[bool]:
        try:
            vf = float(v)
            tf = float(thr)
        except (TypeError, ValueError):
            return None
        if not (np.isfinite(vf) and np.isfinite(tf)):
            return None
        return bool(vf > tf)

    hit_std = _hit(std_val, std_thr)
    hit_crash = _hit(crash_ratio, crash_ratio_thr)
    hit_tail = _hit(tail_ratio, tail_ratio_thr)
    hits = [h for h in (hit_std, hit_crash, hit_tail) if h is True]
    n_hit = int(len(hits))
    # 方法论：3/3 → 成功；1–2/3 → 较成功；0 → 失败
    if n_hit >= 3:
        verdict = "成功"
    elif n_hit >= 1:
        verdict = "较成功"
    else:
        verdict = "失败"

    # Avoid accidental mojibake when displayed through some Windows console paths.
    try:
        verdict = verdict.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    except Exception:
        pass

    return {
        "horizon_trading_days": hh,
        "focus_symbol": focus,
        "baselines": baselines,
        "post": post,
        "focus_Rh": focus_Rh,
        "focus_crash_thr_Rh": focus_crash_thr,
        "focus_is_crash": focus_is_crash,
        "focus_daily_returns": focus_daily,
        "focus_tail_left_hits": focus_tail_left,
        "focus_tail_right_hits": focus_tail_right,
        "focus_tail_left_ratio": focus_tail_left_ratio,
        "focus_tail_right_ratio": focus_tail_right_ratio,
        "cross_section_std_by_k": cs_std_by_k,
        "crash_definition_label": crash_definition_label_h(1.0 - float(np.clip(int(crash_desc_rank_pct), 50, 99)) / 100.0, hh),
        "hits": {
            "std_above_baseline": hit_std,
            "crash_ratio_above_baseline": hit_crash,
            "tail_ratio_above_baseline": hit_tail,
            "n_hit": n_hit,
            "verdict": verdict,
        },
    }
