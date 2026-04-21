"""End-to-end pipeline: Phase0→1→2→3 + defense resolution."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, cast

import numpy as np
import pandas as pd

from ass1_core import daily_returns, load_bundle

from research.defense_state import DefenseLevel, any_adf_asset_failure, resolve_defense_level
from research.phase0 import run_phase0
from research.phase1 import run_phase1, structural_entropy
from research.phase2 import (
    _cross_section_mean_mu_per_day,
    run_phase2,
)
from research.phase3 import p0_pure_mc_median_cumulative_returns, run_phase3, sentiment_to_jump_params
from research.sentiment_calendar import TEST_WINDOW_MIN_DAYS, clamp_test_span_days
from research.sentiment_proxy import vader_st_series_kernel_smoothed_from_detail
from research.post_alarm_realized_metrics import build_post_alarm_realized_bundle, build_fig41_verify_bundle
from research.windowing import (
    resolve_dynamic_train_test_windows,
    resolve_regime_break_window,
    resolve_train_test_with_calendar_test_span,
)
from research.schemas import (
    DefensePolicyConfig,
    Phase0Input,
    Phase1Input,
    Phase2Input,
    Phase2Output,
    Phase3DefenseValidation,
    Phase3Input,
    PipelineSnapshot,
)
from research.state_manager import GlobalStateManager

logger = logging.getLogger(__name__)


def _resolve_universe_symbols(inp: Phase0Input, available: List[str]) -> Phase0Input:
    def map_sym(s: str) -> str:
        aliases = {"GLD": "AU0", "TSMC": "TSM"}
        if s in available:
            return s
        return aliases.get(s, s)

    tech = [map_sym(s) for s in inp.tech_symbols]
    hedge = [map_sym(s) for s in inp.hedge_symbols]
    safe = [map_sym(s) for s in inp.safe_symbols]
    bench = map_sym(inp.benchmark) if inp.benchmark not in available else inp.benchmark
    return inp.model_copy(
        update={
            "tech_symbols": [s for s in tech if s in available],
            "hedge_symbols": [s for s in hedge if s in available],
            "safe_symbols": [s for s in safe if s in available],
            "benchmark": bench if bench in available else (inp.benchmark if inp.benchmark in available else "SPY"),
        }
    )


def _early_april_2026_window(test_start: Any, test_end: Any) -> bool:
    """测试窗是否与 2026-04-01..15 相交（叙事锚点：4 月初非稳态）。"""
    try:
        from datetime import date as d

        a = pd.Timestamp(test_start).date()
        b = pd.Timestamp(test_end).date()
        return a <= d(2026, 4, 15) and b >= d(2026, 4, 1)
    except Exception:
        return False


def _custom_weights_for_symbols(
    weights_ui: Optional[Dict[str, float]], symbols: List[str]
) -> Dict[str, float]:
    """Map UI universe keys (e.g. TSMC, GLD) onto pipeline `symbols` (e.g. TSM, AU0); normalize to simplex."""
    if not symbols:
        return {}
    w_ui = weights_ui or {}
    out: Dict[str, float] = {}
    for s in symbols:
        v = float(w_ui.get(s, 0.0))
        if s == "TSM":
            v += float(w_ui.get("TSMC", 0.0))
        elif s == "AU0":
            v += float(w_ui.get("GLD", 0.0))
        else:
            v = float(w_ui.get(s, 0.0))
        out[s] = max(0.0, v)
    t = sum(out.values())
    if t < 1e-15:
        u = 1.0 / len(symbols)
        return {s: u for s in symbols}
    return {s: out[s] / t for s in symbols}


def _semantic_price_alarm_offsets(
    r_test: pd.DataFrame,
    symbols: List[str],
    st_dates: List[str],
    st_vals: List[float],
    tau_s_low: float,
) -> Tuple[Optional[int], Optional[int]]:
    """
    语义先验 vs 价格不稳：前者为测试窗内首次 S_t < τ_S_low 的日序号；
    后者为等权组合 5 日滚动波动率首次超过全窗 85% 分位的日序号。
    """
    if r_test.empty or not symbols:
        return None, None
    syms = [s for s in symbols if s in r_test.columns]
    if not syms:
        return None, None
    wb = np.ones(len(syms), dtype=float) / float(len(syms))
    r_eq = r_test[syms].to_numpy(dtype=float) @ wb
    n = int(len(r_eq))
    dmap = {str(d): float(v) for d, v in zip(st_dates or [], st_vals or [])}
    st_a = np.array([dmap.get(str(ix.date()), float("nan")) for ix in r_test.index], dtype=float)
    sem_row: Optional[int] = None
    if np.any(np.isfinite(st_a)):
        s_ff = pd.Series(st_a).ffill().bfill().to_numpy(dtype=float)
        thr_s = float(tau_s_low)
        for i in range(n):
            if float(s_ff[i]) < thr_s:
                sem_row = i
                break
    vol5 = pd.Series(r_eq, dtype=float).rolling(5, min_periods=3).std()
    thr_v = float(vol5.quantile(0.85)) if vol5.notna().any() else float("nan")
    price_row: Optional[int] = None
    if np.isfinite(thr_v) and thr_v > 0:
        for i in range(n):
            if i >= 4 and pd.notna(vol5.iloc[i]) and float(vol5.iloc[i]) > thr_v:
                price_row = i
                break
    return sem_row, price_row


def _test_index_to_row(test_ix: pd.DatetimeIndex, ts: pd.Timestamp) -> Optional[int]:
    try:
        return int(list(test_ix).index(ts))
    except ValueError:
        return None


def _first_rolling_h_struct_alarm_row(
    rets: pd.DataFrame,
    test_ix: pd.DatetimeIndex,
    symbols: List[str],
    tau_h1: float,
    window: int = 21,
) -> Optional[int]:
    """First test-row j where rolling covariance structural entropy on [t-window+1, t] falls below τ_h1."""
    syms = [s for s in symbols if s in rets.columns]
    if len(syms) < 2 or len(test_ix) == 0:
        return None
    for j, d in enumerate(test_ix):
        try:
            loc = rets.index.get_loc(d)
        except KeyError:
            continue
        if isinstance(loc, slice):
            loc = int(loc.start) if loc.start is not None else None
        if loc is None:
            continue
        lo = max(0, int(loc) - window + 1)
        sub = rets.iloc[lo : int(loc) + 1][syms].dropna(how="any")
        if len(sub) < window:
            continue
        C = sub.to_numpy(dtype=float)
        if C.shape[0] < 2 or C.shape[1] < 2:
            continue
        cov = np.cov(C, rowvar=False)
        if not np.all(np.isfinite(cov)):
            continue
        h = structural_entropy(cov)
        if h < float(tau_h1):
            return j
    return None


def _first_rolling_jsd_stress_row(
    daily_tri: List[float],
    stress_window: int,
    jsd_baseline_mean: float,
    k_jsd: float,
    *,
    baseline_eps: float,
) -> Optional[int]:
    """首次滚动 W=stress_window 日三角 JSD 均值超阈值的测试窗行号（0 起）。

    口径与 FigX.5 图上「滚动三角均值（告警口径）」白实线一致；W 取自
    `DefensePolicyConfig.semantic_cosine_window`，与 FigX.6 语义–数值余弦共用。
    """
    eps = float(max(baseline_eps, 1e-15))
    n = len(daily_tri)
    w = max(1, int(stress_window))
    if n < max(2, w):
        return None
    for t in range(w - 1, n):
        roll = float(np.mean(daily_tri[t + 1 - w : t + 1]))
        if roll > float(k_jsd) * max(float(jsd_baseline_mean), eps):
            return t
    return None


def _first_credibility_tau_l1_row(
    daily_tri: List[float], policy: DefensePolicyConfig, coverage_penalty: float
) -> Optional[int]:
    alpha = float(max(policy.credibility_baseline_jsd_scale, 1e-9))
    cmin = float(policy.credibility_score_min)
    cmax = float(policy.credibility_score_max)
    if cmin >= cmax:
        cmin, cmax = -0.5, 1.0
    pen = float(max(0.0, coverage_penalty))
    for t, tri in enumerate(daily_tri):
        base = float(1.0 / (1.0 + alpha * float(tri)))
        cred = float(np.clip(base - pen, cmin, cmax))
        if cred <= float(policy.tau_l1):
            return t
    return None


def _rolling_cosine_series(
    a: np.ndarray,
    b: np.ndarray,
    window: int,
) -> List[float]:
    """Per-day Pearson cosine similarity over a rolling window of length W.

    Returns a list of length len(a); entries before the first full window are NaN.
    """
    n = int(min(len(a), len(b)))
    window = int(max(2, window))
    out: List[float] = [float("nan")] * n
    for k in range(window - 1, n):
        sa = a[k - window + 1 : k + 1]
        sb = b[k - window + 1 : k + 1]
        na = float(np.linalg.norm(sa))
        nb = float(np.linalg.norm(sb))
        if na < 1e-15 or nb < 1e-15:
            continue
        out[k] = float(np.dot(sa, sb) / (na * nb))
    return out


def _first_semantic_cosine_negative_row(
    st_arr: np.ndarray,
    num_arr: np.ndarray,
    window: int,
) -> Optional[int]:
    """First test-row index where rolling-window cosine similarity drops below 0."""
    cos_series = _rolling_cosine_series(st_arr, num_arr, window)
    for k, v in enumerate(cos_series):
        if np.isfinite(v) and v < 0.0:
            return k
    return None


def _lead_vs_ref(ref_row: Optional[int], alarm_row: Optional[int]) -> Optional[int]:
    if ref_row is None or alarm_row is None:
        return None
    return int(ref_row - int(alarm_row))


def _build_failure_verdict(
    *,
    ref_full: Optional[int],
    ref_lbl: str,
    leads: List[Tuple[str, Optional[int]]],
    ew_lo: int,
    ew_hi: int,
) -> str:
    """Render the human-readable early-warning verdict for the research bundle.

    Three branches: missing reference row → narrative-only string; reference row
    present and at least one signal lands inside ``[ew_lo, ew_hi]`` → "hit" line;
    otherwise → exploratory line listing each lead.
    """
    if ref_full is None:
        return (
            f"{ref_lbl}；在**完整测试行序**上未映射到参照日（常见于测试行含缺失收益被 Shadow 丢弃）。"
            "各信号**首次**告警行见字段 `research_alarm_day_*`。"
        )
    hits = [name for name, ld in leads if ld is not None and ew_lo <= ld <= ew_hi]
    if hits:
        return (
            f"参照行为测试窗第 **{ref_full}** 行（{ref_lbl}）。"
            f"以下指标较参照 **提前 1～5** 行（交易日）触发：**{'、'.join(hits)}**。"
        )
    parts: List[str] = []
    for name, ld in leads:
        if ld is not None:
            parts.append(f"{name}：提前 **{ld}** 行")
        else:
            parts.append(f"{name}：—")
    tail = "；".join(parts)
    return (
        f"参照行 **{ref_full}**。{tail}。"
        "尚未满足「提前量在 1～5 行」的强口径；可作探索性证据并结合更长窗复核。"
    )


def _attach_post_alarm_research_artifacts(
    out: Dict[str, Any],
    *,
    rets: pd.DataFrame,
    r_train: pd.DataFrame,
    test_ix: pd.DatetimeIndex,
    symbols: List[str],
    syms_use: List[str],
    pol: DefensePolicyConfig,
    alarm_jsd: Optional[int],
    alarm_cos: Optional[int],
) -> None:
    """Mutate ``out`` with chaos-tail + fig41 verification bundles.

    Each external builder call is wrapped in its own ``try/except`` so a failure
    in either does not abort the rest of the research bundle (matches legacy
    behaviour exactly — both blocks just log a warning and continue).
    """
    try:
        chaos_tail = build_post_alarm_realized_bundle(
            rets=rets,
            r_train=r_train,
            test_ix=test_ix,
            symbols=syms_use,
            alarm_jsd=alarm_jsd,
            alarm_cos=alarm_cos,
            lower_q=0.05,
            tail_pre_days=60,
        )
        out.update(chaos_tail)
    except Exception as exc:
        logger.warning("post_alarm_realized_metrics skipped: %s", exc, exc_info=True)
    try:
        _focus = (symbols[0] if symbols else None)
        _common = dict(
            rets=rets,
            r_train=r_train,
            test_ix=test_ix,
            symbols=syms_use,
            focus_symbol=_focus,
            h=5,
            crash_desc_rank_pct=int(getattr(pol, "verify_crash_quantile_pct", 90) or 90),
            std_quantile_pct=int(getattr(pol, "verify_std_quantile_pct", 90) or 90),
            tail_quantile_pct=int(getattr(pol, "verify_tail_quantile_pct", 90) or 90),
            train_tail_days=int(getattr(pol, "verify_train_tail_days", 60) or 60),
        )
        # 1) 既有 fig41_verify：更早 t0（兼容下游），不要改
        t0_earlier: Optional[int] = None
        if alarm_jsd is not None and alarm_cos is not None:
            t0_earlier = int(min(int(alarm_jsd), int(alarm_cos)))
        elif alarm_jsd is not None:
            t0_earlier = int(alarm_jsd)
        elif alarm_cos is not None:
            t0_earlier = int(alarm_cos)
        out["fig41_verify"] = build_fig41_verify_bundle(t0_row=t0_earlier, **_common)
        # 2) 新增双信号 verify（仅添加字段；老调用方无感）
        out["fig41_verify_mm"] = build_fig41_verify_bundle(
            t0_row=(int(alarm_jsd) if alarm_jsd is not None else None), **_common,
        )
        out["fig41_verify_mv"] = build_fig41_verify_bundle(
            t0_row=(int(alarm_cos) if alarm_cos is not None else None), **_common,
        )
    except Exception as exc:
        logger.warning("fig41_verify skipped: %s", exc, exc_info=True)


def _failure_identification_research(
    *,
    rets: pd.DataFrame,
    r_train: pd.DataFrame,
    test_ix: pd.DatetimeIndex,
    symbols: List[str],
    p2: Phase2Output,
    pol: DefensePolicyConfig,
    st_series: Optional[pd.Series],
    r_test: pd.DataFrame,
    price_off_rtest: Optional[int],
) -> Dict[str, Any]:
    """
    Validate early-warning claims: compare first alarm rows (structure / JSD / credibility / cosine)
    to a reference stress day (price volatility spike), all on the Phase2 test-row timeline.
    """
    ref_lbl = "等权组合 5 日波动率首次高于全窗 85% 分位（与语义先验卡 price_off 同源，映射到测试窗行序）"
    daily_tri = list(getattr(p2, "test_daily_triangle_jsd_mean", None) or [])
    n = len(daily_tri)
    if n == 0 or len(test_ix) != n:
        return {
            "research_failure_ref_label": ref_lbl,
            "research_failure_early_warning_verdict": "缺少逐日三角 JSD 序列或与测试窗长度不一致，跳过失效提前量验证。",
            "fig41_ew_ref_test_row": None,
            "fig41_ew_ref_date_iso": None,
            "fig41_ew_jsd_alarm_row": None,
            "fig41_ew_cos_alarm_row": None,
            "fig41_ew_lead_effective_lo": 1,
            "fig41_ew_lead_effective_hi": 5,
        }

    ref_full: Optional[int] = None
    if price_off_rtest is not None and len(r_test.index) > int(price_off_rtest):
        d0 = r_test.index[int(price_off_rtest)]
        ref_full = _test_index_to_row(test_ix, d0)

    syms_use = [s for s in symbols if s in rets.columns]
    alarm_h = _first_rolling_h_struct_alarm_row(rets, test_ix, syms_use, float(pol.tau_h1))

    alarm_jsd = _first_rolling_jsd_stress_row(
        daily_tri,
        int(getattr(pol, "semantic_cosine_window", 5) or 5),
        float(p2.jsd_baseline_mean),
        float(pol.k_jsd),
        baseline_eps=float(getattr(pol, "jsd_baseline_eps", 1e-9) or 1e-9),
    )
    alarm_cred = _first_credibility_tau_l1_row(daily_tri, pol, float(p2.credibility_coverage_penalty))

    alarm_cos: Optional[int] = None
    if st_series is not None and len(p2.test_forecast_dates) == n:
        cos_win = int(getattr(pol, "semantic_cosine_window", 5))
        cal_idx = [pd.Timestamp(x) for x in p2.test_forecast_dates]
        st_a = (
            st_series.reindex(cal_idx).ffill().bfill().to_numpy(dtype=float)
            if len(st_series)
            else np.array([])
        )
        # Use shadow-optimal μ cross-section mean as the numeric side
        best_mu_arr = np.array(list(p2.test_daily_best_model_mu_mean), dtype=float)
        best_mu_arr = pd.Series(best_mu_arr).ffill().bfill().to_numpy(dtype=float)
        if st_a.size == n and best_mu_arr.size == n:
            alarm_cos = _first_semantic_cosine_negative_row(st_a, best_mu_arr, cos_win)

    lead_h = _lead_vs_ref(ref_full, alarm_h)
    lead_j = _lead_vs_ref(ref_full, alarm_jsd)
    lead_c = _lead_vs_ref(ref_full, alarm_cred)
    lead_o = _lead_vs_ref(ref_full, alarm_cos)

    leads: List[Tuple[str, Optional[int]]] = [
        ("结构熵滚动低于 τ_h1", lead_h),
        ("三角 JSD 动态应力", lead_j),
        ("可信度代理 ≤ τ_L1", lead_c),
        ("语义–数值滚动余弦 < 0", lead_o),
    ]
    _ew_lo, _ew_hi = 1, 5
    verdict = _build_failure_verdict(
        ref_full=ref_full, ref_lbl=ref_lbl, leads=leads, ew_lo=_ew_lo, ew_hi=_ew_hi,
    )

    _ref_iso: Optional[str] = None
    if ref_full is not None and ref_full < len(test_ix):
        try:
            _ref_iso = str(pd.Timestamp(test_ix[ref_full]).date())
        except Exception:
            _ref_iso = None

    out = {
        "research_failure_ref_label": ref_lbl,
        "research_alarm_day_rolling_h_struct": alarm_h,
        "research_alarm_day_rolling_jsd_stress": alarm_jsd,
        "research_alarm_day_credibility_l1": alarm_cred,
        "research_alarm_day_semantic_cosine_negative": alarm_cos,
        "research_lead_ref_vs_h_struct": lead_h,
        "research_lead_ref_vs_jsd_stress": lead_j,
        "research_lead_ref_vs_credibility": lead_c,
        "research_lead_ref_vs_semantic_cosine": lead_o,
        "research_failure_early_warning_verdict": verdict,
        # Fig4.1 主栏可视化专用（与叙事/侧栏字段语义独立存储，便于单独迭代）
        "fig41_ew_ref_test_row": ref_full,
        "fig41_ew_ref_date_iso": _ref_iso,
        "fig41_ew_jsd_alarm_row": alarm_jsd,
        "fig41_ew_cos_alarm_row": alarm_cos,
        "fig41_ew_lead_effective_lo": _ew_lo,
        "fig41_ew_lead_effective_hi": _ew_hi,
    }
    _attach_post_alarm_research_artifacts(
        out,
        rets=rets, r_train=r_train, test_ix=test_ix,
        symbols=symbols, syms_use=syms_use, pol=pol,
        alarm_jsd=alarm_jsd, alarm_cos=alarm_cos,
    )
    return out


def _shadow_curves(
    returns: pd.DataFrame,
    w_blind: Dict[str, float],
    w_fused: Dict[str, float],
    test_mask: pd.Series,
) -> Tuple[List[float], List[float], float, float]:
    """Cumulative return curves (simple) for shadow box."""
    r = returns.loc[test_mask].dropna(how="any")
    syms = [s for s in r.columns if s in w_blind and s in w_fused]
    if not syms:
        return [], [], 0.0, 0.0
    wb = np.array([w_blind.get(s, 0.0) for s in syms])
    wf = np.array([w_fused.get(s, 0.0) for s in syms])
    wb = wb / (wb.sum() or 1.0)
    wf = wf / (wf.sum() or 1.0)
    # Use compound price relatives so MDD formula (peak-trough)/peak is valid
    port_b_price = np.cumprod(1.0 + r[syms].to_numpy() @ wb)
    port_f_price = np.cumprod(1.0 + r[syms].to_numpy() @ wf)

    def mdd(price: np.ndarray) -> float:
        if len(price) == 0:
            return 0.0
        peak = np.maximum.accumulate(price)
        dd = (peak - price) / np.maximum(peak, 1e-12)
        return float(np.max(dd))

    # Convert price relatives back to cumulative-return decimals for the chart
    port_b = (port_b_price - 1.0).tolist()
    port_f = (port_f_price - 1.0).tolist()
    return port_b, port_f, mdd(port_b_price), mdd(port_f_price)


class _TestSentimentResolution(NamedTuple):
    """Result of resolving the kernel-smoothed S_t path for the test window.

    The ``meta_updates`` dict is what the caller merges into ``Phase0.meta``
    (keys: ``test_sentiment_st`` (conditional), ``defense_sentiment_min_st``,
    ``sentiment_st_kernel``).
    """

    sentiment_effective: float
    sentiment_for_defense: float
    mc_st_path: Optional[List[float]]
    test_st_series: Optional[pd.Series]
    test_st_list: List[float]
    test_st_dates: List[str]
    meta_updates: Dict[str, Any]


def _resolve_test_sentiment_path(
    *,
    sentiment_score: float,
    sentiment_detail: Optional[Dict[str, Any]],
    pol: DefensePolicyConfig,
    rets_index_test: pd.DatetimeIndex,
    test_start: pd.Timestamp,
    test_end: pd.Timestamp,
    n_test_td: int,
) -> "_TestSentimentResolution":
    """Resolve the kernel-smoothed sentiment path S_t for the test window.

    Pure orchestration: calls into ``vader_st_series_kernel_smoothed_from_detail``
    when ``sentiment_detail`` is provided; otherwise returns a minimal bundle
    using the scalar ``sentiment_score``. On any failure inside the smoother,
    silently falls back to the scalar path (matches legacy try/except shape).
    """
    import math as _math

    sentiment_effective = float(sentiment_score)
    sentiment_for_defense = float(sentiment_score)
    test_st_list: List[float] = []
    test_st_dates: List[str] = []
    mc_st_path: Optional[List[float]] = None
    test_st_series: Optional[pd.Series] = None
    halflife = float(getattr(pol, "sentiment_halflife_days", 2.0) or 2.0)
    # v3 warmup：floor=60 日历天，再按测试窗长度与半衰期动态放大，使训练尾部新闻
    # 进入 H_t 记忆窗口、消除 prefix 常量段。向下传给 vader_st_series_kernel_smoothed_from_detail。
    warmup_days_eff = max(
        60,
        int(n_test_td) * 2 if n_test_td and n_test_td > 0 else 60,
        int(_math.ceil(3.0 * halflife)),
    )

    # Diagnostic: always print the shape of the sentiment_detail that the
    # pipeline is about to consume. This is the single source of truth for
    # "is the news-fetched detail actually reaching the S_t builder?".
    try:
        if isinstance(sentiment_detail, dict):
            _hl = sentiment_detail.get("headlines") or []
            _src = str(sentiment_detail.get("source") or "?")
            _score = sentiment_detail.get("score")
            _pub_set = set()
            _pub_none = 0
            for _r in _hl:
                _p = str((_r or {}).get("published") or "")[:10]
                if _p:
                    _pub_set.add(_p)
                else:
                    _pub_none += 1
            _pub_sorted = sorted(_pub_set)
            print(
                f"[S_t:in] sentiment_detail source={_src} score={_score} "
                f"n_headlines={len(_hl)} published_none={_pub_none} "
                f"unique_pub_days={len(_pub_sorted)} "
                f"pub_range=({_pub_sorted[0] if _pub_sorted else None},"
                f"{_pub_sorted[-1] if _pub_sorted else None}) "
                f"test_window=({test_start.date()},{test_end.date()}) "
                f"warmup_days={warmup_days_eff} "
                f"halflife={halflife}",
                flush=True,
            )
        else:
            print(
                f"[S_t:in] sentiment_detail is NOT a dict "
                f"(type={type(sentiment_detail).__name__}, value_repr={repr(sentiment_detail)[:120]}) "
                f"test_window=({test_start.date()},{test_end.date()}) n_test_td={n_test_td}",
                flush=True,
            )
    except Exception:
        pass

    st_test: Optional[pd.Series] = None
    if sentiment_detail is not None and n_test_td > 0:
        try:
            _sd = cast(Dict[str, Any], sentiment_detail)
            _penalty = float(_sd.get("penalty") or 0.0)
            _boost = float(_sd.get("severity_boost") or 0.0)
            st_test = vader_st_series_kernel_smoothed_from_detail(
                _sd,
                rets_index_test,
                test_start_cal=test_start.date(),
                test_end_cal=test_end.date(),
                fallback=float(sentiment_score),
                halflife_days=halflife,
                warmup_days=warmup_days_eff,
                penalty=_penalty,
                severity_boost=_boost,
            )
        except Exception as exc:
            logger.warning(
                "S_t kernel-smoothed series failed (%s); using scalar sentiment only.",
                exc,
                exc_info=True,
            )
            st_test = None

    meta_updates: Dict[str, Any] = {}
    # 透传 sentiment_proxy 的 constant-trap 诊断标记（若有）— 让 UI 能区分
    # 真信号 vs 合成兜底序列。
    try:
        _trace_obj = (sentiment_detail or {}).get("_st_trace") if isinstance(sentiment_detail, dict) else None
        if isinstance(_trace_obj, dict):
            meta_updates["sentiment_st_trace"] = dict(_trace_obj)
    except Exception:
        pass
    if st_test is not None and len(st_test) > 0:
        sentiment_effective = float(st_test.iloc[-1])
        test_st_list = [float(x) for x in st_test.tolist()]
        test_st_dates = [str(i.date()) for i in st_test.index]
        vals = np.asarray(st_test, dtype=float)
        vals = vals[np.isfinite(vals)]
        if vals.size > 0:
            sentiment_for_defense = float(np.min(vals))
        # constant-detection: 标记 S_t 序列是否近似常数（极差 < 1e-6）
        try:
            if vals.size > 1:
                meta_updates["sentiment_st_is_constant"] = bool(
                    float(np.ptp(vals)) < 1e-6
                )
        except Exception:
            pass
        # Even when the series length is not a perfect match (due to calendar/test span quirks),
        # still expose the path for UI and allow Phase 2 to reindex/align for cosine computation.
        test_st_series = st_test
        meta_updates["test_sentiment_st"] = {"dates": test_st_dates, "values": test_st_list}
        if len(st_test) == n_test_td:
            mc_st_path = [float(st_test.iloc[i]) for i in range(n_test_td)]
    meta_updates["defense_sentiment_min_st"] = sentiment_for_defense
    # ── Always-on visibility: the user-reported "flat line" case is easier to
    # diagnose when the actual series stats land in the console. Use ``print``
    # (not ``logger.info``) because ``dash_app/app.py`` never calls
    # ``logging.basicConfig``, so the root logger sits at WARNING by default
    # and INFO messages would be silently swallowed.
    try:
        if test_st_list:
            _arr = np.asarray(test_st_list, dtype=float)
            _arr = _arr[np.isfinite(_arr)]
            if _arr.size > 0:
                _head = [round(float(x), 4) for x in _arr[:5].tolist()]
                _tail = [round(float(x), 4) for x in _arr[-5:].tolist()]
                print(
                    f"[S_t] n={int(_arr.size)} "
                    f"min={float(_arr.min()):.4f} "
                    f"max={float(_arr.max()):.4f} "
                    f"ptp={float(_arr.max() - _arr.min()):.4f} "
                    f"mean={float(_arr.mean()):.4f} "
                    f"is_constant={bool(meta_updates.get('sentiment_st_is_constant', False))} "
                    f"head={_head} tail={_tail} "
                    f"trace={meta_updates.get('sentiment_st_trace')}",
                    flush=True,
                )
        else:
            print(
                f"[S_t] series empty — "
                f"sentiment_detail={'provided' if sentiment_detail is not None else 'None'} "
                f"n_test_td={int(n_test_td)}",
                flush=True,
            )
    except Exception:
        pass
    _sd_for_meta = sentiment_detail if isinstance(sentiment_detail, dict) else None
    meta_updates["sentiment_st_kernel"] = {
        "method": "kernel_smoothed_exponential_v3_1_dayrich_tanh",
        "halflife_days": halflife,
        "alpha": 1.0,
        "beta": 0.2,
        "offset_scale": 0.10,
        "warmup_days": int(warmup_days_eff),
        "normalize_kernel": True,
        "soft_clip": "tanh",
        "penalty": float((_sd_for_meta or {}).get("penalty") or 0.0) if _sd_for_meta else 0.0,
        "severity_boost": float((_sd_for_meta or {}).get("severity_boost") or 0.0) if _sd_for_meta else 0.0,
        "vader_avg": float((_sd_for_meta or {}).get("vader_avg") or 0.0) if _sd_for_meta else 0.0,
        "n_headlines": int((_sd_for_meta or {}).get("n_headlines") or 0) if _sd_for_meta else 0,
    }
    return _TestSentimentResolution(
        sentiment_effective=sentiment_effective,
        sentiment_for_defense=sentiment_for_defense,
        mc_st_path=mc_st_path,
        test_st_series=test_st_series,
        test_st_list=test_st_list,
        test_st_dates=test_st_dates,
        meta_updates=meta_updates,
    )


def _build_mu_cov_hist(
    *,
    rets: pd.DataFrame,
    train_mask: pd.Series,
    symbols: List[str],
    p2: Phase2Output,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Assemble per-symbol mu (best-model lookup w/ historical-mean fallback),
    covariance (diagonal-clipped to 1e-10), and a historical sample matrix
    for Monte Carlo. Pure numerics; no I/O.

    If the empirically observed sample is too short (<30 rows after dropping
    NaNs), falls back to a 200-row Gaussian draw from ``(mu, cov)`` (legacy
    behaviour, deterministic via ``rng=1``).
    """
    hist_mu = rets.loc[train_mask].mean()
    mu = np.array(
        [
            p2.model_mu.get(p2.best_model_per_symbol.get(s, "naive"), {}).get(
                s, float(hist_mu.get(s, 0.0))
            )
            for s in symbols
        ],
        dtype=float,
    )
    cov = (
        rets.loc[train_mask]
        .cov()
        .reindex(symbols)
        .reindex(columns=symbols)
        .fillna(0.0)
        .to_numpy(dtype=float)
        .copy()
    )
    np.fill_diagonal(cov, np.maximum(np.diag(cov), 1e-10))

    hist = rets.loc[train_mask].dropna(how="any").to_numpy(dtype=float)
    if hist.shape[0] < 30:
        hist = np.random.default_rng(1).multivariate_normal(mu, cov, size=200)
    return mu, cov, hist


