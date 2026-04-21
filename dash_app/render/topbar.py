"""顶栏动态内容 — defense-intro-slot + reasons 同行横向展开。

**2 个槽位**：
* ``topbar-defense-intro-slot`` — 「防御策略介绍」Level 0 / 1 / 2 三色介绍横排，
  移到了 ``app-topbar-center`` 顶部（由 ``ui/topbar.py`` 负责布局位置）。
* ``topbar-defense-reasons-collapse`` —（id 沿用旧名）6 条 reason 的容器，
  **不再折叠**，由 ``ui/topbar.py`` 放在 "当前防御状态" 同一行内联展开。
  内容过滤策略：**严格**只保留与当前防御等级严重度相符的 tag：

  * Level 2 → 仅 severity=="danger"
  * Level 1 → 仅 severity=="warn"
  * Level 0 → 仅 severity=="success"

  相较侧栏使用的 ``_should_show_defense_tag``（"当前及以下等级"）更窄，
  精准反映"当前防御状态由哪几项条件触发"。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Tuple

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


def _severity_matches_level(severity: str, level: int) -> bool:
    """Strict match：把当前等级和 reason 的严重度一一对应。"""
    lvl = int(level or 0)
    sev = (severity or "").strip().lower()
    if lvl >= 2:
        return sev == "danger"
    if lvl == 1:
        return sev in ("warn", "warning")
    return sev == "success"


def _build_reasons_inline(
    raw_reasons: Dict[str, Tuple[Any, str]],
    defense_level: int,
) -> Any:
    """把 6 条 reason 按严重度严格过滤后，横向平铺成一行。

    设计：
    * 每条 reason 仍用 ``_div_from_fig_line``（与侧栏同一视觉风格）。
    * 顺序沿用 FigX.1 → FigX.6（即 st → h_struct → figx3 → consistency → jsd → cos）。
    * 如果过滤后为空，返回空 ``html.Div``（顶栏会看起来只剩一个 level badge）。
    """
    from dash_app.dash_ui_helpers import _div_from_fig_line

    order: List[str] = ["st", "h_struct", "figx3", "consistency", "jsd", "cos"]
    kept: List[Any] = []
    for key in order:
        pair = raw_reasons.get(key)
        if not pair:
            continue
        body, sev = pair
        if body is None:
            continue
        if not _severity_matches_level(sev, defense_level):
            continue
        kept.append(
            html.Div(
                _div_from_fig_line((body, sev)),
                className="topbar-reason-chip",
            )
        )

    if not kept:
        return html.Div()

    return html.Div(
        kept,
        className="topbar-reasons-inline d-flex flex-wrap align-items-center gap-2",
    )


def build_topbar_dynamic_components(
    state: DashboardState,
    *,
    raw_reasons: Dict[str, Tuple[Any, str]] | None = None,
) -> TopbarDynamicComponents:
    """构造顶栏动态组件。

    Args:
        state: 当前 dashboard state（用 ``defense_level`` 做严格严重度过滤）。
        raw_reasons: 由 ``render.sidebar_right`` 预先算好的 6 条原始
            ``(body, severity)`` 键值对（key ∈ ``{"st","h_struct","figx3",
            "consistency","jsd","cos"}``）。缺省时退回空内联块。
    """
    assert isinstance(state, DashboardState), "state must be DashboardState"
    _trace("build_topbar start level=%s", state.defense_level)

    raw = raw_reasons or {}
    out = TopbarDynamicComponents(
        defense_intro_slot=_build_defense_intro_slot(),
        reasons_collapse=_build_reasons_inline(raw, state.defense_level),
    )
    _trace("build_topbar done kept=%d", len(getattr(out.reasons_collapse, "children", []) or []))
    return out
