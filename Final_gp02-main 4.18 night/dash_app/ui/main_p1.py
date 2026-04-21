"""Main panel layout for Phase 1 (stationarity / Ljung-Box / group analysis)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

from dash_app.render.explain import P1_STAT_METHOD_MD
from dash_app.services.copy import get_app_label
from dash_app.ui.layout import (
    _analysis_card,
    _fig_explain_title,
    _figure_wrap,
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
                    # Mode-aware container: updated by `_mode_main_panel_refresh` callback
                    html.Div(
                        id="p1-stat-method-card",
                        children=_analysis_card(
                            _fig_explain_title(1, 1, get_app_label(
                                "p1_stat_method_caption",
                                "统计方法说明（ADF / Ljung-Box / P 值含义）",
                            )),
                            P1_STAT_METHOD_MD,
                        ),
                    ),
                ],
                fig_label="Figure1.1",
            ),
            html.Div(id="card-p1", style={"display": "none"}),
        ],
    )
