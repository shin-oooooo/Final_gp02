"""Main panel layout for Phase 1 (stationarity / Ljung-Box / group analysis)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from dash_app.render.explain import p1_stat_method
from dash_app.services.copy import get_figure_title
from dash_app.ui.layout import (
    _analysis_card,
    _figure_wrap,
    explain_title_from_figures,
)


def main_p1_panel() -> html.Div:
    """Return the full main-panel-p1 layout."""
    return html.Div(
        id="main-panel-p1",
        className="main-tab-panel",
        style={"display": "none"},
        children=[
            _figure_wrap(
                1,
                [
                    dbc.Row(
                        [
                            dbc.Col(html.Div(id="p1-asset-cards"), lg=5, width=12),
                            dbc.Col(html.Div(id="p1-group-analysis"), lg=7, width=12),
                        ],
                        className="mt-2 g-3",
                    ),
                    # Mode-aware container: updated by `_caption_refresh_on_mode` callback。
                    # 标题统一从 figures_titles.md 的 ``fig_1_1_explain`` / ``..._res`` 读取，
                    # 正文从 ``content-{LANG}/Inv/Fig1.1-Inv.md`` / ``Res-templates/Fig1.1-Res.md`` 加载。
                    html.Div(
                        id="p1-stat-method-card",
                        children=_analysis_card(
                            explain_title_from_figures(
                                "fig_1_1_explain", "invest", "Figure 1.1 讲解"
                            ),
                            p1_stat_method("invest"),
                            md_slot_id="p1-stat-method-md",
                        ),
                    ),
                ],
                fig_label=get_figure_title("fig_1_1", "Figure 1.1 · 分组诊断与失效前兆识别"),
            ),
            html.Div(id="card-p1", style={"display": "none"}),
        ],
    )
