"""Main panel layout for Phase 0 (asset universe, weights, correlation, beta)."""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

import dash_bootstrap_components as dbc
from dash import dcc, html

from dash_app.ui.layout import (
    _figure_wrap,
    _placeholder_fig,
)
from dash_app.constants import _CAT_LABELS
from dash_app.services.copy import get_app_label, get_figure_title, get_status_message
_CAT_COLORS = {"tech": "#4fc3f7", "hedge": "#ffa726", "safe": "#66bb6a", "benchmark": "#b0bec5"}
_CATS = ["tech", "hedge", "safe", "benchmark"]

_EXTRA_COLORS = ["#90a4ae", "#ba68c8", "#4dd0e1", "#ffcc80", "#a5d6a7"]


# ---------------------------------------------------------------------------
# Helpers used ONLY by the p0 layout / p0 callbacks
# ---------------------------------------------------------------------------
def _universe_extra_color(i: int) -> str:
    return _EXTRA_COLORS[i % len(_EXTRA_COLORS)]


def _cat_header_dimmed(cat: str, syms_in_cat: List[str], strike_syms: Set[str], strike_cats: Set[str]) -> bool:
    """类标题变暗 iff 该类下每一行都处于划线态（整类划线或单标的全员划线）。"""
    su = [str(s).upper() for s in syms_in_cat]
    if not su:
        return False
    cat_broad = cat in strike_cats
    return all((s in strike_syms or cat_broad) for s in su)


def _p0_diag_line(sym: str, diag_map: Dict[str, Dict[str, Any]]) -> Tuple[str, str]:
    """Return (one-line status, badge color) for 平稳 × 规律 四象限。文案由 ``all_labels.md`` 提供。"""
    d = diag_map.get(sym)
    if not d:
        return get_app_label("diag_pending", "待诊断"), "secondary"
    ok = bool(d.get("stationary_returns"))
    lpv = bool(d.get("low_predictive_value"))
    fail = bool(d.get("basic_logic_failure"))
    if fail:
        return get_app_label("diag_nonstat_or_logic_fail", "非平稳或逻辑失败 · 不可作为建模前提"), "danger"
    if ok and not lpv:
        return get_app_label("diag_stable_structure", "平稳 · 存在可建模结构（拒绝纯噪声）"), "success"
    if ok and lpv:
        return get_app_label("diag_stable_weak", "平稳 · 残差近白噪声（弱规律）"), "warning"
    return get_app_label("diag_nonstat_needs_diff", "非平稳 · 需差分或进一步检验"), "danger"


def _p0_slim_asset_row(
    sym: str,
    cat: str,
    weight: float,
    diag_map: Dict[str, Dict[str, Any]],
    *,
    struck: bool,
    color: str,
) -> html.Div:
    line, badge_c = _p0_diag_line(sym, diag_map)
    row_style: Dict[str, Any] = {"textDecoration": "line-through", "opacity": 0.55} if struck else {}
    return html.Div(
        [
            html.Div(className="p0-slim-bar", style={"background": color}),
            html.Div(
                [
                    html.Button(
                        html.I(className="fa fa-crosshairs"),
                        id={"type": "p0-sym-select", "sym": sym},
                        n_clicks=0,
                        type="button",
                        title=get_status_message("p0_btn_pie_title", "选为当前调整标的（与饼图联动）"),
                        className="btn btn-sm btn-outline-secondary py-0 px-1 me-1 p0-sym-select-btn",
                    ),
                    html.Button(
                        id={"type": "p0-sym-row", "sym": sym},
                        n_clicks=0,
                        type="button",
                        className="p0-slim-row-hit btn btn-link text-start p-0 flex-grow-1 text-decoration-none",
                        style=row_style,
                        children=[
                            html.Span(sym, className="mono fw-bold me-2"),
                            dbc.Badge(line, color=badge_c, className="me-1 p0-diag-pill"),
                            html.Span(
                                get_status_message("p0_weight_tooltip", "权重 {weight}（右侧饼图调整）").format(weight=f"{weight:.1%}"),
                                className="small text-muted",
                            ),
                        ],
                    ),
                ],
                className="p0-slim-body flex-grow-1",
            ),
        ],
        className="p0-slim-card d-flex mb-1",
    )


