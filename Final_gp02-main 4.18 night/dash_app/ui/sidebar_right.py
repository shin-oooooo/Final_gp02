"""Right sidebar (sidebar2) UI components extracted from app.py."""

from __future__ import annotations

from typing import Any, Dict, List

import dash_bootstrap_components as dbc
from dash import dcc, html

from dash_app.services.copy import get_figure_title, get_status_message
from dash_app.render.explain import render_defense_intro_alerts
from dash_app.ui.layout import (
    _analysis_card,
    _figx_card_header,
    _placeholder_fig,
)
from dash_app.ui.metric_rails import credibility_rail, structural_entropy_rail


def _sidebar_defense_intro_alerts() -> list:
    """Level 2 / 1 / 0 说明块（侧栏卡片与侧栏2折叠内容共用）。"""
    return render_defense_intro_alerts()


def _collapsible_defense_strategy_intro(is_open: bool = False) -> html.Div:
    """主区顶部：防御策略介绍，可折叠。"""
    collapse_id = "defense-strategy-intro-collapse"
    btn_id = "btn-toggle-defense-strategy-intro"
    return html.Div(
        [
            dbc.Button(
                [
                    html.I(className="fa fa-shield-halved me-2"),
                    html.Span(get_status_message("defense_intro_card_title", "防御策略介绍"), className="fw-bold small"),
                    html.I(className="fa fa-chevron-down ms-2", id="defense-strategy-intro-chevron"),
                ],
                id=btn_id,
                color="link",
                className="text-start w-100 p-0 phase-card-header-title",
                n_clicks=0,
            ),
            dbc.Collapse(
                dbc.Card(
                    dbc.CardBody(
                        _sidebar_defense_intro_alerts(),
                        className="pt-2 pb-2",
                    ),
                    className="mb-2 border-secondary shadow-sm",
                ),
                id=collapse_id,
                is_open=is_open,
            ),
        ],
        className="mb-2",
    )


def _asset_anomaly_row(label: str, items: List[Dict[str, Any]], color: str) -> html.Div:
    """Create a row of small asset anomaly cards."""
    if items:
        cards = [
            dbc.Card(
                dbc.CardBody([
                    html.Div(item["symbol"], className="fw-bold"),
                    html.Div(item["value"], className="small text-muted"),
                ]),
                className=f"border-{color} shadow-none me-1 mb-1",
                style={"minWidth": "70px", "flex": "0 0 auto"},
            )
            for item in items
        ]
    else:
        cards = [html.Span("—", className="small text-muted")]
    return html.Div(
        [
            html.Div(label, className="small fw-bold mb-1 text-muted"),
            html.Div(cards, className="d-flex flex-wrap"),
        ],
        className="mb-2",
    )


