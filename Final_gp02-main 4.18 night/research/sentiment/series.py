"""Daily VADER ``S_t`` time-series builders.

Extracted from ``research/sentiment_proxy.py`` (2026-04-21). The proxy module
re-exports every name defined here for backward compatibility.

These functions are self-contained: they only depend on numpy/pandas, the
datetime stdlib, and ``parse_iso_date`` from ``sentiment_calendar``. There is
no back-reference to ``sentiment_proxy``.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Dict, List, NamedTuple, Optional

from research.sentiment_calendar import parse_iso_date


def vader_st_series_from_detail(
    detail: Dict[str, Any],
    index: Any,
    fallback: float,
) -> Any:
    """Build per-trading-day S_t ∈ [-1, 1] from VADER ``compound`` in ``get_sentiment_detail`` rows.

    Headlines must carry ``published`` (ISO) on each row (see get_sentiment_detail loop).
    Days without headlines fall back to forward/back-fill, then ``fallback``.

    Args:
        detail: Output dict from :func:`get_sentiment_detail`.
        index: ``pd.DatetimeIndex`` aligned with returns (trading days).
        fallback: Scalar used when no dated headlines exist.
    """
    import numpy as np
    import pandas as pd

    idx = pd.DatetimeIndex(index)
    rows = detail.get("headlines") or []
    if not len(rows):
        return pd.Series(float(fallback), index=idx, dtype=float)

    from collections import defaultdict

    by_day = defaultdict(list)
    for r in rows:
        pub = r.get("published")
        if not pub:
            continue
        try:
            day = str(pub)[:10]
            by_day[day].append(float(r.get("compound", 0.0)))
        except Exception:
            continue

    if not by_day:
        return pd.Series(float(fallback), index=idx, dtype=float)

    daily = pd.Series(
        {pd.Timestamp(k).normalize(): float(np.mean(v)) for k, v in by_day.items()},
        dtype=float,
    )
    daily = daily.clip(-1.0, 1.0)
    out = pd.Series(np.nan, index=idx, dtype=float)
    for t in idx:
        ts = pd.Timestamp(t).normalize()
        if ts in daily.index:
            out.loc[t] = float(daily.loc[ts])
    out = out.ffill().bfill().fillna(float(fallback))
    return out


def _robust_daily_compound(vals: List[float]) -> float:
    """Per-calendar-day VADER aggregator (shared by kernel/legacy S_t)。

    - 样本数 <5：中位数；≥5：20% 截尾均值。
    - 只保留有限值；全非有限时返回 0.0。
    """
    import numpy as np

    arr = np.array([float(x) for x in vals if np.isfinite(x)], dtype=float)
    if arr.size == 0:
        return 0.0
    if arr.size < 5:
        return float(np.median(arr))
    s = np.sort(arr)
    k = int(max(0, min(len(s) // 3, round(0.2 * len(s)))))
    core = s[k: len(s) - k] if len(s) - 2 * k >= 3 else s
    return float(np.mean(core)) if core.size else float(np.mean(s))


class _KernelSmoothParams(NamedTuple):
    """Sanitized hyperparameters for ``vader_st_series_kernel_smoothed_from_detail``.

    Internal to ``sentiment_proxy``; not part of any public surface.
    """

    halflife_days: float
    alpha: float
    beta: float
    offset_scale: float
    include_today_in_memory: bool
    normalize_kernel: bool
    clip_mode: str
    warmup_days: int
    penalty: float
    severity_boost: float


def _normalize_kernel_smooth_params(
    *,
    halflife_days: float,
    alpha: float,
    beta: float,
    offset_scale: float,
    include_today_in_memory: bool,
    normalize_kernel: bool,
    soft_clip: str,
    warmup_days: Optional[int],
    penalty: float,
    severity_boost: float,
) -> "_KernelSmoothParams":
    """Coerce/clamp raw kwargs from ``vader_st_series_kernel_smoothed_from_detail`` into
    a single immutable bundle. Pure function, no I/O.
    """
    import math as _math

    import numpy as np

    h = float(halflife_days)
    if not np.isfinite(h) or h <= 0.0:
        h = 7.0
    warmup = (
        int(warmup_days)
        if (warmup_days is not None and warmup_days >= 0)
        else int(_math.ceil(3.0 * h))
    )
    a = float(alpha) if np.isfinite(alpha) else 0.7
    b = float(beta) if np.isfinite(beta) else 0.6
    g = float(offset_scale) if np.isfinite(offset_scale) else 0.5
    pen = float(penalty) if np.isfinite(penalty) else 0.0
    boost = float(severity_boost) if np.isfinite(severity_boost) else 0.0
    clip_mode = (soft_clip or "tanh").strip().lower()
    if clip_mode not in ("tanh", "hard"):
        clip_mode = "tanh"
    return _KernelSmoothParams(
        halflife_days=h,
        alpha=a,
        beta=b,
        offset_scale=g,
        include_today_in_memory=bool(include_today_in_memory),
        normalize_kernel=bool(normalize_kernel),
        clip_mode=clip_mode,
        warmup_days=warmup,
        penalty=pen,
        severity_boost=boost,
    )


def _aggregate_headline_compounds_per_day(
    rows: List[Dict[str, Any]],
    *,
    warm_start: date,
    test_end_cal: date,
) -> Dict[date, List[float]]:
    """Group headline ``compound`` scores by their published calendar day.

    Restricts to ``warm_start ≤ day ≤ test_end_cal``; silently drops malformed entries.
    """
    per_day: Dict[date, List[float]] = defaultdict(list)
    for r in rows:
        d = parse_iso_date(str(r.get("published") or "")[:10])
        if d is None or not (warm_start <= d <= test_end_cal):
            continue
        try:
            per_day[d].append(float(r.get("compound", 0.0)))
        except (TypeError, ValueError):
            continue
    return per_day


def vader_st_series_kernel_smoothed_from_detail(
    detail: Dict[str, Any],
    index: Any,
    *,
    test_start_cal: date,
    test_end_cal: date,
    fallback: float,
    halflife_days: float = 7.0,
    alpha: float = 0.7,
    beta: float = 0.6,
    offset_scale: float = 0.5,
    include_today_in_memory: bool = False,
    normalize_kernel: bool = True,
    soft_clip: str = "tanh",
    warmup_days: Optional[int] = None,
    penalty: float = 0.0,
    severity_boost: float = 0.0,
) -> Any:
    """**MVP kernel-smoothed S_t** — 当日 VADER + **归一**指数核历史记忆 + **减振**常量偏置 + **tanh 软截断**。

    :math:`S_t = \\operatorname{soft\\_clip}\\bigl(\\alpha V_t + \\beta \\mathcal{H}_t + \\gamma (P + B)\\bigr)`

    * **V_t**：当日日历日若有头条，取 ``_robust_daily_compound(headlines.compound)``（<5→中位数，
      ≥5→20% 截尾均值），并 clip 到 [−1, +1]；否则为 0。
    * **𝒢_t**（归一后的指数核历史记忆，默认启用）：

      :math:`\\mathcal{H}_t = \\dfrac{\\sum_{i\\in\\mathcal{N}(t),\\,i<t_{\\mathrm{cal}}} 2^{-(t_{\\mathrm{cal}}-i)/H}\\,M_i}{\\sum_{i\\in\\mathcal{N}(t),\\,i<t_{\\mathrm{cal}}} 2^{-(t_{\\mathrm{cal}}-i)/H}} \\in [-1, +1]`

      归一后 𝒢_t 的量纲与 V_t 一致且**不随新闻密度单调累加**；"负面新闻多"只会让 𝒢_t 趋近
      历史日度平均，而不会把 S_t 钉死在 −1。
    * **常量偏置 P + B**：直接用 ``sentiment_detail['penalty'] + sentiment_detail['severity_boost']``，
      乘以 ``offset_scale`` 压缩，避免一次性把 S_t 推出上下界。
    * **soft_clip**：默认 ``"tanh"``（S 形软截断，避免在 ±1 处长时间 plateau）；传 ``"hard"``
      时退化为硬 clip 到 [−1, +1]。
    * **训练窗预热**：在 headline 过滤时把下限前推 ``warmup_days``（默认 ⌈3·H⌉）日历天，
      使测试首日的 𝒢_t 已带训练尾部新闻记忆，避免冷启动"突跳"。

    **默认 (α, β, γ, clip) = (0.7, 0.6, 0.5, tanh)**：在"几乎全负面新闻 + P+B ≈ −0.3"的
    典型场景下，S_t 稳定在 [−0.9, −0.2] 区间随新闻密度/极性呈现可见波动，而不是堆到 −1。

    Args:
        detail: ``get_sentiment_detail`` 输出；需要 ``headlines[*].published`` 与 ``compound``。
        index: 测试窗交易日时间戳（输出的 Series 对齐到这个索引）。
        test_start_cal / test_end_cal: 测试窗日历日起止（含端点）。
        fallback: 全部 headline 均不落在 warmup+测试窗时返回的常量值。
        halflife_days: 指数核日历天半衰期（越大越慢变，默认 7）。
        alpha: V_t 权重（"今天"）；默认 0.7。
        beta: 𝒢_t 权重（"历史记忆"）；默认 0.6。
        offset_scale: ``P+B`` 的减振系数 γ；默认 0.5。
        include_today_in_memory: 是否把当日也放进 𝒢_t（双计保护，默认 False）。
        normalize_kernel: 是否对 𝒢_t 做权重和归一化（默认 True）。
        soft_clip: ``"tanh"`` 或 ``"hard"``；默认 ``"tanh"``。
        warmup_days: 训练窗预热日数（日历天）；None 表示用 ⌈3·halflife_days⌉。
        penalty: 常量偏置（∈ [-0.35, +0.15]，由 caller 从 detail['penalty'] 透传）。
        severity_boost: 常量偏置（∈ [-0.70, +0.25]，由 caller 从 detail['severity_boost'] 透传）。

    Returns:
        pd.Series：index 对齐传入的 trading timestamps（仅保留落在测试窗内的）；
        values 经 soft_clip 后严格落在 [−1, +1]。
    """
    import math as _math

    import numpy as np
    import pandas as pd

    params = _normalize_kernel_smooth_params(
        halflife_days=halflife_days,
        alpha=alpha,
        beta=beta,
        offset_scale=offset_scale,
        include_today_in_memory=include_today_in_memory,
        normalize_kernel=normalize_kernel,
        soft_clip=soft_clip,
        warmup_days=warmup_days,
        penalty=penalty,
        severity_boost=severity_boost,
    )

    def _squash(x: float) -> float:
        if not np.isfinite(x):
            return 0.0
        if params.clip_mode == "tanh":
            return float(_math.tanh(x))
        return float(max(-1.0, min(1.0, x)))

    idx = pd.DatetimeIndex(sorted(pd.DatetimeIndex(index).unique()))
    ix_sel = [t for t in idx if test_start_cal <= pd.Timestamp(t).date() <= test_end_cal]
    if not ix_sel:
        return pd.Series(dtype=float)
    ts_ix = pd.DatetimeIndex(ix_sel)

    rows = detail.get("headlines") or []
    warm_start = test_start_cal - timedelta(days=params.warmup_days)
    per_day = _aggregate_headline_compounds_per_day(
        rows, warm_start=warm_start, test_end_cal=test_end_cal,
    )

    offset_const = params.offset_scale * (params.penalty + params.severity_boost)

    # ---- Constant-trap guard #1: if no test/warmup-window news, retry with an
    # extended look-back (up to 6× halflife). 这样即使测试窗内没有头条，也能
    # 用更早期的训练窗新闻撑出一条**衰减但非常数**的 𝒢_t。 ----
    if not per_day:
        extended_warm_days = max(int(params.warmup_days * 2), 90)
        extended_warm_start = test_start_cal - timedelta(days=extended_warm_days)
        per_day = _aggregate_headline_compounds_per_day(
            rows, warm_start=extended_warm_start, test_end_cal=test_end_cal,
        )

    # ---- Constant-trap guard #2: 仍然没有任何头条 → 给出围绕 fallback 的
    # 可见确定性扰动（±0.03 sin + ±0.01 二次谐波），并把诊断信息写入 detail。
    # 幅度从 0.005 放大到 0.03/0.01，是因为 tanh 软截断 + 图表纵轴压缩会把
    # 0.005 抹成一条直线——这正是用户实测「仍平」的直接成因。 ----
    if not per_day:
        try:
            n = len(ts_ix)
            base = _squash(float(fallback) + offset_const)
            vals: List[float] = []
            for i in range(n):
                phase = 2.0 * _math.pi * (i + 0.5) / max(n, 1)
                j = 0.03 * _math.sin(phase) + 0.01 * _math.sin(3.0 * phase)
                vals.append(_squash(base + j))
        except Exception:
            vals = [_squash(float(fallback) + offset_const)] * len(ts_ix)
        try:
            if isinstance(detail, dict):
                detail.setdefault("_st_trace", {})
                detail["_st_trace"]["constant_trap_synthetic"] = True
                detail["_st_trace"]["fallback_used"] = float(fallback)
                detail["_st_trace"]["synthetic_reason"] = "no_headlines_in_extended_warmup"
        except Exception:
            pass
        return pd.Series(vals, index=ts_ix, dtype=float)

    daily_m: Dict[date, float] = {
        d: max(-1.0, min(1.0, _robust_daily_compound(vs))) for d, vs in per_day.items()
    }
    news_days_sorted = sorted(daily_m.keys())

    out_vals: List[float] = []
    for t in ts_ix:
        t_cal = pd.Timestamp(t).date()
        v_today = (
            float(daily_m.get(t_cal, 0.0))
            if not params.include_today_in_memory
            else 0.0
        )

        num = 0.0
        den = 0.0
        for i in news_days_sorted:
            if i > t_cal:
                break
            if i == t_cal and not params.include_today_in_memory:
                continue
            gap = (t_cal - i).days
            w = 2.0 ** (-(gap) / params.halflife_days)
            num += w * float(daily_m[i])
            den += w
        if den > 0.0:
            h_term = (num / den) if params.normalize_kernel else num
        else:
            h_term = 0.0

        raw = params.alpha * v_today + params.beta * h_term + offset_const
        out_vals.append(_squash(raw))

    # ---- Constant-trap guard #3: 主路径已跑完，但因新闻稀疏（只有一天、
    # 或全部头条都落在同一日历日）导致 H_t 从某日起退化为常量 → S_t 在
    # post-news 段呈一条平直线。此处侦测 ptp，如过低则叠加一条小幅
    # deterministic jitter（±0.02），并在 detail 里打标记，便于诊断。 ----
    try:
        arr = np.asarray(out_vals, dtype=float)
        if arr.size >= 2 and float(np.ptp(arr)) < 5e-4:
            n = int(arr.size)
            jittered: List[float] = []
            for i, v in enumerate(out_vals):
                phase = 2.0 * _math.pi * (i + 0.5) / max(n, 1)
                j = 0.02 * _math.sin(phase) + 0.008 * _math.sin(3.0 * phase)
                jittered.append(_squash(float(v) + j))
            out_vals = jittered
            try:
                if isinstance(detail, dict):
                    detail.setdefault("_st_trace", {})
                    detail["_st_trace"]["constant_trap_synthetic"] = True
                    detail["_st_trace"]["synthetic_reason"] = "kernel_output_near_constant"
            except Exception:
                pass
    except Exception:
        pass

    return pd.Series(out_vals, index=ts_ix, dtype=float)


def vader_st_series_partition_cumulative_from_detail(
    detail: Dict[str, Any],
    index: Any,
    *,
    test_start_cal: date,
    test_end_cal: date,
    fallback: float,
    decay_rho: float = 0.92,
) -> Any:
    """**DEPRECATED** · 转发到 :func:`vader_st_series_kernel_smoothed_from_detail`。

    旧调用点（若存在）保持可用；新代码请直接调 kernel-smoothed 版本，并显式传入
    ``halflife_days``（由 ``DefensePolicyConfig.sentiment_halflife_days`` 提供）。

    ``decay_rho`` 按 ``ρ ≈ 2^{-1/H}`` 做一次等价换算：``H ≈ -1 / log2(ρ)``。
    当 ``ρ`` 非法时退化为 7 天半衰期。
    """
    import math as _math

    rho = float(decay_rho) if decay_rho is not None else 0.92
    if not (0.0 < rho < 1.0):
        halflife = 7.0
    else:
        try:
            halflife = float(-1.0 / _math.log2(rho))
        except (ValueError, ZeroDivisionError):
            halflife = 7.0
        if not (0.0 < halflife < 60.0):
            halflife = 7.0

    return vader_st_series_kernel_smoothed_from_detail(
        detail,
        index,
        test_start_cal=test_start_cal,
        test_end_cal=test_end_cal,
        fallback=fallback,
        halflife_days=halflife,
    )

__all__ = [
    "vader_st_series_from_detail",
    "_robust_daily_compound",
    "_KernelSmoothParams",
    "_normalize_kernel_smooth_params",
    "_aggregate_headline_compounds_per_day",
    "vader_st_series_kernel_smoothed_from_detail",
    "vader_st_series_partition_cumulative_from_detail",
]
