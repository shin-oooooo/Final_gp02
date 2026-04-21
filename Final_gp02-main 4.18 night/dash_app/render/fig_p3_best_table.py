"""Figure 3.1 · 各标的最佳模型收益期望与波动预测（无竖向条框的三行小表）。

**纯图表构造器**，单一职责：把 Phase 2 的 ``best_model_per_symbol`` / ``model_mu``
/ ``model_sigma`` 字典，按 ``symbols`` 顺序取出胜者模型在 **测试窗末端** 的一步
预测 (μ̂, σ̂)，渲染成 3×N 的 Plotly Table：

====  ====  ====  ...
标的   S1    S2   ...
μ̂     .
σ̂     .
====  ====  ====  ...

视觉约定与用户规范一致：**无竖向条框**（所有 cell border 透明），通过
隔行 fill 实现可读的水平分隔。

该模块仅依赖 ``plotly.graph_objects``，**不触碰 Dash / 任何项目内部模块**，
便于独立测试与替换。由 ``dash_app/render/main_p3.py::_build_fig_best_table``
唯一消费。
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import plotly.graph_objects as go


_TABLE_HEIGHT_PX = 200
_ROW_HEIGHT_PX = 34
_FALLBACK = "—"
_DEFAULT_BEST_MODEL = "naive"


# --------------------------------------------------------------------------- #
# 私有 helper                                                                  #
# --------------------------------------------------------------------------- #


def _fmt_number(v: Any) -> str:
    """把任意数值格式化为 6 位小数；NaN / None / 异常 → ``"—"``。"""
    try:
        x = float(v)
    except (TypeError, ValueError):
        return _FALLBACK
    if not math.isfinite(x):
        return _FALLBACK
    return f"{x:.6f}"


def _resolve_best_mu_sigma(
    sym: str,
    model_key: str,
    model_mu: Dict[str, Any],
    model_sigma: Dict[str, Any],
    model_mu_test_ts: Optional[Dict[str, Any]],
    model_sigma_test_ts: Optional[Dict[str, Any]],
) -> Tuple[Any, Any]:
    """取胜者模型在 OOS 末日的 (μ̂, σ̂)；时序缺失时回退全样本标量字典。

    与 ``dash_app/ui/main_p2.py::_p2_mu_sigma_table`` 的取值顺序保持一致。
    """
    mu: Any = None
    sg: Any = None
    if model_mu_test_ts and model_sigma_test_ts:
        ts_m = (model_mu_test_ts.get(model_key) or {}).get(sym) or []
        ts_s = (model_sigma_test_ts.get(model_key) or {}).get(sym) or []
        if ts_m and ts_s:
            mu, sg = ts_m[-1], ts_s[-1]
    if mu is None:
        mu = (model_mu.get(model_key) or {}).get(sym)
        sg = (model_sigma.get(model_key) or {}).get(sym)
    return mu, sg


def _palette(template: str) -> Dict[str, str]:
    """根据 Plotly 模板名推断明/暗色；输出 borderless 表格所需 4 种颜色。"""
    is_dark = isinstance(template, str) and "dark" in template.lower()
    return {
        "label_fg": "#cfd8dc" if is_dark else "#37474f",
        "value_fg": "#e0f2f1" if is_dark else "#1b1b1f",
        "row_bg_a": "rgba(255,255,255,0.04)" if is_dark else "rgba(0,0,0,0.04)",
        "row_bg_b": "rgba(0,0,0,0)",
    }


def _collect_rows(
    symbols: Sequence[str],
    best_model_per_symbol: Dict[str, str],
    model_mu: Dict[str, Any],
    model_sigma: Dict[str, Any],
    model_mu_test_ts: Optional[Dict[str, Any]],
    model_sigma_test_ts: Optional[Dict[str, Any]],
) -> Tuple[List[str], List[str], List[str]]:
    """把三行内容（标的 / μ̂ / σ̂）组装成字符串列表。"""
    syms: List[str] = [str(s) for s in symbols if s]
    mu_row: List[str] = []
    sg_row: List[str] = []
    bm_map = best_model_per_symbol or {}
    mu_map = model_mu or {}
    sg_map = model_sigma or {}
    for s in syms:
        m = str(bm_map.get(s) or _DEFAULT_BEST_MODEL)
        mu, sg = _resolve_best_mu_sigma(
            s, m, mu_map, sg_map, model_mu_test_ts, model_sigma_test_ts,
        )
        mu_row.append(_fmt_number(mu))
        sg_row.append(_fmt_number(sg))
    return syms, mu_row, sg_row


def _empty_figure(template: str) -> go.Figure:
    return go.Figure(
        layout=dict(
            template=template,
            height=_TABLE_HEIGHT_PX,
            margin=dict(l=8, r=8, t=8, b=8),
            annotations=[
                dict(
                    text="暂无可用的最佳模型 μ̂ / σ̂",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    font=dict(size=12, color="#9aa0a6"),
                )
            ],
        )
    )


def _build_borderless_table(
    syms: List[str],
    mu_row: List[str],
    sg_row: List[str],
    palette: Dict[str, str],
) -> go.Table:
    """构造 borderless 3×(1+N) 表格：首列=行名，其余 N 列=每标的数值。"""
    label_fg = palette["label_fg"]
    value_fg = palette["value_fg"]
    row_bg_a = palette["row_bg_a"]
    row_bg_b = palette["row_bg_b"]

    row_labels: List[str] = ["标的", "μ̂（最佳模型）", "σ̂（最佳模型）"]
    row_values: Tuple[List[str], List[str], List[str]] = (syms, mu_row, sg_row)

    first_col = row_labels
    symbol_cols: List[List[str]] = [
        [row_values[r][c] for r in range(3)] for c in range(len(syms))
    ]

    row_fills = [row_bg_a, row_bg_b, row_bg_a]

    # Plotly ≥6.0 tightened ``cells.font.size`` / ``cells.font.color`` to a
    # 1-D list (一个长度 = 列数的列表，每个条目作用于该整列所有行)，不再接受
    # 旧版 ``[[14,14,14], [12,12,12], ...]`` 的嵌套结构（会直接抛
    # ``ValueError: Invalid element(s) received for the 'size' property``）。
    # 本表每列所有行本来就同字号/同色，所以扁平化即是正解。
    font_color: List[str] = [label_fg] + [value_fg] * len(syms)
    font_size: List[int] = [14] + [12] * len(syms)
    cell_fill: List[List[str]] = [row_fills] * (1 + len(syms))

    return go.Table(
        columnwidth=[120] + [60] * len(syms),
        header=dict(
            values=[""] * (1 + len(syms)),
            fill_color="rgba(0,0,0,0)",
            line_color="rgba(0,0,0,0)",
            height=0,
        ),
        cells=dict(
            values=[first_col] + symbol_cols,
            align=["left"] + ["right"] * len(syms),
            fill_color=cell_fill,
            line_color="rgba(0,0,0,0)",
            font=dict(color=font_color, size=font_size),
            height=_ROW_HEIGHT_PX,
        ),
    )


# --------------------------------------------------------------------------- #
# 对外唯一接口                                                                 #
# --------------------------------------------------------------------------- #


def fig_p3_best_mu_sigma_table(
    best_model_per_symbol: Dict[str, str],
    model_mu: Dict[str, Any],
    model_sigma: Dict[str, Any],
    symbols: Sequence[str],
    template: str,
    *,
    model_mu_test_ts: Optional[Dict[str, Any]] = None,
    model_sigma_test_ts: Optional[Dict[str, Any]] = None,
    figure_title: Optional[str] = None,
) -> go.Figure:
    """Figure 3.1 · 三行无竖框小表：[标的 / μ̂_best / σ̂_best]。

    Args:
        best_model_per_symbol: ``{sym: model_key}``，Phase 2 影子胜者映射。
        model_mu: ``{model_key: {sym: μ̂}}``。
        model_sigma: ``{model_key: {sym: σ̂}}``。
        symbols: 列顺序；建议传 ``phase0.meta.symbols_resolved``。
        template: Plotly 模板名，用于明/暗色自适应。
        model_mu_test_ts: 可选；若给出，对每个胜者取 ``[-1]`` 即 OOS 末日。
        model_sigma_test_ts: 同上。
        figure_title: 占位参数，保持与本项目其它 ``fig_*`` 构造器签名形状一致
            （标题由 ``_figure_wrap`` 的 ``fig_label`` 外挂，本函数不使用）。

    Returns:
        ``go.Figure``：单一 ``go.Table`` trace；全部 border 透明，行高固定，
        首列为行名，其余列为标的。
    """
    del figure_title  # 外挂至 fig_label；保留参数以锁定签名形状

    syms, mu_row, sg_row = _collect_rows(
        symbols,
        best_model_per_symbol,
        model_mu,
        model_sigma,
        model_mu_test_ts,
        model_sigma_test_ts,
    )
    if not syms:
        return _empty_figure(template)

    palette = _palette(template)
    table = _build_borderless_table(syms, mu_row, sg_row, palette)

    return go.Figure(
        data=[table],
        layout=dict(
            template=template,
            height=_TABLE_HEIGHT_PX,
            margin=dict(l=8, r=8, t=8, b=8),
        ),
    )