def sidebar_right_column() -> dbc.Col:
    """Sidebar 2: Defense Dashboard column (extracted from app.py)."""
    return dbc.Col(
        [
            html.Div(
                className="sidebar-scroll-inner sidebar2-scroll-inner",
                style={"overflowY": "auto", "height": "100vh"},
                children=[
                    # FigX.1: S_t（由原主栏 Figure3.1 迁入）
                    dbc.Card([
                        _figx_card_header(get_figure_title("fig_x_1", "FigX.1 · S_t 情绪路径")),
                        dbc.CardBody([
                            dcc.Graph(id="sb2-fig-st", figure=_placeholder_fig(get_status_message("placeholder_st", "S_t")), config={"displayModeBar": False}, style={"height": "280px"}),
                            html.Div(id="sb2-fig-st-reason", className="mt-2 sb2-figx-reason-below"),
                            html.Div(
                                id="sb2-explain-slot-01",
                                children=[
                                    _analysis_card(
                                        get_figure_title("fig_x_1_explain", "FigX.1 讲解：测试窗 S_t（VADER 分段累积）"),
                                        get_status_message("idle_placeholder", "未运行：占位预览。"),
                                    ),
                                ],
                            ),
                        ], className="p-2"),
                    ], className="mb-2 border-secondary shadow-sm"),
                    # FigX.2: 结构熵（由原主栏 Figure1.1 迁入）
                    html.Div(
                        id="sb2-p1-block",
                        children=[
                            dbc.Card([
                                _figx_card_header(get_figure_title("fig_x_2", "FigX.2 · 结构熵")),
                                dbc.CardBody([
                                    html.Div(
                                        id="sb2-fig-h-struct",
                                        children=structural_entropy_rail(0.0, 0.5, show_marker=False),
                                        className="sb2-metric-rail-wrap",
                                    ),
                                    html.Div(id="sb2-fig-h-struct-reason", className="mt-2 sb2-figx-reason-below"),
                                    html.Div(
                                        id="sb2-explain-slot-02",
                                        children=[
                                            _analysis_card(
                                                get_figure_title("fig_x_2_explain", "FigX.2 讲解：结构熵与 Level 判定"),
                                                get_status_message("idle_placeholder", "未运行：占位预览。"),
                                            ),
                                        ],
                                    ),
                                ], className="p-2"),
                            ], className="mb-2 border-secondary shadow-sm"),
                        ],
                    ),
                    # FigX.3: 资产异常卡片（高波动 + 低 AC1）
                    html.Div(
                        id="sb2-p1-vol-ac1-block",
                        children=[
                            dbc.Card([
                                _figx_card_header(get_figure_title("fig_x_3", "FigX.3 · 资产异常诊断")),
                                dbc.CardBody([
                                    html.Div(id="sb2-fig-vol-ac1-cards", children=[]),
                                    html.Div(id="sb2-fig-vol-ac1-reason", className="mt-2 sb2-figx-reason-below"),
                                    html.Div(
                                        id="sb2-explain-slot-03",
                                        children=[
                                            _analysis_card(
                                                get_figure_title("fig_x_3_explain", "FigX.3 讲解：高波动与低自相关资产"),
                                                get_status_message("idle_placeholder", "未运行：占位预览。"),
                                            ),
                                        ],
                                    ),
                                ], className="p-2"),
                            ], className="mb-2 border-secondary shadow-sm"),
                        ],
                    ),
                    # FigX.4–6: P2 防御条带（一致性 / JSD / 余弦由原主栏对应块迁入）
                    html.Div(
                        id="sb2-p2-block",
                        children=[
                            dbc.Card([
                                _figx_card_header(get_figure_title("fig_x_4", "FigX.4 · 一致性 + 三态灯")),
                                dbc.CardBody([
                                    html.Div(
                                        id="sb2-fig-consistency",
                                        children=credibility_rail(0.0, 0.45, 0.70, show_marker=False),
                                        className="sb2-metric-rail-wrap",
                                    ),
                                    html.Div(id="sb2-fig-consistency-reason", className="mt-2 sb2-figx-reason-below"),
                                    html.Div(id="sb2-p2-traffic-lights", className="mt-2"),
                                    html.Div(
                                        id="sb2-explain-slot-04",
                                        children=[
                                            _analysis_card(
                                                get_figure_title("fig_x_4_explain", "FigX.4 讲解：可信度评分与三态灯"),
                                                get_status_message("idle_placeholder", "未运行：占位预览。"),
                                            ),
                                        ],
                                    ),
                                ], className="p-2"),
                            ], className="mb-2 border-secondary shadow-sm"),
                            dbc.Card([
                                _figx_card_header(get_figure_title("fig_x_5", "FigX.5 · 模型—模型应力检验")),
                                dbc.CardBody([
                                    dcc.Graph(id="sb2-fig-jsd-stress", figure=_placeholder_fig(get_status_message("placeholder_jsd", "JSD 应力")), config={"displayModeBar": False}, style={"height": "300px"}),
                                    html.Div(id="sb2-fig-jsd-stress-reason", className="mt-2 sb2-figx-reason-below"),
                                    html.Div(
                                        id="sb2-explain-slot-05",
                                        children=[
                                            _analysis_card(
                                                get_figure_title("fig_x_5_explain", "FigX.5 讲解：模型—模型应力检验"),
                                                get_status_message("figx_run_prompt", "请点击顶栏「**保存运行**」；此处载入 `FigX.5-Inv.md` / `FigX.5-Res.md` 并注入占位符。").format(md_inv="FigX.5-Inv.md", md_res="FigX.5-Res.md"),
                                            ),
                                        ],
                                    ),
                                ], className="p-2"),
                            ], className="mb-2 border-secondary shadow-sm"),
                            dbc.Card([
                                _figx_card_header(get_figure_title("fig_x_6", "FigX.6 · 语义背离余弦")),
                                dbc.CardBody([
                                    dcc.Graph(id="sb2-fig-cosine", figure=_placeholder_fig(get_status_message("placeholder_cosine", "语义背离")), config={"displayModeBar": False}, style={"height": "300px"}),
                                    html.Div(id="sb2-fig-cosine-reason", className="mt-2 sb2-figx-reason-below"),
                                    html.Div(
                                        id="sb2-explain-slot-06",
                                        children=[
                                            _analysis_card(
                                                get_figure_title("fig_x_6_explain", "FigX.6 讲解：语义–数值滚动余弦"),
                                                get_status_message("figx_run_prompt", "请点击顶栏「**保存运行**」；此处载入 `FigX.6-Inv.md` / `FigX.6-Res.md` 并注入占位符。").format(md_inv="FigX.6-Inv.md", md_res="FigX.6-Res.md"),
                                            ),
                                        ],
                                    ),
                                ], className="p-2"),
                            ], className="mb-2 border-secondary shadow-sm"),
                        ],
                    ),
                ],
            ),
        ],
        xs=12, md=5, lg=5,
        className="mb-0 order-2 order-lg-2 sidebar2-col dash-three-col",
        style={"overflowY": "auto", "height": "100vh"},
    )
