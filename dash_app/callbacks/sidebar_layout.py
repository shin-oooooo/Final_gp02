"""Sidebar layout callbacks."""
from typing import Any

from dash import Input, Output, State


def register_sidebar_layout_callbacks(app):
    @app.callback(
        Output("sidebar1-collapsed", "data"),
        Input("btn-sidebar1-toggle", "n_clicks"),
        State("sidebar1-collapsed", "data"),
        prevent_initial_call=True,
    )
    def _toggle_sidebar1_collapsed(_n: int, cur: Any) -> bool:
        return not bool(cur)

    @app.callback(
        Output("btn-sidebar1-toggle", "children"),
        Output("dash-body-three-col-row", "className"),
        Output("sidebar1-col", "className"),
        Input("sidebar1-collapsed", "data"),
    )
    def _sync_sidebar1_layout(collapsed: Any) -> tuple[Any, str, str]:
        c = bool(collapsed)
        icon = ">>" if c else "<<"
        row = "g-0 align-items-stretch dashboard-three-col-row app-body-row"
        if c:
            row += " sidebar1-is-collapsed"
        col = "mb-0 order-3 order-lg-1 sidebar1-col dash-three-col h-100"
        if c:
            col += " sidebar1-col--collapsed"
        return icon, row, col
