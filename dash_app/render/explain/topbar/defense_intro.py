"""顶栏三色 Level 0/1/2 介绍横排 — 从 ``defense_intro.md`` 加载后渲染为 Dash 组件。

**外部 API**（签名与原 ``figure_caption_service.render_defense_intro_alerts`` 一致）：
    render_defense_intro_alerts() -> list[dbc.Row]
"""

from __future__ import annotations

from typing import List


def render_defense_intro_alerts() -> list:
    """三色横排 Level 0 / 1 / 2 介绍（Feedback 要求 13）。"""
    import dash_bootstrap_components as dbc
    from dash import html

    from dash_app.services.copy import get_defense_intro

    data = get_defense_intro()
    cols: List = []
    for level_key, color in [("level0", "success"), ("level1", "warning"), ("level2", "danger")]:
        spec = data.get(level_key) or {}
        title = str(spec.get("title") or level_key)
        pretext = str(spec.get("pretext") or "")
        items = spec.get("items") or []
        cls = f"py-2 h-100 defense-traffic defense-traffic-{level_key.replace('level', 'l')}"
        children: list = [html.Div(html.Strong(title), className="mb-1")]
        if pretext:
            children.append(html.P(pretext, className="small mb-1"))
        if items:
            children.append(
                html.Ul(
                    [html.Li(str(it), className="small") for it in items],
                    className="small mb-0 ps-3",
                )
            )
        cols.append(dbc.Col(dbc.Alert(children, color=color, className=cls), xs=12, md=4))
    return [dbc.Row(cols, className="g-2 defense-intro-row")]