def _build_extra_research_bundle(
    *,
    p2: Phase2Output,
    pol: DefensePolicyConfig,
    sentiment_for_defense: float,
    sem_off: Optional[int],
    price_off: Optional[int],
    lead_days: Optional[int],
    test_start: pd.Timestamp,
    test_end: pd.Timestamp,
    eff_scenario_step: Optional[int],
    fail_extra: Dict[str, Any],
) -> Dict[str, Any]:
    """Compose the ``extra_research`` payload merged into Phase3.defense_validation."""
    extra: Dict[str, Any] = {
        "research_consistency_score": float(p2.consistency_score),
        "research_tau_l2": float(pol.tau_l2),
        "research_tau_l1": float(pol.tau_l1),
        "research_defense_sentiment_min_st": float(sentiment_for_defense),
        "research_tau_s_low": float(pol.tau_s_low),
        "research_semantic_numeric_divergence": bool(
            getattr(p2, "logic_break_semantic_cosine_negative", False)
        ),
        "research_jsd_stress": bool(p2.jsd_stress),
        "research_prob_full_pipeline_failure": bool(
            getattr(p2, "prob_full_pipeline_failure", False)
        ),
        "research_semantic_alarm_day_offset": sem_off,
        "research_price_instability_day_offset": price_off,
        "research_semantic_lead_trading_days": lead_days,
        "research_test_window_label": f"{pd.Timestamp(test_start).date()} — {pd.Timestamp(test_end).date()}",
        "research_scenario_inject_step": int(eff_scenario_step)
        if eff_scenario_step is not None
        else None,
        "research_early_april_2026_window": _early_april_2026_window(test_start, test_end),
    }
    extra.update(fail_extra)
    return extra


