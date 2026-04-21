"""顶栏动态内容 — defense-intro-slot + reasons-collapse。

**2 个槽位**：
* ``topbar-defense-intro-slot`` — 三色 Level 0/1/2 介绍横排
* ``topbar-defense-reasons-collapse`` — 6 条 reason 横向展开（复用 sidebar 2 的 6 条 reason）
"""

from __future__ import annotations

import logging
import os
from typing import Any

import dash_bootstrap_components as dbc
from dash import html

from dash_app.render.contracts import DashboardState, TopbarDynamicComponents

logger = logging.getLogger("dash_app.render.topbar")
_TRACE = os.environ.get("DEBUG_RENDER", "0").strip() not in ("", "0", "false", "False")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if _TRACE:
        try:
            print(f"[topbar] {msg % args}" if args else f"[topbar] {msg}")
        except Exception:
            pass


def _build_defense_intro_slot() -> Any:
    """Level 0 / 1 / 2 三色介绍横排。"""
    from dash_app.ui.sidebar_right import _collapsible_defense_strategy_intro

    return _collapsible_defense_strategy_intro()


def _build_reasons_collapse(
    sb2_st: Any,
    sb2_h_struct: Any,
    figx3_reason: Any,
    sb2_consistency: Any,
    sb2_jsd: Any,
    sb2_cos: Any,
) -> Any:
    """把 6 条 reason 横向排列。参数顺序严格与 FigX.1~6 对应。"""
    return html.Div(
        dbc.Row(
            [
                dbc.Col(sb2_st,          xs=12, sm=6, md=4, lg=2, className="mb-1"),
                dbc.Col(sb2_h_struct,    xs=12, sm=6, md=4, lg=2, className="mb-1"),
                dbc.Col(figx3_reason,    xs=12, sm=6, md=4, lg=2, className="mb-1"),
                dbc.Col(sb2_consistency, xs=12, sm=6, md=4, lg=2, className="mb-1"),
                dbc.Col(sb2_jsd,         xs=12, sm=6, md=4, lg=2, className="mb-1"),
                dbc.Col(sb2_cos,         xs=12, sm=6, md=4, lg=2, className="mb-1"),
            ],
            className="g-1 topbar-reasons-row",
        ),
        className="topbar-reasons-container mt-2",
    )


def build_topbar_dynamic_components(
    state: DashboardState,
    *,
    sb2_st_reason: Any,
    sb2_h_struct_reason: Any,
    figx3_reason: Any,
    sb2_consistency_reason: Any,
    sb2_jsd_reason: Any,
    sb2_cos_reason: Any,
) -> TopbarDynamicComponents:
    """构造顶栏动态组件。

    6 条 reason 由 ``sidebar_right`` 先算好传入；本函数只做横向布局。
    """
    assert isinstance(state, DashboardState), "state must be DashboardState"
    _trace("build_topbar start")

    out = TopbarDynamicComponents(
        defense_intro_slot=_build_defense_intro_slot(),
        reasons_collapse=_build_reasons_collapse(
            sb2_st_reason, sb2_h_struct_reason, figx3_reason,
            sb2_consistency_reason, sb2_jsd_reason, sb2_cos_reason,
        ),
    )
    _trace("build_topbar done")
    return out
