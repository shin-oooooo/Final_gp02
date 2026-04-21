"""Sidebar 2 block visibility callback."""
from __future__ import annotations

from typing import Optional

from dash import Input, Output


def register_sidebar2_visibility_callbacks(app):
    @app.callback(
        Output("sb2-p1-block", "style"),
        Output("sb2-p2-block", "style"),
        Input("main-tab-store", "data"),
        prevent_initial_call=False,
    )
    def _sb2_blocks_visibility(tab: Optional[str]):
        show = {"display": "block"}
        hide = {"display": "none"}
        t = tab or "p0"
        if t in ("p0", "p3", "p4"):
            return show, show
        if t == "p1":
            return show, hide
        if t == "p2":
            return hide, show
        return show, show
