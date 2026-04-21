"""Plotly figure builders for Dash research UI.

Defense + fig41 panels live in ``dash_app/figures_defense.py`` and are
re-exported here so ``from dash_app.figures import fig_st_sentiment_path``
and friends continue to work unchanged.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import norm

from dash_app.figures_defense import (
    fig_defense_jsd_stress_timeseries,
    fig_defense_semantic_cosine,
    fig_fig41_focus_daily_returns,
    fig_fig41_std_by_k,
    fig_st_sentiment_path,
)


def _with_figure_title(fig: go.Figure, figure_title: Optional[str]) -> go.Figure:
    """No-op: titles are now rendered outside Plotly via _figure_wrap / figure-unit-label."""
    return fig
def _sort_syms_by_group(
    syms: List[str],
    tech: Sequence[str] | None,
    hedge: Sequence[str] | None,
    safe: Sequence[str] | None,
) -> List[str]:
    """Sort symbols so same-group assets are adjacent: tech → hedge → safe → others."""
    def _key(s: str) -> tuple:
        if tech and s in tech:
            return (0, s)
        if hedge and s in hedge:
            return (1, s)
        if safe and s in safe:
            return (2, s)
        return (3, s)
    return sorted(syms, key=_key)


def fig_correlation_heatmap(
    train_corr_preview: Dict[str, Any],
    symbols: Sequence[str],
    template: str,
    *,
    tech: Sequence[str] | None = None,
    hedge: Sequence[str] | None = None,
    safe: Sequence[str] | None = None,
    cross_threshold: float = 0.3,
    benchmark: str | None = None,
    figure_title: Optional[str] = None,
) -> go.Figure:
    syms = [s for s in symbols if s in train_corr_preview]
    if not syms:
        for k in train_corr_preview:
            if isinstance(train_corr_preview.get(k), dict):
                syms = sorted(train_corr_preview.keys())
                break
    syms = [s for s in syms if isinstance(train_corr_preview.get(s), dict)]
    if len(syms) < 2:
        return _with_figure_title(
            go.Figure(layout=dict(title="训练期相关性（数据不足）", template=template)),
            figure_title,
        )
    syms = _sort_syms_by_group(syms, tech, hedge, safe)
    M = []
    for si in syms:
        row = train_corr_preview.get(si, {})
        M.append([float(row.get(sj, np.nan)) for sj in syms])

    bench = benchmark or ""

    def _sym_color(sym: str) -> str:
        if bench and sym == bench:
            return "#b0bec5"
        if tech and sym in tech:
            return "#4fc3f7"
        if hedge and sym in hedge:
            return "#ffa726"
        if safe and sym in safe:
            return "#66bb6a"
        return "#78909c"

    text_m: List[List[str]] = []
    for i, si in enumerate(syms):
        row_t: List[str] = []
        for j, sj in enumerate(syms):
            v = M[i][j]
            tag = " *" if i != j and abs(v) > cross_threshold else ""
            row_t.append(f"{v:.2f}{tag}")
        text_m.append(row_t)

    n = len(syms)
    xi = list(range(n))
    yi = list(range(n))
    fig = go.Figure(
        data=go.Heatmap(
            z=M,
            x=xi,
            y=yi,
            text=text_m,
            texttemplate="%{text}",
            textfont={"size": 10},
            colorscale="RdBu_r",
            zmid=0,
            zmin=-1,
            zmax=1,
        ),
        layout=dict(
            title=f"训练期资产相关性（* = |ρ|>{cross_threshold} 的非对角强相关）",
            template=template,
            height=400,
            margin=dict(l=56, r=12, t=44, b=72),
            xaxis=dict(
                tickmode="array",
                tickvals=xi,
                ticktext=[""] * n,
                showticklabels=False,
                range=(-0.95, n - 0.45),
                constrain="domain",
            ),
            yaxis=dict(
                tickmode="array",
                tickvals=yi,
                ticktext=[""] * n,
                showticklabels=False,
                autorange="reversed",
                range=(n - 1 + 0.55, -0.65),
                scaleanchor="x",
                scaleratio=1,
            ),
        ),
    )
    for i, sym in enumerate(syms):
        fig.add_annotation(
            x=-0.55,
            y=i,
            xref="x",
            yref="y",
            text=sym,
            showarrow=False,
            xanchor="right",
            font=dict(size=11, color=_sym_color(sym)),
        )
    for j, sym in enumerate(syms):
        fig.add_annotation(
            x=j,
            y=n - 1 + 0.42,
            xref="x",
            yref="y",
            text=sym,
            showarrow=False,
            textangle=-35,
            xanchor="right",
            yanchor="top",
            font=dict(size=11, color=_sym_color(sym)),
        )
    return _with_figure_title(fig, figure_title)


def fig_p0_portfolio_pie(
    weights: Dict[str, float],
    symbols: Sequence[str],
    template: str,
    *,
    tech: Sequence[str] | None = None,
    hedge: Sequence[str] | None = None,
    safe: Sequence[str] | None = None,
    benchmark: str | None = None,
    pie_selected: Optional[str] = None,
    figure_title: Optional[str] = None,
) -> go.Figure:
    """P0 组合权重饼图；颜色与资产类别一致。pie_selected 扇区略外拉，便于在权重更新后仍识别当前调整标的。"""
    def _color(sym: str) -> str:
        if tech and sym in tech:
            return "#4fc3f7"
        if hedge and sym in hedge:
            return "#ffa726"
        if safe and sym in safe:
            return "#66bb6a"
        if benchmark and sym == benchmark:
            return "#b0bec5"
        return "#78909c"

    labels: List[str] = []
    values: List[float] = []
    colors: List[str] = []
    for sym in symbols:
        w = max(float(weights.get(sym, 0.0)), 0.0)
        labels.append(sym)
        values.append(w)
        colors.append(_color(sym))

    if not labels:
        return _with_figure_title(
            go.Figure(layout=dict(title="组合权重（无标的）", template=template, height=320)),
            figure_title,
        )
    ssum = sum(values)
    if ssum <= 1e-15:
        u = 1.0 / len(labels)
        values = [u] * len(labels)
    else:
        values = [v / ssum for v in values]

    sel_u = str(pie_selected).strip().upper() if pie_selected else ""
    pull = [0.07 if str(lab).strip().upper() == sel_u else 0.0 for lab in labels]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            pull=pull,
            marker=dict(colors=colors, line=dict(color="#09090e", width=1.5)),
            hole=0.38,
            textfont=dict(size=10, family="IBM Plex Mono"),
            textinfo="label+percent",
            hovertemplate="%{label}: %{percent}<extra></extra>",
            sort=False,
        )
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=36, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(font=dict(size=10, color="#a8a8c0"), bgcolor="rgba(0,0,0,0)"),
        font=dict(color="#a8a8c0"),
        height=340,
        title=dict(text="组合权重（点击扇区后可用滑块调整）", font=dict(size=13)),
        template=template,
        uirevision="p0-portfolio-pie",
    )
    return _with_figure_title(fig, figure_title)


def fig_beta_regime_compare(
    beta_steady: Dict[str, float],
    beta_break: Dict[str, float],
    symbols: Sequence[str],
    benchmark: str,
    template: str,
    *,
    figure_title: Optional[str] = None,
) -> go.Figure:
    syms = [s for s in symbols if s != benchmark and (s in beta_steady or s in beta_break)]
    if not syms:
        return _with_figure_title(
            go.Figure(layout=dict(title="Dynamic Beta：无可用标的", template=template)),
            figure_title,
        )
    b0 = [float(beta_steady.get(s, float("nan"))) for s in syms]
    b1 = [float(beta_break.get(s, float("nan"))) for s in syms]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(name="稳态期 β（训练窗）", x=syms, y=b0, marker_color="#3F51B5"),
    )
    fig.add_trace(
        go.Bar(name="断裂期 β（测试锚定窗）", x=syms, y=b1, marker_color="#ff7f0e"),
    )
    fig.update_layout(
        barmode="group",
        title=f"Dynamic Beta vs {benchmark}（稳态 vs 断裂）",
        template=template,
        height=400,
        xaxis_title="标的",
        yaxis_title="Beta",
        legend_orientation="h",
        legend_yanchor="bottom",
        legend_y=1.02,
    )
    fig.add_hline(
        y=1.0,
        line_dash="dash",
        line_color="rgba(255,255,255,0.55)",
        line_width=1.5,
        annotation_text="β = 1.0",
        annotation_position="top right",
        annotation_font_size=11,
    )
    return _with_figure_title(fig, figure_title)
def _iso_date_list(xs: List[Any]) -> List[str]:
    """Normalize axis dates to YYYY-MM-DD strings (avoids Plotly mixed int/str x)."""
    out: List[str] = []
    for x in xs:
        try:
            out.append(pd.Timestamp(x).strftime("%Y-%m-%d"))
        except Exception:
            out.append(str(x)[:10])
    return out


def _align_float_series(vals: List[float], n: int) -> List[float]:
    """Pad/truncate so len == n; prevents Plotly from using implicit integer x for extra y points."""
    if n <= 0:
        return []
    if len(vals) >= n:
        return [float(v) for v in vals[:n]]
    return [float(v) for v in vals] + [float("nan")] * (n - len(vals))


def _train_return_tail(json_path: str, symbol: str, train_start: str, train_end: str, n: int = 50) -> tuple[List[str], List[float]]:
    from ass1_core import load_bundle, daily_returns

    bundle = load_bundle(json_path)
    close = bundle.close_universe.sort_index()
    if symbol not in close.columns:
        return [], []
    rets = daily_returns(close[[symbol]]).dropna()
    tr = rets.loc[(rets.index >= pd.to_datetime(train_start)) & (rets.index <= pd.to_datetime(train_end))]
    tr = tr.iloc[-n:]
    dates = [d.strftime("%Y-%m-%d") for d in tr.index]
    vals = tr[symbol].astype(float).tolist()
    return dates, vals


def _test_returns(json_path: str, symbol: str, test_start: str, test_end: str) -> tuple[List[str], List[float]]:
    """Load realized returns for the full test window."""
    try:
        from ass1_core import load_bundle, daily_returns

        bundle = load_bundle(json_path)
        close = bundle.close_universe.sort_index()
        if symbol not in close.columns:
            return [], []
        rets = daily_returns(close[[symbol]]).dropna()
        te = rets.loc[(rets.index >= pd.to_datetime(test_start)) & (rets.index <= pd.to_datetime(test_end))]
        if te.empty:
            return [], []
        dates = [d.strftime("%Y-%m-%d") for d in te.index]
        vals = te[symbol].astype(float).tolist()
        return dates, vals
    except Exception:
        return [], []


def _daily_var95_loss(mu: float, sig: float) -> float:
    """Gaussian 95% 1-day VaR as positive loss: -(μ + σ·z_0.05)."""
    if not (np.isfinite(mu) and np.isfinite(sig)):
        return float("nan")
    sig = max(float(sig), 1e-12)
    return float(-(float(mu) + sig * norm.ppf(0.05)))


def _zip_var95(mu_seq: Sequence[float], sig_seq: Sequence[float]) -> List[float]:
    return [_daily_var95_loss(u, v) for u, v in zip(mu_seq, sig_seq)]


# DEPRECATED (2026-04-21): no Python callers in repo (only referenced by docs
# Instructions/AItoAI_new.md). Kept as stable public entry; delete in a
# dedicated follow-up PR once docs are updated.
def fig_model_forecast_overlay(
    json_path: str,
    symbol: str,
    train_start: str,
    train_end: str,
    model_mu: Dict[str, Dict[str, float]],
    model_sigma: Dict[str, Dict[str, float]],
    jsd_triangle_mean: float,
    jsd_triangle_max: float,
    jsd_threshold: float,
    template: str,
    test_start: str = "2026-02-01",
    test_end: str = "2026-04-07",
    model_mu_test_ts: Optional[Dict[str, Dict[str, List[float]]]] = None,
    model_sigma_test_ts: Optional[Dict[str, Dict[str, List[float]]]] = None,
    test_forecast_dates: Optional[List[str]] = None,
    *,
    figure_title: Optional[str] = None,
) -> go.Figure:
    """Figure 2.5：各模型 95% VaR 单轨（由 OOS μ/σ 的高斯左尾导出）+ JS 分歧带。"""
    train_dates, hist = _train_return_tail(json_path, symbol, train_start, train_end, n=30)
    test_dates_all, test_vals_all = _test_returns(json_path, symbol, test_start, test_end)
    train_dates = _iso_date_list(train_dates)
    test_dates_all = _iso_date_list(test_dates_all)
    hist_down = [max(0.0, -float(x)) for x in hist]

    use_ts = False
    if (
        model_mu_test_ts and test_forecast_dates and symbol
        and test_dates_all
        and len(test_dates_all) == len(test_forecast_dates)
    ):
        use_ts = all(
            len((model_mu_test_ts.get(m) or {}).get(symbol) or []) == len(test_dates_all)
            for m in ("naive", "arima", "lightgbm", "kronos")
        )

    fig = go.Figure()
    L = len(hist)
    if L < 2:
        return _with_figure_title(
            go.Figure(layout=dict(title=f"样本不足 — {symbol}", template=template)),
            figure_title,
        )

    if train_dates:
        fig.add_vrect(
            x0=train_dates[0], x1=train_dates[-1],
            fillcolor="rgba(31,119,180,0.08)", layer="below", line_width=0,
            annotation_text="训练集尾段", annotation_position="top left",
            annotation_font_size=10, annotation_font_color="#7ab8e8",
        )
    if test_dates_all:
        fig.add_vrect(
            x0=test_dates_all[0], x1=test_dates_all[-1],
            fillcolor="rgba(214,39,40,0.06)", layer="below", line_width=0,
            annotation_text="测试集", annotation_position="top right",
            annotation_font_size=10, annotation_font_color="#e88888",
        )

    fig.add_trace(
        go.Scatter(
            x=train_dates, y=hist_down,
            mode="lines+markers", name="训练尾段下行实现 max(0,-r)",
            line=dict(color="#1f77b4", width=2), marker=dict(size=3),
        )
    )

    anchor = float(hist[-1])

    if use_ts and test_dates_all:
        H = len(test_dates_all)
        fore_dates = list(test_dates_all)
        naive_y = _align_float_series(
            [float(x) for x in (model_mu_test_ts or {}).get("naive", {}).get(symbol, [])], H
        )
        arima_y = _align_float_series(
            [float(x) for x in (model_mu_test_ts or {}).get("arima", {}).get(symbol, [])], H
        )
        lgb_y = _align_float_series(
            [float(x) for x in (model_mu_test_ts or {}).get("lightgbm", {}).get(symbol, [])], H
        )
        kronos_y = _align_float_series(
            [float(x) for x in (model_mu_test_ts or {}).get("kronos", {}).get(symbol, [])], H
        )
        sn_ts = _align_float_series(
            [float(x) for x in (model_sigma_test_ts or {}).get("naive", {}).get(symbol, [0.01] * H)], H
        )
        sa_ts = _align_float_series(
            [float(x) for x in (model_sigma_test_ts or {}).get("arima", {}).get(symbol, [0.01] * H)], H
        )
        sl_ts = _align_float_series(
            [float(x) for x in (model_sigma_test_ts or {}).get("lightgbm", {}).get(symbol, [0.01] * H)], H
        )
        sk_ts = _align_float_series(
            [float(x) for x in (model_sigma_test_ts or {}).get("kronos", {}).get(symbol, [0.01] * H)], H
        )
        env_scale = [
            1.15 * max(
                float(sa_ts[j] if j < len(sa_ts) else 0.01),
                float(sl_ts[j] if j < len(sl_ts) else 0.01),
                float(sk_ts[j] if j < len(sk_ts) else 0.01),
                1e-6,
            ) * np.sqrt((j + 1) / float(max(H, 1)))
            for j in range(H)
        ]
        var_naive = _zip_var95(naive_y, sn_ts)
        var_arima = _zip_var95(arima_y, sa_ts)
        var_lgb = _zip_var95(lgb_y, sl_ts)
        var_kronos = _zip_var95(kronos_y, sk_ts)
    else:
        if test_dates_all:
            H = len(test_dates_all)
            anchor_date = train_dates[-1] if train_dates else _iso_date_list([train_end])[0]
            fore_dates = [anchor_date] + list(test_dates_all)
        else:
            H = 12
            try:
                _anchor_dt = pd.Timestamp(train_dates[-1]) if train_dates else pd.Timestamp(train_end)
                _fore_bdays = pd.bdate_range(start=_anchor_dt + pd.Timedelta(days=1), periods=H)
                fore_dates = [_anchor_dt.strftime("%Y-%m-%d")] + [d.strftime("%Y-%m-%d") for d in _fore_bdays]
            except Exception:
                fore_dates = [train_dates[-1]] * (H + 1) if train_dates else []
        if not fore_dates:
            return _with_figure_title(fig, figure_title)

        def _plateau_path(mu: float) -> List[float]:
            return [anchor + (mu - anchor) * min(1.0, j / float(max(H, 1))) for j in range(len(fore_dates))]

        naive_y = [anchor] * len(fore_dates)
        arima_y = _plateau_path(float(model_mu.get("arima", {}).get(symbol, anchor)))
        lgb_y = _plateau_path(float(model_mu.get("lightgbm", {}).get(symbol, anchor)))
        kronos_y = _plateau_path(float(model_mu.get("kronos", {}).get(symbol, anchor)))
        sa = float(model_sigma.get("arima", {}).get(symbol, 0.01))
        sl = float(model_sigma.get("lightgbm", {}).get(symbol, 0.01))
        sk = float(model_sigma.get("kronos", {}).get(symbol, 0.01))
        sn = float(model_sigma.get("naive", {}).get(symbol, 0.01))
        sig_m = max(sa, sl, sk, 1e-6)
        env_scale = [1.15 * sig_m * np.sqrt(min(j, H) / float(max(H, 1))) for j in range(len(fore_dates))]
        sig_naive_l: List[float] = []
        sig_ar_l: List[float] = []
        sig_lgb_l: List[float] = []
        sig_kr_l: List[float] = []
        for j in range(len(fore_dates)):
            step = max(1, min(j, H))
            rt = np.sqrt(step / float(max(H, 1)))
            sig_naive_l.append(max(sn, 1e-12))
            sig_ar_l.append(max(sa * rt, 1e-12))
            sig_lgb_l.append(max(sl * rt, 1e-12))
            sig_kr_l.append(max(sk * rt, 1e-12))
        var_naive = _zip_var95(naive_y, sig_naive_l)
        var_arima = _zip_var95(arima_y, sig_ar_l)
        var_lgb = _zip_var95(lgb_y, sig_lgb_l)
        var_kronos = _zip_var95(kronos_y, sig_kr_l)

    ribbon_scale = 0.48

    fig.add_trace(go.Scatter(
        x=fore_dates, y=var_naive, mode="lines", name="Naive 95% VaR（滞后一期）",
        line=dict(color="#aaaaaa", width=1.5, dash="dash"),
    ))
    fig.add_trace(go.Scatter(
        x=fore_dates, y=var_arima, mode="lines", name="ARIMA 95% VaR",
        line=dict(color="#00e676", width=2.5, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=fore_dates, y=var_lgb, mode="lines", name="LightGBM 95% VaR",
        line=dict(color="#c39bff", width=2, dash="dashdot"),
    ))

    y_top: List[float] = []
    y_bot: List[float] = []
    for i in range(len(fore_dates)):
        raw_hi = float(np.nanmax([var_arima[i], var_lgb[i], var_kronos[i]]))
        raw_lo = float(np.nanmin([var_arima[i], var_lgb[i], var_kronos[i]]))
        spread = max(raw_hi - raw_lo, 1e-9) if np.isfinite(raw_hi - raw_lo) else 1e-9
        e = max(ribbon_scale * env_scale[i], 0.1 * spread)
        y_top.append(raw_hi + e)
        y_bot.append(raw_lo - e)
    thr_eff = max(float(jsd_threshold), 1e-12)
    t_ratio = float(np.clip(jsd_triangle_mean / (thr_eff * 1.5), 0.0, 1.0))
    fill_rgba = f"rgba({int(255 - 75 * t_ratio)},{int(165 - 145 * t_ratio)},{int(20 * t_ratio)},{round(0.22 + 0.53 * t_ratio, 2)})"
    ratio = float(jsd_triangle_mean / thr_eff)
    ratio_show = min(ratio, 99.99)
    band_name = "JS 三角分歧带（JSD 均值 {:.4f} / 阈值 {:.4f} 约 {:.2f} 倍{}）".format(
        jsd_triangle_mean,
        thr_eff,
        ratio_show,
        "，超阈值" if jsd_triangle_mean > thr_eff else "",
    )
    fig.add_trace(go.Scatter(
        x=fore_dates + fore_dates[::-1] + [fore_dates[0]],
        y=y_top + y_bot[::-1] + [y_top[0]],
        fill="toself", fillcolor=fill_rgba,
        line=dict(width=0), name=band_name, hoverinfo="skip",
    ))

    fig.add_trace(go.Scatter(
        x=fore_dates, y=var_kronos, mode="lines", name="Kronos 95% VaR",
        line=dict(color="#ff7f0e", width=3, dash="solid"),
    ))

    if train_dates:
        _xv = train_dates[-1]
        fig.add_shape(
            type="line",
            xref="x",
            yref="paper",
            x0=_xv,
            x1=_xv,
            y0=0,
            y1=1,
            layer="above",
            line=dict(color="rgba(255,255,255,0.5)", width=1.5, dash="solid"),
        )
        fig.add_annotation(
            xref="x",
            yref="paper",
            x=_xv,
            y=1.0,
            text="训练截止" if use_ts else "预测锚点",
            showarrow=False,
            xanchor="center",
            yanchor="bottom",
            font=dict(size=10, color="rgba(255,255,255,0.75)"),
        )

    if test_dates_all and test_vals_all:
        test_down = [max(0.0, -float(v)) for v in test_vals_all]
        fig.add_trace(go.Scatter(
            x=test_dates_all, y=test_down,
            mode="lines+markers", name="测试期下行实现 max(0,-r)",
            line=dict(color="#f06292", width=2, dash="solid"), marker=dict(size=3),
        ))

    fig.update_layout(
        xaxis_title="日期",
        yaxis_title="单日 95% VaR（损失为正）/ 下行实现",
        template=template,
        height=480,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
        hovermode="x unified",
        margin=dict(b=80),
        xaxis=dict(type="date"),
    )
    return _with_figure_title(fig, figure_title)


def _path_to_cumret_pct(path: Sequence[Union[float, int]]) -> List[float]:
    p0 = float(path[0]) if path else 1.0
    p0 = p0 if abs(p0) > 1e-12 else 1.0
    return [float((v / p0 - 1.0) * 100.0) for v in path]


def fig_mc_dual_track(
    times: List[float],
    paths_baseline: List[List[float]],
    paths_stress: List[List[float]],
    worst_idx: int,
    template: str,
    mdd_stress_pct: float | None = None,
    path_median_nojump: Optional[List[float]] = None,
    path_jump_p5: Optional[List[float]] = None,
    mdd_p95: float | None = None,
    date_labels: Optional[List[str]] = None,
    *,
    figure_title: Optional[str] = None,
) -> go.Figure:
    fig = go.Figure()
    if not paths_baseline or not times:
        return _with_figure_title(
            go.Figure(layout=dict(title="蒙特卡洛路径（无数据）", template=template)),
            figure_title,
        )

    # Use actual dates for x-axis when provided, otherwise fractional years
    t: Union[List[str], List[float]] = date_labels if (date_labels and len(date_labels) == len(times)) else times
    worst_idx = int(np.clip(worst_idx, 0, max(len(paths_stress) - 1, 0)))

    pm = path_median_nojump or []
    pj = path_jump_p5 or []
    if pm and pj and len(pm) == len(t) == len(pj):
        ym = _path_to_cumret_pct(pm)
        y5 = _path_to_cumret_pct(pj)
        y_hi = [max(a, b) for a, b in zip(ym, y5)]
        y_lo = [min(a, b) for a, b in zip(ym, y5)]
        fig.add_trace(
            go.Scatter(
                x=t + t[::-1],
                y=y_hi + y_lo[::-1],
                fill="toself",
                fillcolor="rgba(255,100,100,0.14)",
                line=dict(color="rgba(0,0,0,0)"),
                name="风险区（无跳中位数 ↔ 含跳 5% 分位轨）",
                legendgroup="risk",
                showlegend=True,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=t,
                y=ym,
                mode="lines",
                line=dict(color="#2f4f4f", width=2, dash="dash"),
                name="保守：无跳路径中位数",
                legendgroup="med",
                showlegend=True,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=t,
                y=y5,
                mode="lines",
                line=dict(color="#b22222", width=3),
                name="压力：含跳 5% 分位单轨",
                legendgroup="p5",
                showlegend=True,
            )
        )

    for i, p in enumerate(paths_baseline):
        yp = _path_to_cumret_pct(p)
        fig.add_trace(
            go.Scatter(
                x=t,
                y=yp,
                mode="lines",
                line=dict(color="rgba(160,160,160,0.28)", width=1),
                name="基准云（无跳子样本）",
                legendgroup="base",
                showlegend=(i == 0),
            )
        )

    stress_legend_shown = False
    for i, p in enumerate(paths_stress):
        if i == worst_idx:
            continue
        yp = _path_to_cumret_pct(p)
        fig.add_trace(
            go.Scatter(
                x=t,
                y=yp,
                mode="lines",
                line=dict(color="rgba(255,80,80,0.18)", width=1),
                name="压力云（含跳子样本）",
                legendgroup="stress",
                showlegend=(not stress_legend_shown),
            )
        )
        stress_legend_shown = True

    if paths_stress:
        y_w = _path_to_cumret_pct(paths_stress[worst_idx])
        fig.add_trace(
            go.Scatter(
                x=t,
                y=y_w,
                mode="lines",
                line=dict(color="rgba(180,50,50,0.55)", width=1),
                name="云内最差终值路径",
            )
        )

    ann_parts = []
    if mdd_stress_pct is not None and np.isfinite(mdd_stress_pct):
        ann_parts.append(f"P5路径MDD: {mdd_stress_pct:.1f}%")
    if mdd_p95 is not None and np.isfinite(mdd_p95):
        ann_parts.append(f"云P95 MDD（尾部风险）: {mdd_p95:.1f}%")
    ann = "   |   ".join(ann_parts)

    using_dates = date_labels and len(date_labels) == len(times)
    xaxis_title = "日期" if using_dates else "时间 (年)"

    fig.update_layout(
        template=template,
        height=460,
        xaxis_title=xaxis_title,
        yaxis_title="累计收益 (%)",
        annotations=[
            dict(
                text=ann,
                xref="paper",
                yref="paper",
                x=0.01,
                y=-0.18,
                showarrow=False,
                font=dict(size=12),
                xanchor="left",
            )
        ]
        if ann
        else [],
        margin=dict(b=100),
    )
    return _with_figure_title(fig, figure_title)
def fig_p3_triple_test_equity(
    dates: Sequence[str],
    max_sharpe: Optional[Sequence[float]],
    custom_weights: Optional[Sequence[float]],
    cvar_weights: Optional[Sequence[float]],
    template: str,
    *,
    figure_title: Optional[str] = None,
) -> go.Figure:
    """Same test-window daily returns; three fixed weighting rules (Max-Sharpe / user pie / CVaR)."""
    if not dates or not max_sharpe or not custom_weights or not cvar_weights:
        return _with_figure_title(
            go.Figure(
                layout=dict(
                    title="三轨累计收益（无测试窗曲线：请先运行管线并确保测试期有收益样本）",
                    template=template,
                    height=320,
                )
            ),
            figure_title,
        )
    n = len(dates)
    if len(max_sharpe) != n or len(custom_weights) != n or len(cvar_weights) != n:
        return _with_figure_title(
            go.Figure(
                layout=dict(title="三轨累计收益（曲线长度与日期不一致）", template=template, height=320)
            ),
            figure_title,
        )

    def _pct(seq: Sequence[float]) -> List[float]:
        return [float(v) * 100.0 for v in seq]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(dates),
            y=_pct(max_sharpe),
            mode="lines",
            name="Level 0 · Max-Sharpe",
            line=dict(color="#42a5f5", width=2.2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=list(dates),
            y=_pct(custom_weights),
            mode="lines",
            name="自定义权重（饼图）",
            line=dict(color="#78909c", width=2, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=list(dates),
            y=_pct(cvar_weights),
            mode="lines",
            name="熔断权重（Level 2 · CVaR）",
            line=dict(color="#ef5350", width=2.2),
        )
    )
    fig.update_layout(
        template=template,
        height=380,
        xaxis_title="交易日",
        yaxis_title="累计收益 (%)",
        legend=dict(orientation="h", y=1.12),
        margin=dict(t=60),
    )
    return _with_figure_title(fig, figure_title)


def fig_weights_compare(
    weights: Dict[str, float],
    symbols: Sequence[str],
    template: str,
    custom_weights: Optional[Dict[str, float]] = None,
    *,
    figure_title: Optional[str] = None,
) -> go.Figure:
    syms = [s for s in symbols if s in weights] or list(weights.keys())
    if not syms:
        return _with_figure_title(go.Figure(layout=dict(title="权重", template=template)), figure_title)
    n = len(syms)
    eq = 1.0 / n
    w_opt = [float(weights.get(s, 0.0)) for s in syms]
    if custom_weights:
        w_cust = [max(0.0, float(custom_weights.get(s, 0.0))) for s in syms]
        t = sum(w_cust) or 1.0
        w_cust = [v / t for v in w_cust]
        first_name = "自定义权重（饼图）"
        first_y = w_cust
    else:
        first_name = "等权基准"
        first_y = [eq] * n
    ymax = max(0.01, max(w_opt + list(first_y) + [eq]) * 1.15)
    fig = go.Figure(
        data=[
            go.Bar(name=first_name, x=syms, y=first_y, marker_color="#adb5bd"),
            go.Bar(name="当前 Phase3 优化", x=syms, y=w_opt, marker_color="#0d6efd"),
        ],
        layout=dict(
            title="资产权重：自定义（或等权）vs 当前 Phase3 优化",
            barmode="group",
            template=template,
            height=360,
            yaxis=dict(title="权重", range=[0, ymax]),
        ),
    )
    return _with_figure_title(fig, figure_title)
# ── Phase 2 Divergence View helpers ─────────────────────────────────────────

_P2_MODELS = ["naive", "arima", "lightgbm", "kronos"]
_P2_COLORS = {"naive": "#aaaaaa", "arima": "#00e676", "lightgbm": "#c39bff", "kronos": "#ff7f0e"}
_P2_LABELS = {"naive": "Naive", "arima": "ARIMA", "lightgbm": "LightGBM", "kronos": "Kronos"}


def _gaussian_pdf(x: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    s = max(float(sigma), 1e-12)
    return np.exp(-0.5 * ((x - mu) / s) ** 2) / (s * np.sqrt(2.0 * np.pi))


# DEPRECATED (2026-04-21): zero callers across repo. Kept to preserve file
# surface during slim-down round; delete in a dedicated follow-up PR.
def _jsd_lookup(jsd_matrix: Dict[str, Dict[str, float]], a: str, b: str) -> float:
    if not jsd_matrix:
        return 0.0
    if a in jsd_matrix and b in jsd_matrix[a]:
        return float(jsd_matrix[a][b])
    if b in jsd_matrix and a in jsd_matrix[b]:
        return float(jsd_matrix[b][a])
    return 0.0
def fig_p2_best_model_pixels(
    best_model_per_symbol: Dict[str, str],
    symbols: Sequence[str],
    selected_symbol: Optional[str],
    template: str,
    *,
    figure_title: Optional[str] = None,
) -> go.Figure:
    """4 rows (models) × N columns (assets): lit square = shadow-holdout best model."""
    syms = [s for s in symbols if s]
    if not syms:
        return _with_figure_title(
            go.Figure(layout=dict(title="各资产影子最优模型（无标的）", template=template, height=200)),
            figure_title,
        )

    n = len(syms)
    # 响应式尺寸：
    #   N ≤ 5 → 沿用原尺寸（bg=14 / lit=24）；
    #   N = 6 → 缩到 bg=12 / lit=20，把 tick 倾角从 -35 加到 -45；
    #   N ≥ 7 → 继续缩到 bg=10 / lit=17，tick 倾角 -55。
    # 这是给 Fig3.1 加一个软的列宽收缩策略，避免 N 大时 scatter 列重叠，
    # 同时 x 轴 ticklabel 太长时也不会互相压字。
    if n >= 7:
        bg_size, lit_size, tick_angle = 10, 17, -55
    elif n == 6:
        bg_size, lit_size, tick_angle = 12, 20, -45
    else:
        bg_size, lit_size, tick_angle = 14, 24, -35

    row_of = {m: i for i, m in enumerate(_P2_MODELS)}
    fig = go.Figure()
    # dim background grid
    fig.add_trace(go.Scatter(
        x=[j for mi in range(4) for j in range(n)],
        y=[mi for mi in range(4) for j in range(n)],
        mode="markers",
        marker=dict(size=bg_size, color="rgba(120,120,140,0.10)", symbol="square"),
        showlegend=False, hoverinfo="skip",
    ))
    # lit pixels
    for j, sym in enumerate(syms):
        bm = str(best_model_per_symbol.get(sym) or "naive")
        if bm not in row_of:
            bm = "naive"
        mi = row_of[bm]
        fig.add_trace(go.Scatter(
            x=[j], y=[mi], mode="markers",
            marker=dict(size=lit_size, color=_P2_COLORS[bm], symbol="square",
                        line=dict(width=2, color="rgba(255,255,255,0.8)")),
            showlegend=False,
            hovertemplate=f"{sym}<br>影子最优：{_P2_LABELS[bm]}<extra></extra>",
        ))
    if selected_symbol and selected_symbol in syms:
        fig.add_vline(x=syms.index(selected_symbol), line_width=2, line_dash="dot",
                      line_color="rgba(255,255,255,0.40)")
    fig.update_layout(
        title=dict(text="各资产影子验证最优模型（每列一盏，行色=曲线色）", font=dict(size=13)),
        template=template, height=240,
        margin=dict(l=72, r=24, t=52, b=72),
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(n)),
            ticktext=list(syms),
            tickangle=tick_angle,
            showgrid=False,
            zeroline=False,
            # 给 x 轴两侧留 0.5 个单位 padding，避免首尾 marker 被 clip；
            # 并通过 constraintoward="center" 让列宽随宿主容器宽度线性缩放。
            range=[-0.6, n - 0.4],
        ),
        yaxis=dict(tickmode="array", tickvals=list(range(4)),
                   ticktext=[_P2_LABELS[m] for m in _P2_MODELS],
                   showgrid=False, autorange="reversed"),
        plot_bgcolor="rgba(30,34,44,0.35)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return _with_figure_title(fig, figure_title)


def _p2_hex_to_rgb(h: str) -> tuple[int, int, int]:
    s = h.strip().lstrip("#")
    if len(s) >= 6:
        return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    return 128, 130, 135


def _p2_soft_density_colorscale(hex_color: str) -> List[List[Union[float, str]]]:
    """z∈[0,1]: low → fully transparent; high → same RGB as the model μ line (opaque).

    Stops are skewed so only the upper part of z reaches saturated axis color — large
    low/high density visual gap.
    """
    r, g, b = _p2_hex_to_rgb(hex_color)
    return [
        [0.0, f"rgba({r},{g},{b},0)"],
        [0.08, f"rgba({r},{g},{b},0.02)"],
        [0.22, f"rgba({r},{g},{b},0.08)"],
        [0.42, f"rgba({r},{g},{b},0.22)"],
        [0.62, f"rgba({r},{g},{b},0.48)"],
        [0.82, f"rgba({r},{g},{b},0.78)"],
        [0.94, f"rgba({r},{g},{b},0.94)"],
        [1.0, f"rgba({r},{g},{b},1)"],
    ]


def fig_p2_density_heatmap(
    test_forecast_dates: Optional[Sequence[Any]],
    model_mu_test_ts: Dict[str, Any],
    model_sigma_test_ts: Dict[str, Any],
    symbol: Optional[str],
    template: str,
    *,
    test_vals: Optional[Sequence[float]] = None,
    n_r_bins: int = 120,
    model: str = "all",
    figure_title: Optional[str] = None,
) -> go.Figure:
    """Figure 2.3: time × return plane — predictive density p_t(r) with μ(t) ridge lines.

    OOS: for each test date t, uses Gaussian N(μ_t, σ_t²) per model; stacked as semi-transparent
    layers when ``model=='all'``. Legend group toggles density + μ together per model.
    """
    if not symbol or not test_forecast_dates:
        return _with_figure_title(
            go.Figure(
                layout=dict(
                    title="预测密度演化：请先运行计算并选择标的",
                    template=template,
                    height=420,
                    annotations=[dict(text="暂无 OOS 序列数据", xref="paper", yref="paper",
                                      x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#888"))],
                )
            ),
            figure_title,
        )

    dates = [d for d in (test_forecast_dates or []) if d is not None]
    if not dates:
        return _with_figure_title(
            go.Figure(layout=dict(title="预测密度演化：无测试日期", template=template, height=420)),
            figure_title,
        )

    T = len(dates)
    models_to_use = _P2_MODELS if model == "all" else [model]

    models_valid: List[str] = []
    all_mus: List[List[float]] = []
    all_sigs: List[List[float]] = []
    for m in models_to_use:
        ts_m = (model_mu_test_ts.get(m) or {}).get(symbol) or []
        ts_s = (model_sigma_test_ts.get(m) or {}).get(symbol) or []
        if len(ts_m) == T and len(ts_s) == T:
            models_valid.append(m)
            all_mus.append([float(x) for x in ts_m])
            all_sigs.append([float(x) for x in ts_s])

    if not all_mus:
        return _with_figure_title(
            go.Figure(
                layout=dict(
                    title=f"预测密度演化 — {symbol}：OOS μ/σ 序列不可用",
                    template=template,
                    height=420,
                )
            ),
            figure_title,
        )

    all_mu_arr = np.array(all_mus)
    all_sig_arr = np.array(all_sigs)
    sig_max = float(np.nanmax(np.where(np.isfinite(all_sig_arr), all_sig_arr, np.nan)))
    mu_lo = float(np.nanmin(all_mu_arr)) - 4.0 * sig_max
    mu_hi = float(np.nanmax(all_mu_arr)) + 4.0 * sig_max
    if not (np.isfinite(mu_lo) and np.isfinite(mu_hi) and mu_lo < mu_hi):
        mu_lo, mu_hi = -0.05, 0.05
    r_bins = np.linspace(mu_lo, mu_hi, n_r_bins + 1)
    r_centers = (r_bins[:-1] + r_bins[1:]) / 2.0

    fig = go.Figure()
    multi_layer = model == "all" and len(models_valid) > 1
    # γ>1：大部分低密度留在色带低端（更透明），只有高密度区快速贴近轴线色
    z_gamma = 1.75

    for m_idx, m in enumerate(models_valid):
        mus_m = all_mus[m_idx]
        sigs_m = all_sigs[m_idx]
        density_grid = np.zeros((n_r_bins, T), dtype=np.float32)
        for t_idx in range(T):
            mu_t = mus_m[t_idx]
            sig_t = max(sigs_m[t_idx], 1e-8)
            if not (np.isfinite(mu_t) and np.isfinite(sig_t)):
                continue
            density_grid[:, t_idx] = _gaussian_pdf(r_centers, mu_t, sig_t).astype(np.float32)
        log_dens = np.log1p(density_grid)
        zmax = float(np.nanmax(log_dens))
        if zmax < 1e-14:
            z_norm = np.zeros_like(log_dens)
        else:
            z_norm = (log_dens / zmax).astype(np.float32)
        z_norm = np.clip(z_norm, 0.0, 1.0) ** z_gamma

        lbl = _P2_LABELS.get(m, m)
        fig.add_trace(go.Heatmap(
            x=dates,
            y=r_centers.tolist(),
            z=z_norm.tolist(),
            colorscale=_p2_soft_density_colorscale(_P2_COLORS.get(m, "#888888")),
            opacity=0.78 if multi_layer else 1.0,
            xgap=0,
            ygap=0,
            zsmooth=False,
            showscale=not multi_layer,
            hovertemplate=(
                f"{lbl} 密度<br>日期: %{{x}}<br>收益: %{{y:.4f}}<br>相对强度: %{{z:.2f}}<extra></extra>"
            ),
            name=lbl,
            legendgroup=m,
            showlegend=True,
            **({} if multi_layer else {
                "colorbar": dict(
                    title=dict(text="相对强度", side="right"),
                    thickness=12, len=0.72, tickfont=dict(size=9),
                ),
            }),
        ))
        lw = 2.6 if m == "kronos" else 1.85
        dash = "solid" if m == "kronos" else "dash"
        fig.add_trace(go.Scatter(
            x=dates,
            y=mus_m,
            mode="lines",
            name=lbl,
            legendgroup=m,
            showlegend=False,
            line=dict(color=_P2_COLORS.get(m, "#cccccc"), width=lw, dash=dash),
            hovertemplate=f"μ({lbl})<br>%{{x}}<br>μ=%{{y:.5f}}<extra></extra>",
        ))

    tv = list(test_vals) if test_vals is not None else []
    if tv and len(tv) == T:
        fig.add_trace(go.Scatter(
            x=dates,
            y=tv,
            mode="lines+markers",
            name="已实现收益（真值）",
            legendgroup="realized",
            line=dict(color="rgba(240,98,146,0.92)", width=2),
            marker=dict(size=3, color="rgba(240,98,146,0.92)"),
            hovertemplate="实现: %{x}<br>r=%{y:.5f}<extra></extra>",
        ))

    fig.update_layout(
        template=template,
        height=440,
        xaxis=dict(
            title="日期（测试期 t）",
            type="date",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
        ),
        yaxis=dict(
            title="预测下一期收益 r",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            tracegroupgap=0,
            itemsizing="constant",
        ),
        margin=dict(t=68, b=56, l=58, r=28),
        hovermode="closest",
        plot_bgcolor="rgba(20,24,32,0.45)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return _with_figure_title(fig, figure_title)
