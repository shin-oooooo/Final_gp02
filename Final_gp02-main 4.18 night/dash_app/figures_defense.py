"""Defense / fig41 panel figure builders.

Extracted from ``dash_app/figures.py`` during the 2026-04-21 slim-down round.
All public names below are re-exported by ``dash_app.figures`` to preserve the
legacy import surface (``from dash_app.figures import fig_st_sentiment_path``
etc. continues to work unchanged).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def _with_figure_title(fig: go.Figure, figure_title: Optional[str]) -> go.Figure:
    """No-op shim — titles render outside Plotly via ``_figure_wrap``.

    Local copy of the helper from ``dash_app/figures.py`` to avoid a circular
    import (``figures`` re-exports from this module).
    """
    return fig


def _format_yymmdd(value: Any) -> str:
    """渲染 ``YY.MM.DD``。接受 ISO ``YYYY-MM-DD`` / ``pd.Timestamp`` / 类日期对象。"""
    if value is None:
        return "—"
    s = str(value)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return f"{s[2:4]}.{s[5:7]}.{s[8:10]}"
    try:
        ts = pd.Timestamp(value)
        return ts.strftime("%y.%m.%d")
    except Exception:
        return s


def fig_st_sentiment_path(
    test_sentiment_st: Any,
    sentiment_scalar: float,
    template: str,
    *,
    figure_title: Optional[str] = None,
    st_trace: Optional[Dict[str, Any]] = None,
) -> go.Figure:
    """Test-window S_t path when available; else note scalar fallback.

    Edge cases handled:

    - 序列缺失或空 → 纯文本占位。
    - 序列为常数（所有有限值极差 < 1e-9），且等于 ``sentiment_scalar`` →
      视作"新闻抓取 fallback"，加粗副标题明示，hline 偏移一个像素级差值
      以保证视觉上仍可见（否则会与 S_t 完全重合）。
    - 其他情况下，hline 的 annotation 改到右上角，避免与首日 S_t 值重叠。
    - ``st_trace`` 非空且 ``constant_trap_synthetic=True`` → 在副标题区打一行
      橙黄警示："(合成占位 · {synthetic_reason})"，提醒观众当前曲线是由
      ``research/sentiment/series.py`` 的 constant-trap guard 合成的，不代表
      真实舆情信号。``synthetic_reason`` 取自 guard：
        * ``no_headlines_in_extended_warmup`` — 90 日 warmup 内无任何头条；
        * ``kernel_output_near_constant`` — 头条非空但核输出近似常数
          （极差 < 5e-4），常见于"头条全挤在同一日历日"。
    """
    if not (
        isinstance(test_sentiment_st, dict)
        and test_sentiment_st.get("dates")
        and test_sentiment_st.get("values")
    ):
        try:
            print(
                f"[FigX.1] S_t placeholder — sentiment_scalar={float(sentiment_scalar):.4f} "
                f"(dict={isinstance(test_sentiment_st, dict)}, "
                f"dates={bool(test_sentiment_st.get('dates')) if isinstance(test_sentiment_st, dict) else False}, "
                f"values={bool(test_sentiment_st.get('values')) if isinstance(test_sentiment_st, dict) else False})",
                flush=True,
            )
        except Exception:
            pass
        return _with_figure_title(
            go.Figure(
                layout=dict(
                    title=f"测试窗 S_t 未生成（情绪标量 S={float(sentiment_scalar):.2f}）",
                    template=template,
                    height=220,
                )
            ),
            figure_title,
        )

    d = test_sentiment_st["dates"]
    v = test_sentiment_st["values"]
    try:
        _nums = [float(x) for x in v if x is not None]
        if _nums:
            _mn, _mx = min(_nums), max(_nums)
            print(
                f"[FigX.1] rendering n={len(_nums)} "
                f"min={_mn:.4f} max={_mx:.4f} ptp={_mx - _mn:.4f} "
                f"sentiment_scalar={float(sentiment_scalar):.4f} "
                f"head={[round(x, 4) for x in _nums[:5]]} "
                f"tail={[round(x, 4) for x in _nums[-5:]]}",
                flush=True,
            )
    except Exception:
        pass
    x = [str(t) for t in d]
    y: List[float] = []
    for vv in v:
        try:
            y.append(float(vv))
        except (TypeError, ValueError):
            y.append(float("nan"))

    finite = [yv for yv in y if yv == yv and abs(yv) < float("inf")]
    s_const = len(finite) >= 2 and (max(finite) - min(finite)) < 1e-9
    s_equal_scalar = (
        bool(finite)
        and abs(float(finite[0]) - float(sentiment_scalar)) < 1e-6
    )
    is_fallback = s_const and s_equal_scalar

    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name="S_t",
            line=dict(color="#7e57c2", width=2),
        )
    )
    if is_fallback:
        fig.add_hline(
            y=float(sentiment_scalar),
            line_dash="dash",
            line_color="#ff7043",
            line_width=2,
            annotation_text=f"情绪标量 S = {float(sentiment_scalar):.2f}（新闻 fallback）",
            annotation_position="top right",
            annotation_font_color="#ff7043",
        )
        subtitle = (
            "S_t 序列为常数且等于 S → 新闻抓取 fallback，请检查 `news_fetch_log.json`"
        )
    else:
        fig.add_hline(
            y=float(sentiment_scalar),
            line_dash="dash",
            line_color="rgba(255,255,255,0.6)",
            line_width=1,
            annotation_text=f"情绪标量 S = {float(sentiment_scalar):.2f}",
            annotation_position="top right",
            annotation_font_color="rgba(255,255,255,0.85)",
        )
        subtitle = None

    # 合成占位提示（R3.1 guards）：若 meta.sentiment_st_trace 标记为 synthetic，
    # 优先展示该提示（即便 is_fallback 也显式覆盖，以便观众分清"新闻抓取失败"
    # 与"核输出退化为常数"）。
    synthetic_banner: Optional[str] = None
    if isinstance(st_trace, dict) and bool(st_trace.get("constant_trap_synthetic")):
        reason = str(st_trace.get("synthetic_reason") or "synthetic").strip()
        synthetic_banner = f"⚠ 合成占位 · S_t 由 constant-trap guard 生成（reason: {reason}）"

    layout_kwargs: Dict[str, Any] = dict(
        template=template,
        height=260,
        xaxis=dict(tickangle=-35),
        yaxis=dict(range=[-1.05, 1.05], title="S_t"),
        margin=dict(t=44, b=64, l=48, r=24),
    )
    annotations: List[Dict[str, Any]] = []
    if subtitle is not None:
        annotations.append(
            dict(
                text=subtitle,
                xref="paper",
                yref="paper",
                x=0.5,
                y=1.08,
                xanchor="center",
                yanchor="bottom",
                showarrow=False,
                font=dict(color="#ff7043", size=11),
            )
        )
    if synthetic_banner is not None:
        annotations.append(
            dict(
                text=synthetic_banner,
                xref="paper",
                yref="paper",
                x=0.01,
                y=-0.22,
                xanchor="left",
                yanchor="top",
                showarrow=False,
                font=dict(color="#f5a524", size=10),
            )
        )
    if annotations:
        layout_kwargs["annotations"] = annotations
    fig.update_layout(**layout_kwargs)
    return _with_figure_title(fig, figure_title)


# ---------------------------------------------------------------------------
# FigX.5 — JSD stress time-series (defense sidebar)
# ---------------------------------------------------------------------------

def fig_defense_jsd_stress_timeseries(
    p2: Dict[str, Any],
    jsd_baseline_mean: float,
    k_jsd: float,
    stress_window: int,
    template: str,
    *,
    baseline_eps: float = 1e-9,
    figure_title: Optional[str] = None,
) -> go.Figure:
    """Three per-day cross-section JSD series + threshold + first rolling-breach annotation.

    Axes: x = test date, y = JSD value.
    Traces: JSD(Kronos,ARIMA), JSD(Kronos,LGBM), JSD(LGBM,ARIMA).
    Threshold line: k_jsd × max(jsd_baseline_mean, ε)（ε 与侧栏 `jsd_baseline_eps` 一致）。
    Vertical line: first day W=stress_window-day rolling mean of triangle JSD exceeds
    threshold. W 取自 `DefensePolicyConfig.semantic_cosine_window`，与 FigX.6 语义–数值
    滚动余弦共用同一口径（默认 5 日）。
    """
    dates = list(p2.get("test_forecast_dates") or [])
    ka = list(p2.get("test_daily_jsd_kronos_arima") or [])
    kg = list(p2.get("test_daily_jsd_kronos_gbm") or [])
    ga = list(p2.get("test_daily_jsd_gbm_arima") or [])
    tri = list(p2.get("test_daily_triangle_jsd_mean") or [])

    n = min(len(dates), len(ka), len(kg), len(ga), len(tri))
    if n == 0:
        empty = go.Figure(layout=dict(
            title="JSD 应力时序：无测试窗数据",
            template=template, height=300,
            annotations=[dict(text="暂无数据", xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False, font=dict(size=13, color="#888"))],
        ))
        return _with_figure_title(empty, figure_title)

    dates = dates[:n]
    ka, kg, ga, tri = ka[:n], kg[:n], ga[:n], tri[:n]

    _eps = float(max(float(baseline_eps), 1e-15))
    threshold = float(k_jsd) * max(float(jsd_baseline_mean), _eps)
    thr_eff = max(threshold, 1e-12)
    tri_arr = np.array([float(x) if np.isfinite(x) else float("nan") for x in tri], dtype=float)
    tri_pool = float(np.nanmean(tri_arr)) if np.any(np.isfinite(tri_arr)) else 0.0

    # --- JS-style triangle disagreement ribbon (same envelope idea as fig_model_forecast_overlay) ---
    ribbon_scale = 0.48
    y_top: List[float] = []
    y_bot: List[float] = []
    for i in range(n):
        a = float(ka[i]) if np.isfinite(ka[i]) else float("nan")
        b = float(kg[i]) if np.isfinite(kg[i]) else float("nan")
        g = float(ga[i]) if np.isfinite(ga[i]) else float("nan")
        if not (np.isfinite(a) and np.isfinite(b) and np.isfinite(g)):
            y_top.append(float("nan"))
            y_bot.append(float("nan"))
            continue
        raw_hi = max(a, b, g)
        raw_lo = min(a, b, g)
        spread = max(raw_hi - raw_lo, 1e-9)
        t_i = float(tri_arr[i]) if np.isfinite(tri_arr[i]) else tri_pool
        env_scale = max(abs(t_i), 0.5 * spread, _eps)
        e = max(ribbon_scale * 0.35 * env_scale, 0.12 * spread, 2e-4)
        y_top.append(raw_hi + e)
        y_bot.append(raw_lo - e)

    t_ratio0 = float(np.clip(tri_pool / (thr_eff * 1.5), 0.0, 1.0))
    fill_rgba = (
        f"rgba({int(255 - 75 * t_ratio0)},{int(165 - 145 * t_ratio0)},"
        f"{int(20 * t_ratio0)},{round(0.22 + 0.53 * t_ratio0, 2)})"
    )
    band_name = "JS 三角分歧带（日度包络）"

    fig = go.Figure()
    xs_band = list(dates) + list(dates)[::-1] + ([dates[0]] if dates else [])
    ys_band = y_top + y_bot[::-1] + ([y_top[0]] if y_top and np.isfinite(y_top[0]) else [])
    if (
        len(xs_band) == len(ys_band)
        and len(xs_band) > 0
        and all(np.isfinite(v) for v in y_top)
        and all(np.isfinite(v) for v in y_bot)
    ):
        fig.add_trace(
            go.Scatter(
                x=xs_band,
                y=ys_band,
                fill="toself",
                fillcolor=fill_rgba,
                line=dict(width=0),
                name=band_name,
                hoverinfo="skip",
            )
        )

    pairs = [
        ("JSD(Kronos, ARIMA)", ka, "#ff7f0e"),
        ("JSD(Kronos, LGBM)", kg, "#c39bff"),
        ("JSD(LGBM, ARIMA)", ga, "#00e676"),
    ]
    for name, vals, color in pairs:
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=vals,
                mode="lines",
                name=name,
                line=dict(color=color, width=1.8),
                hovertemplate=f"{name}<br>%{{x}}<br>JSD=%{{y:.4f}}<extra></extra>",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=tri,
            mode="lines",
            name="日度三角 JSD",
            line=dict(color="rgba(255,255,255,0.55)", width=1.4, dash="dot"),
            hovertemplate="日度三角 JSD<br>%{x}<br>%{y:.4f}<extra></extra>",
        )
    )

    # Rolling mean of triangle JSD over W=stress_window days — this is the actual
    # alarm signal (matches the red vertical "first breach" line exactly).
    # 前 (W-1) 天窗口不满，用 NaN 占位；W 与 FigX.6 语义—数值余弦共用。
    nw = max(1, int(stress_window))
    roll_series: List[float] = [float("nan")] * n
    for t in range(nw - 1, n):
        window = tri_arr[t + 1 - nw : t + 1]
        if np.any(np.isfinite(window)):
            roll_series[t] = float(np.nanmean(window))
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=roll_series,
            mode="lines",
            name=f"滚动三角均值（W={nw}，告警口径）",
            line=dict(color="#ffffff", width=2.4),
            connectgaps=False,
            hovertemplate="滚动三角均值<br>%{x}<br>%{y:.4f}<extra></extra>",
        )
    )

    # Show ONLY the effective threshold line: k_jsd × max(jsd_baseline_mean, ε)
    # Use an explicit trace (not add_hline) so it appears in legend and stays visible above ribbons.
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=[threshold] * len(dates),
            mode="lines",
            name="阈值 τ = k×max(基线,ε)",
            line=dict(color="rgba(255,80,80,0.95)", width=2.4, dash="dash"),
            hovertemplate="阈值 τ<br>%{x}<br>%{y:.4f}<extra></extra>",
        )
    )

    first_breach: Optional[int] = None
    for t in range(nw - 1, n):
        roll = roll_series[t]
        if np.isfinite(roll) and roll > threshold:
            first_breach = t
            break
    if first_breach is not None:
        breach_date = dates[first_breach]
        try:
            x_v = pd.Timestamp(breach_date)
        except Exception:
            x_v = breach_date
        fig.add_shape(
            type="line",
            x0=x_v,
            x1=x_v,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line=dict(color="rgba(255,80,80,0.9)", width=1.5, dash="solid"),
        )
        fig.add_annotation(
            x=x_v,
            y=1.0,
            xref="x",
            yref="paper",
            text=f"首次背离 {_format_yymmdd(breach_date)}",
            showarrow=False,
            yanchor="top",
            xanchor="left",
            font=dict(size=10, color="rgba(255,120,120,1)"),
        )

    fig.update_layout(
        template=template,
        height=320,
        margin=dict(t=52, b=56, l=56, r=20),
        xaxis=dict(title="测试日", type="date", showgrid=True,
                   gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title="JSD", showgrid=True,
                   gridcolor="rgba(255,255,255,0.06)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, itemsizing="constant"),
        hovermode="x unified",
        plot_bgcolor="rgba(20,24,32,0.45)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return _with_figure_title(fig, figure_title)


# ---------------------------------------------------------------------------
# FigX.6 — Semantic–numeric cosine (updated: rolling window + shadow-optimal μ)
# ---------------------------------------------------------------------------

def fig_defense_semantic_cosine(
    p2: Dict[str, Any],
    meta: Dict[str, Any],
    cosine_window: int,
    template: str,
    *,
    figure_title: Optional[str] = None,
) -> go.Figure:
    """Rolling-window cosine between S_t and shadow-optimal μ cross-section mean.

    Traces:
      - Raw S_t (test window)
      - Shadow-optimal μ̄ (per-day cross-section mean of best-model μ)
      - Rolling cosine similarity (right y-axis, [-1, 1])
    Vertical annotation: first day rolling cos < 0.
    """
    dates_iso = [str(d) for d in (p2.get("test_forecast_dates") or []) if d is not None]
    best_mu_ts = list(p2.get("test_daily_best_model_mu_mean") or [])
    n = min(len(dates_iso), len(best_mu_ts))

    if n == 0:
        empty = go.Figure(layout=dict(
            title="语义背离余弦：无测试窗数据",
            template=template, height=340,
            annotations=[dict(text="暂无数据", xref="paper", yref="paper",
                              x=0.5, y=0.5, showarrow=False, font=dict(size=13, color="#888"))],
        ))
        return _with_figure_title(empty, figure_title)

    dates_plot = dates_iso[:n]
    best_mu = best_mu_ts[:n]

    # Align S_t
    tst = meta.get("test_sentiment_st") if isinstance(meta.get("test_sentiment_st"), dict) else {}
    st_dates = [str(x) for x in (tst.get("dates") or [])]
    st_vals_raw = tst.get("values") or []
    st_vals: List[float] = []
    for v in st_vals_raw:
        try:
            st_vals.append(float(v))
        except (TypeError, ValueError):
            st_vals.append(float("nan"))
    dmap = {st_dates[i]: st_vals[i] for i in range(min(len(st_dates), len(st_vals)))}
    st_arr = np.array([dmap.get(str(d), np.nan) for d in dates_plot], dtype=float)
    st_arr = pd.Series(st_arr).ffill().bfill().to_numpy(dtype=float)

    mu_arr = pd.Series(best_mu, dtype=float).ffill().bfill().to_numpy(dtype=float)

    # Rolling cosine
    window = int(max(2, cosine_window))
    cos_vals: List[float] = [float("nan")] * n
    for k in range(window - 1, n):
        sa = st_arr[k - window + 1 : k + 1]
        sb = mu_arr[k - window + 1 : k + 1]
        na = float(np.linalg.norm(sa))
        nb = float(np.linalg.norm(sb))
        if na > 1e-15 and nb > 1e-15:
            cos_vals[k] = float(np.dot(sa, sb) / (na * nb))

    # First breach day
    first_breach: Optional[int] = None
    for k, v in enumerate(cos_vals):
        if np.isfinite(v) and v < 0.0:
            first_breach = k
            break

    fig = go.Figure()

    # Raw S_t (left y-axis)
    fig.add_trace(go.Scatter(
        x=dates_plot, y=st_arr.tolist(), mode="lines", name="S_t（原始）",
        line=dict(color="rgba(171,71,188,0.65)", width=1.5),
        yaxis="y",
        hovertemplate="S_t=%{y:.4f}<extra></extra>",
    ))

    # Shadow-optimal μ (left y-axis, secondary scale via y3 to keep visual separation)
    fig.add_trace(go.Scatter(
        x=dates_plot, y=mu_arr.tolist(), mode="lines", name="影子最优 μ̄",
        line=dict(color="rgba(38,198,218,0.65)", width=1.5),
        yaxis="y2",
        hovertemplate="μ̄=%{y:.5f}<extra></extra>",
    ))

    # Rolling cosine (right y-axis)
    fig.add_trace(go.Scatter(
        x=dates_plot, y=cos_vals, mode="lines", name=f"滚动余弦 W={window}",
        line=dict(color="#ffffff", width=2.2),
        yaxis="y3",
        hovertemplate="cos=%{y:.4f}<extra></extra>",
    ))

    # Zero line on cosine axis
    fig.add_hline(
        y=0, line=dict(color="rgba(255,80,80,0.5)", width=1, dash="dash"),
        annotation_text="cos=0", annotation_position="bottom right",
        annotation_font=dict(size=9, color="rgba(255,120,120,0.8)"),
    )

    if first_breach is not None:
        x_raw = dates_plot[first_breach]
        try:
            x_v = pd.Timestamp(x_raw)
        except Exception:
            x_v = x_raw
        fig.add_shape(
            type="line",
            x0=x_v,
            x1=x_v,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line=dict(color="rgba(255,80,80,0.9)", width=1.5, dash="solid"),
        )
        fig.add_annotation(
            x=x_v,
            y=1.0,
            xref="x",
            yref="paper",
            text=f"首次背离 {_format_yymmdd(x_raw)}",
            showarrow=False,
            yanchor="top",
            xanchor="left",
            font=dict(size=10, color="rgba(255,120,120,1)"),
        )

    fig.update_layout(
        template=template,
        height=340,
        margin=dict(t=52, b=56, l=56, r=72),
        xaxis=dict(title="测试日", type="date", showgrid=True,
                   gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title="S_t", side="left", showgrid=False,
                   range=[-1.1, 1.1]),
        yaxis2=dict(title="μ̄", side="left", overlaying="y", showgrid=False,
                    anchor="free", position=0.0),
        yaxis3=dict(title="余弦", side="right", overlaying="y", showgrid=True,
                   gridcolor="rgba(255,255,255,0.06)", range=[-1.1, 1.1]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1, itemsizing="constant"),
        hovermode="x unified",
        plot_bgcolor="rgba(20,24,32,0.45)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return _with_figure_title(fig, figure_title)


# ---------------------------------------------------------------------------
# Fig4.1 — fixed 5-day verification charts (post-alarm realized)
# ---------------------------------------------------------------------------

def fig_fig41_focus_daily_returns(
    dates: List[str],
    daily_returns: List[float],
    template: str,
    *,
    figure_title: Optional[str] = None,
) -> go.Figure:
    """Line chart: focus symbol simple daily returns over t0+1..t0+h."""
    from dash_app.services.copy import get_status_message
    n = min(len(dates), len(daily_returns))
    if n == 0:
        return _with_figure_title(
            go.Figure(layout=dict(
                title=get_status_message("fig41_empty_daily_returns", "告警后 5 日：无可用日收益"),
                template=template,
                height=260,
            )),
            figure_title,
        )
    xs = dates[:n]
    ys = [float(v) if np.isfinite(v) else float("nan") for v in daily_returns[:n]]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers",
            name="日收益",
            line=dict(color="#42a5f5", width=2.4),
            marker=dict(size=7, color="#42a5f5"),
            hovertemplate="%{x}<br>r=%{y:.4%}<extra></extra>",
        )
    )
    fig.add_hline(y=0, line=dict(color="rgba(200,200,200,0.35)", width=1, dash="dot"))
    fig.update_layout(
        template=template,
        height=280,
        margin=dict(t=30, b=36, l=56, r=20),
        xaxis=dict(title="交易日", type="date", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title="简单日收益", tickformat=".2%", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        hovermode="x unified",
        plot_bgcolor="rgba(20,24,32,0.45)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return _with_figure_title(fig, figure_title)


# DEPRECATED (2026-04-21): no Python callers (only _naming_audit.txt lists
# it). Kept as stable public entry; delete in a dedicated follow-up PR.
def fig_fig41_std_by_k(
    std_by_k: List[float],
    baseline_std: Optional[float],
    template: str,
    *,
    figure_title: Optional[str] = None,
) -> go.Figure:
    """第二部分：告警后 k=1..h 的横截面 Std 柱状图 + 训练基线线。

    Args:
        std_by_k: 每个时间面 k 的横截面 Std（长度 1..h，可含 NaN）。
        baseline_std: 训练窗滚动序列按 Std 分位得到的阈值。
        template: Plotly template。
        figure_title: 预留参数（与其他 fig_fig41_* 统一，当前未使用）。
    """
    n = len(std_by_k or [])
    if n == 0:
        return _with_figure_title(
            go.Figure(layout=dict(title="Std（告警后 1～5 日）：无数据", template=template, height=260)),
            figure_title,
        )
    xs = [f"D{k + 1}" for k in range(n)]
    ys = [float(v) if np.isfinite(v) else float("nan") for v in std_by_k[:n]]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=xs,
            y=ys,
            name="Std",
            marker_color="rgba(66,165,245,0.85)",
            hovertemplate="%{x}<br>Std=%{y:.4f}<extra></extra>",
        )
    )
    try:
        b = float(baseline_std) if baseline_std is not None else float("nan")
    except (TypeError, ValueError):
        b = float("nan")
    if np.isfinite(b):
        fig.add_hline(
            y=b,
            line=dict(color="rgba(255,80,80,0.65)", width=2, dash="dash"),
            annotation_text=f"Std基线={b:.4f}",
            annotation_position="top right",
            annotation_font=dict(size=9, color="rgba(255,120,120,0.9)"),
        )
    fig.update_layout(
        template=template,
        height=280,
        margin=dict(t=30, b=36, l=56, r=20),
        yaxis=dict(title="横截面 Std（R^(k)）", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        xaxis=dict(title="告警后第 k 天", showgrid=False),
        plot_bgcolor="rgba(20,24,32,0.45)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return _with_figure_title(fig, figure_title)
