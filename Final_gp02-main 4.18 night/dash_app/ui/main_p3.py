"""Main panel layout for Phase 3 (adaptive optimization, dual-track MC)."""

from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import dcc, html

from dash_app.render.explain import (
    P3_SECTION_31_ADAPTIVE_MD,
    P3_SECTION_32_DUAL_MC_MD,
)
from dash_app.ui.layout import (
    _analysis_card,
    _fig_explain_title,
    _figure_wrap,
    _placeholder_fig,
    _research_under_graph,
)
from dash_app.services.copy import get_app_label


def build_p3_adaptive_intro_column(body: str | None = None) -> Any:
    """P3 Figure3.2 左侧：AdaptiveOptimizer 介绍卡片。

    Args:
        body: 若为 None，使用启动时加载的 ``P3_SECTION_31_ADAPTIVE_MD``；
              模式切换回调会传入 ``p3_section_31_adaptive(mode)`` 的返回值以刷新。
    """
    src = body if body is not None else (P3_SECTION_31_ADAPTIVE_MD or "")
    src = src.strip()
    if len(src) > 1800:
        src = src[:1800] + "\n\n…"
    return dbc.Card(
        [
            dbc.CardHeader(
                get_app_label("p3_adaptive_header", "AdaptiveOptimizer 与三阶段防御"),
                className="py-2 small fw-bold",
            ),
            dbc.CardBody(
                dcc.Markdown(src, mathjax=True, className="mb-0 phase-doc-body small", style={"lineHeight": "1.65"}),
                className="py-2",
            ),
        ],
        className="border-secondary shadow-sm h-100 mb-2 mb-lg-0",
    )


def main_p3_panel() -> html.Div:
    """Return the full main-panel-p3 layout."""
    return html.Div(
        id="main-panel-p3",
        className="main-tab-panel",
        style={"display": "none"},
        children=[
            html.Div(id="objective-banner", className="mt-2"),
            html.P(
                get_app_label(
                    "p3_st_reuse_note",
                    "测试窗 S_t 与侧栏 FigX.1 同源；影子择模结果已移至 Phase 2 顶部展示。",
                ),
                className="small text-muted mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        # Mode-aware container: updated by `_caption_refresh_on_mode` callback
                        html.Div(
                            id="p3-adaptive-intro-card",
                            children=build_p3_adaptive_intro_column(),
                        ),
                        width=12,
                        className="mb-2",
                    ),
                ],
                className="g-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        _figure_wrap(
                            0,
                            [
                                dcc.Graph(
                                    id="fig-p3-best-table",
                                    figure=_placeholder_fig(),
                                    config={"displayModeBar": False},
                                    style={"height": "220px"},
                                    className="mb-2",
                                ),
                            ],
                            fig_label="Figure3.1",
                        ),
                        xs=12,
                        md={"size": 9, "offset": 0},
                        lg={"size": 8, "offset": 0},
                    ),
                ],
                className="g-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        _figure_wrap(
                            1,
                            [
                                dcc.Graph(
                                    id="fig-p3-weights",
                                    figure=_placeholder_fig(),
                                ),
                            ],
                            fig_label="Figure3.2",
                        ),
                        width=12,
                    ),
                ],
                className="g-2",
            ),
            _figure_wrap(
                2,
                [
                    dcc.Graph(
                        id="fig-p3-mc",
                        figure=_placeholder_fig(),
                    ),
                    # Mode-aware container: updated by `_mode_main_panel_refresh` callback
                    html.Div(
                        id="p3-fig33-explain-card",
                        children=_analysis_card(
                            _fig_explain_title(3, 3, get_app_label("p3_fig33_caption", "双轨蒙特卡洛")),
                            P3_SECTION_32_DUAL_MC_MD,
                        ),
                    ),
                ],
                fig_label="Figure3.3",
            ),
            html.Div(id="card-p3"),
        ],
    )