def run_pipeline(
    json_path: Optional[str] = None,
    phase0_in: Optional[Phase0Input] = None,
    policy: Optional[DefensePolicyConfig] = None,
    sentiment_score: float = -0.1,
    sentiment_detail: Optional[Dict[str, Any]] = None,
    state: Optional[GlobalStateManager] = None,
    scenario_inject_step: Optional[int] = None,
    scenario_inject_impact: float = -0.12,
    custom_portfolio_weights: Optional[Dict[str, float]] = None,
) -> PipelineSnapshot:
    base = os.path.dirname(os.path.abspath(__file__))
    json_path = json_path or os.path.join(os.path.dirname(base), "data.json")
    bundle = load_bundle(json_path)
    close = bundle.close_universe.sort_index()
    available = list(close.columns)

    p0i = phase0_in or Phase0Input()
    p0i = _resolve_universe_symbols(p0i, available)
    pol = policy or DefensePolicyConfig()

    symbols = [s for s in (p0i.tech_symbols + p0i.hedge_symbols + p0i.safe_symbols) if s in close.columns]
    if p0i.benchmark in close.columns and p0i.benchmark not in symbols:
        symbols = list(dict.fromkeys(symbols + [p0i.benchmark]))

    rets = daily_returns(close[symbols]).dropna(how="all")

    live_detail = bool(
        isinstance(sentiment_detail, dict) and sentiment_detail.get("source") == "live"
    )
    if live_detail:
        _raw_span = int(sentiment_detail.get("effective_test_span_days") or 0)
        span_cal = clamp_test_span_days(_raw_span) if _raw_span > 0 else 0
    else:
        span_cal = 0

    # Dynamic windows: optional calendar test span from live news meta (T in [30, 50])
    if live_detail and span_cal >= TEST_WINDOW_MIN_DAYS:
        train_start, train_end, test_start, test_end = resolve_train_test_with_calendar_test_span(
            rets.index,
            template_train_start=p0i.train_start,
            template_train_end=p0i.train_end,
            template_test_start=p0i.test_start,
            template_test_end=p0i.test_end,
            calendar_test_span_days=span_cal,
        )
    else:
        train_start, train_end, test_start, test_end = resolve_dynamic_train_test_windows(
            rets.index,
            template_train_start=p0i.train_start,
            template_train_end=p0i.train_end,
            template_test_start=p0i.test_start,
            template_test_end=p0i.test_end,
        )
    train_mask = (rets.index >= train_start) & (rets.index <= train_end)
    test_mask = (rets.index >= test_start) & (rets.index <= test_end)
    test_ix = rets.index[test_mask]
    rb_s, rb_e = resolve_regime_break_window(
        rets.index, p0i.regime_break_start, p0i.regime_break_end, test_ix
    )
    p0i = p0i.model_copy(
        update={
            "train_start": str(train_start.date()),
            "train_end": str(train_end.date()),
            "test_start": str(test_start.date()),
            "test_end": str(test_end.date()),
            "regime_break_start": str(rb_s.date()),
            "regime_break_end": str(rb_e.date()),
        }
    )

    p0 = run_phase0(close, p0i)
    # Store resolved window info for UI
    _meta = dict(p0.meta or {})
    _meta["resolved_windows"] = {
        "train_start": str(train_start.date()),
        "train_end": str(train_end.date()),
        "test_start": str(test_start.date()),
        "test_end": str(test_end.date()),
    }
    n_test_td = int(test_mask.sum())
    _st_res = _resolve_test_sentiment_path(
        sentiment_score=sentiment_score,
        sentiment_detail=sentiment_detail,
        pol=pol,
        rets_index_test=rets.index[test_mask],
        test_start=test_start,
        test_end=test_end,
        n_test_td=n_test_td,
    )
    sentiment_effective = _st_res.sentiment_effective
    sentiment_for_defense = _st_res.sentiment_for_defense
    test_st_list = _st_res.test_st_list
    test_st_dates = _st_res.test_st_dates
    mc_st_path = _st_res.mc_st_path
    test_st_series_p2 = _st_res.test_st_series
    _meta.update(_st_res.meta_updates)
    p0 = p0.model_copy(update={"meta": _meta})

    close_train = close.loc[
        (close.index >= train_start) & (close.index <= train_end),
        [c for c in symbols if c in close.columns],
    ]

    p1i = Phase1Input(symbols=symbols, sentiment_score=sentiment_effective)
    p1 = run_phase1(rets.loc[train_mask], p1i, pol, close_train=close_train)

    tr_ix = rets.loc[train_mask].index
    sent_series = pd.Series(np.linspace(sentiment_effective, sentiment_effective, len(tr_ix)), index=tr_ix)

    p2i = Phase2Input(
        symbols=symbols,
        jsd_baseline_window=int(getattr(pol, "semantic_cosine_window", 5) or 5),
    )
    p2 = run_phase2(
        rets, train_mask, test_mask, p2i, pol,
        sentiment_series=sent_series,
        close=close,
        test_st_series=test_st_series_p2,
    )

    level = resolve_defense_level(
        consistency=p2.consistency_score,
        sentiment=sentiment_for_defense,
        h_struct=p1.h_struct,
        adf_asset_failure=any_adf_asset_failure(p1.diagnostics),
        jsd_stress=p2.jsd_stress,
        policy=pol,
        prob_full_pipeline_failure=bool(getattr(p2, "prob_full_pipeline_failure", False)),
        semantic_numeric_divergence=bool(
            getattr(p2, "logic_break_semantic_cosine_negative", False)
        ),
    )

    mu, cov, hist = _build_mu_cov_hist(rets=rets, train_mask=train_mask, symbols=symbols, p2=p2)

    jp, ji = sentiment_to_jump_params(sentiment_effective)

    # MC horizon = actual test-period trading days; default scenario step ~30 (≈ early March 2026)
    test_trading_days = int(test_mask.sum())
    default_scenario_step = min(30, max(1, test_trading_days - 1))
    eff_scenario_step = scenario_inject_step if scenario_inject_step is not None else default_scenario_step

    blocked = {d.symbol for d in p1.diagnostics if d.weight_zero or d.basic_logic_failure}
    r_test_clean = rets.loc[test_mask].dropna(how="any")
    test_returns_daily = (
        r_test_clean[symbols].to_numpy(dtype=float).tolist()
        if len(symbols) and not r_test_clean.empty
        else None
    )

    cw_pipe = _custom_weights_for_symbols(custom_portfolio_weights, symbols)
    p3i = Phase3Input(
        symbols=symbols,
        defense_level=int(level),
        mu_daily=mu.tolist(),
        cov_daily=cov.tolist(),
        sentiments={s: sentiment_effective for s in symbols},
        jump_p=jp,
        jump_impact=ji,
        mc_horizon_days=test_trading_days,
        scenario_inject_step=eff_scenario_step,
        scenario_inject_impact=scenario_inject_impact,
        mc_sentiment_path=mc_st_path,
        blocked_symbols=sorted(blocked),
        test_returns_daily=test_returns_daily,
        custom_portfolio_weights=cw_pipe,
    )
    p3 = run_phase3(p3i, pol, DefenseLevel(level), hist_returns=hist)

    # Generate ISO date labels aligned with the downsampled mc_times step indices
    test_dates = rets.loc[test_mask].index
    n_mc_steps = p3.mc_timesteps          # total path steps (= test_trading_days)
    max_pts = 200
    idx_time = np.unique(
        np.linspace(0, n_mc_steps - 1, num=min(max_pts, n_mc_steps), dtype=int)
    )
    date_labels = [
        str(test_dates[min(int(i), len(test_dates) - 1)].date()) for i in idx_time
    ]
    p3 = p3.model_copy(update={"mc_date_labels": date_labels})

    blind_w = {s: 1.0 / len(symbols) for s in symbols}
    sh_b, sh_f, mdd_b, mdd_f = _shadow_curves(rets, blind_w, p3.weights, test_mask)
    r_test = rets.loc[test_mask].dropna(how="any")
    sh_lbl = [str(i.date()) for i in r_test.index]

    n_sh = len(sh_f)
    p0_mc = (
        p0_pure_mc_median_cumulative_returns(mu, cov, symbols, n_sh)
        if n_sh > 0
        else []
    )
    if len(p0_mc) != n_sh and n_sh > 0:
        p0_mc = (p0_mc + [p0_mc[-1] if p0_mc else 0.0] * n_sh)[:n_sh]

    sem_off, price_off = _semantic_price_alarm_offsets(
        r_test, symbols, test_st_dates, test_st_list, float(pol.tau_s_low)
    )
    lead_days: Optional[int] = None
    if sem_off is not None and price_off is not None:
        lead_days = int(price_off - sem_off)

    test_ix = rets.index[test_mask]
    fail_extra = _failure_identification_research(
        rets=rets,
        r_train=rets.loc[train_mask],
        test_ix=test_ix,
        symbols=symbols,
        p2=p2,
        pol=pol,
        st_series=test_st_series_p2,
        r_test=r_test,
        price_off_rtest=price_off,
    )

    extra_research = _build_extra_research_bundle(
        p2=p2, pol=pol,
        sentiment_for_defense=sentiment_for_defense,
        sem_off=sem_off, price_off=price_off, lead_days=lead_days,
        test_start=test_start, test_end=test_end,
        eff_scenario_step=eff_scenario_step,
        fail_extra=fail_extra,
    )
    _dv = p3.defense_validation or Phase3DefenseValidation()
    p3 = p3.model_copy(update={"defense_validation": _dv.model_copy(update=extra_research)})

    snap = PipelineSnapshot(
        phase0=p0,
        phase1=p1,
        phase2=p2,
        phase3=p3,
        defense_level=int(level),
        defense_policy=pol,
        shadow_blind_cumulative=sh_b,
        shadow_fused_cumulative=sh_f,
        shadow_p0_mc_median_cumulative=p0_mc,
        shadow_index_labels=sh_lbl,
        shadow_mdd_blind_pct=float(mdd_b * 100.0),
        shadow_mdd_fused_pct=float(mdd_f * 100.0),
    )

    if state is not None:
        state.set_policy(pol)
        state.phase0 = p0
        state.phase1 = p1
        state.phase2 = p2
        state.phase3 = p3
        state.defense_level = int(level)
        state.extra["shadow"] = (sh_b, sh_f, mdd_b, mdd_f)

    return snap


def snapshot_to_jsonable(snap: PipelineSnapshot) -> Dict[str, Any]:
    return snap.model_dump()