def _build_p0_asset_tree(
    universe: Dict[str, Any],
    order: List[str],
    weights: Dict[str, float],
    diag_map: Dict[str, Dict[str, Any]],
    strike_syms: set,
    strike_cats: set,
) -> html.Div:
    blocks: List[Any] = []
    for cat in _CATS:
        val = universe.get(cat)
        cat_syms = val if isinstance(val, list) else ([val] if isinstance(val, str) and val else [])
        syms = [s for s in cat_syms if s in order]
        if not syms:
            continue
        color = _CAT_COLORS.get(cat, "#78909c")
        cat_struck = cat in strike_cats
        cat_hdr_dim = _cat_header_dimmed(cat, syms, strike_syms, strike_cats)
        cat_hdr_style = {"textDecoration": "line-through", "opacity": 0.55} if cat_hdr_dim else {}
        blocks.append(
            html.Div(
                [
                    html.Button(
                        id={"type": "p0-cat-row", "cat": cat},
                        n_clicks=0,
                        type="button",
                        className="p0-tree-cat mb-1 p0-slim-row-hit btn btn-link text-start p-0 w-100 text-decoration-none",
                        style=cat_hdr_style,
                        children=[
                            html.I(className="fa fa-folder-tree me-2", style={"color": color}),
                            html.Span(_CAT_LABELS.get(cat, cat), className="fw-bold small"),
                            html.Span(f"（{len(syms)}）", className="small text-muted ms-1"),
                        ],
                    ),
                    html.Div(
                        [
                            _p0_slim_asset_row(
                                sym, cat, weights.get(sym, 0.0), diag_map,
                                struck=(sym in strike_syms or cat_struck),
                                color=color,
                            )
                            for sym in syms
                        ],
                        className="p0-tree-assets ms-2 ps-2 border-start",
                        style={"borderColor": color},
                    ),
                ],
                className="mb-2",
            )
        )
    extra = universe.get("extra") or {}
    if isinstance(extra, dict):
        for i, (gname, syms_raw) in enumerate(extra.items()):
            if not isinstance(syms_raw, list):
                continue
            syms = [str(s).upper() for s in syms_raw if s and str(s).upper() in order]
            if not syms:
                continue
            color = _universe_extra_color(i)
            gk = f"extra:{gname}"
            cat_struck = gk in strike_cats
            cat_hdr_dim = _cat_header_dimmed(gk, syms, strike_syms, strike_cats)
            cat_hdr_style = {"textDecoration": "line-through", "opacity": 0.55} if cat_hdr_dim else {}
            blocks.append(
                html.Div(
                    [
                        html.Button(
                            id={"type": "p0-cat-row", "cat": gk},
                            n_clicks=0,
                            type="button",
                            className="p0-tree-cat mb-1 p0-slim-row-hit btn btn-link text-start p-0 w-100 text-decoration-none",
                            style=cat_hdr_style,
                            children=[
                                html.I(className="fa fa-folder-tree me-2", style={"color": color}),
                                html.Span(gname, className="fw-bold small"),
                                html.Span(f"（{len(syms)}）", className="small text-muted ms-1"),
                            ],
                        ),
                        html.Div(
                            [
                                _p0_slim_asset_row(
                                    sym, gk, weights.get(sym, 0.0), diag_map,
                                    struck=(sym in strike_syms or cat_struck),
                                    color=color,
                                )
                                for sym in syms
                            ],
                            className="p0-tree-assets ms-2 ps-2 border-start",
                            style={"borderColor": color},
                        ),
                    ],
                    className="mb-2",
                )
            )
    if not blocks:
        return html.Div(get_status_message("no_asset_config", "暂无资产配置"), className="small text-muted")
    return html.Div(
        [
            html.P(
                get_status_message("p0_asset_guide", "左侧：资产与统计指示灯（点击行可划线；「应用」按划线重算；红钮「删除资产」永久移除划线项）。"
                "组合权重默认为等权，请在右侧饼图调整。"),
                className="small text-muted mb-2",
            ),
            html.Div(blocks),
        ],
        className="p0-asset-tree",
    )


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------
def main_p0_panel() -> html.Div:
    """Return the full main-panel-p0 layout."""
    return html.Div(
        id="main-panel-p0",
        className="main-tab-panel",
        style={"display": "block"},
        children=[
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            dbc.Button(get_status_message("btn_add_asset", "新增资产"), id="btn-p0-add-asset", color="success", size="sm", className="w-100"),
                                            xs=6, md=6,
                                        ),
                                        dbc.Col(
                                            dbc.Button(get_status_message("btn_remove_assets", "删除资产"), id="btn-p0-remove-assets", color="danger", size="sm", className="w-100"),
                                            xs=6, md=6,
                                        ),
                                    ],
                                    className="g-2 mb-1",
                                ),
                                html.P(
                                    get_status_message("p0_strike_hint", "划线表示暂不参与组合；侧栏「应用」按当前划线重算诊断与图表；「删除资产」则从组合永久移除划线项。"),
                                    className="small text-muted mb-2",
                                ),
                                html.Div(id="p0-assets"),
                            ],
                            className="invest-interpretation-block h-100",
                        ),
                        width=12,
                    ),
                ],
                className="g-3 mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        _figure_wrap(
                            0,
                            [
                                dcc.Graph(
                                    id="fig-p0-pie",
                                    figure=_placeholder_fig(get_status_message("p0_placeholder_pie", "组合权重（默认可调）")),
                                    config={"displayModeBar": False},
                                ),
                                html.P(
                                    get_status_message("p0_pie_hint", "默认等权；点击扇区选定标的后可多次拖动滑块，再点击其它扇区或左侧准星更换标的。"),
                                    className="small text-muted mb-1 invest-interpretation-block",
                                ),
                                html.Div(id="p0-pie-target-label", className="small mb-1 invest-interpretation-block"),
                                html.Div(
                                    dcc.Slider(
                                        id="p0-pie-slider",
                                        min=0.0,
                                        max=1.0,
                                        step=0.005,
                                        value=0.1,
                                        className="p0-weight-panel",
                                        updatemode="mouseup",
                                        tooltip=None,
                                    ),
                                    className="invest-interpretation-block",
                                ),
                            ],
                            fig_label=get_figure_title("fig_0_1", "Figure 0.1 · 组合权重饼图"),
                        ),
                        width=12,
                    ),
                ],
                className="g-3 mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        _figure_wrap(
                            1,
                            [
                                dcc.Graph(
                                    id="fig-p0-corr",
                                    figure=_placeholder_fig(),
                                ),
                            ],
                            fig_label=get_figure_title("fig_0_2", "Figure 0.2 · 相关性热力图"),
                        ),
                        id="p0-corr-col",
                        width=12,
                    ),
                ],
                className="g-3 mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(id="p0-heatmap-text"),
                        id="p0-heatmap-text-col",
                        width=12,
                        className="invest-interpretation-block",
                    ),
                ],
                className="g-3 mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        _figure_wrap(
                            2,
                            [
                                dcc.Graph(
                                    id="fig-p0-beta",
                                    figure=_placeholder_fig(),
                                ),
                            ],
                            fig_label=get_figure_title("fig_0_3", "Figure 0.3 · Beta 分布与区制对比"),
                        ),
                        id="p0-beta-col",
                        width=12,
                    ),
                ],
                className="g-3 mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(id="p0-beta-text-stack"),
                        id="p0-beta-text-col",
                        width=12,
                        className="invest-interpretation-block",
                    ),
                ],
                className="g-3 mb-2",
            ),
            html.Div(
                html.Div(id="p0-asset-class-analysis"),
                className="mb-2 invest-interpretation-block",
            ),
            html.Div(id="about-phase0-logic", className="mb-2 invest-interpretation-block"),
        ],
    )
