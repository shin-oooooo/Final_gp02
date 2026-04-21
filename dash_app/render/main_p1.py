"""主栏 P1 渲染 — 资产诊断卡片网格 + 分组分析。

**3 个槽位**：p1-asset-cards, card-p1, p1-group-analysis
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Tuple

import dash_bootstrap_components as dbc
from dash import dcc, html

from dash_app.render.contracts import DashboardState, MainP1Components

logger = logging.getLogger("dash_app.render.main_p1")
_TRACE = os.environ.get("DEBUG_RENDER", "0").strip() not in ("", "0", "false", "False")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if _TRACE:
        try:
            print(f"[main_p1] {msg % args}" if args else f"[main_p1] {msg}")
        except Exception:
            pass


def _classify_diagnostic(d: Dict[str, Any]) -> Tuple[str, str, str, str]:
    """把一个诊断字典分类为 (border_cls, body_cls, headline, badge_col)。"""
    level_ok = bool(d.get("stationary_returns"))
    lpv = bool(d.get("low_predictive_value"))
    fail = bool(d.get("basic_logic_failure"))

    if fail:
        return "border-danger", "bg-danger bg-opacity-10", "非平稳或逻辑失败 · 不可建模", "danger"
    if level_ok and not lpv:
        return "border-success", "bg-success bg-opacity-10", "平稳 · 存在可建模结构", "success"
    if level_ok and lpv:
        return "border-warning", "bg-warning bg-opacity-10", "平稳 · 残差近白噪声（弱规律）", "warning"
    return "border-danger", "bg-danger bg-opacity-10", "非平稳 · 需差分或进一步检验", "danger"


def _build_diagnostic_card(d: Dict[str, Any]) -> Any:
    """单个资产诊断卡。"""
    from dash_app.services.copy import get_status_message
    from dash_app.ui.layout import _fmt_p

    assert isinstance(d, dict), f"d must be dict, got {type(d).__name__}"

    sym = d.get("symbol", "?")
    adf_lr = float(d.get("adf_p", 1.0))
    lb = d.get("ljung_box_p")
    adf_fin = float(d.get("adf_p_returns", 1.0))
    diff_o = int(d.get("diff_order") or 0)
    border_cls, body_cls, headline, badge_col = _classify_diagnostic(d)

    badge = dbc.Badge(headline, color=badge_col, className="mb-2", style={"whiteSpace": "normal"})
    return dbc.Col(
        dbc.Card(
            dbc.CardBody(
                [
                    html.H6(sym, className="card-title mb-2"),
                    badge,
                    html.P(
                        [html.Strong(get_status_message("adf_log_p", "ADF 对数收益 p: ")),
                         _fmt_p(adf_lr)],
                        className="small mb-1",
                    ),
                    html.P(
                        [html.Strong(get_status_message("diff_order_adf_p", "差分阶 / ADF(终) p: ")),
                         f"{diff_o} / ", _fmt_p(adf_fin)],
                        className="small mb-1 text-muted",
                    ),
                    html.P(
                        [html.Strong("Ljung–Box p: "), _fmt_p(lb)],
                        className="small mb-0",
                    ),
                ],
                className=body_cls,
            ),
            className=f"h-100 {border_cls}",
        ),
        width=6, md=4, lg=6, className="mb-2",
    )


def _build_p1_grid(diagnostics: List[Dict[str, Any]]) -> Any:
    """Phase 1 诊断卡片网格。"""
    assert isinstance(diagnostics, list), "diagnostics must be list"
    _trace("grid building %d diag cards", len(diagnostics))
    return dbc.Row([_build_diagnostic_card(d) for d in diagnostics], className="g-2")


def _build_p1_group_analysis(state: DashboardState) -> Any:
    """逐资产分析 + 整体结论卡片。"""
    from dash_app.render.explain import narrative_p1_group_analysis
    from dash_app.services.copy import get_status_message

    p1_group_md = narrative_p1_group_analysis(state.p1)
    return dbc.Card(
        [
            dbc.CardHeader(
                html.Span(
                    get_status_message("per_asset_analysis_title", "逐资产分析与整体结论"),
                    className="phase-card-header-title",
                ),
                className="border-primary bg-transparent py-2",
            ),
            dbc.CardBody(
                dcc.Markdown(
                    p1_group_md, mathjax=True,
                    className="mb-0 phase-doc-body", style={"lineHeight": "1.8"},
                ),
                className="pt-2 pb-3",
            ),
        ],
        className="shadow-sm border-primary border-opacity-50 phase-text-panel",
    )


def build_main_p1_components(state: DashboardState) -> MainP1Components:
    """构造主栏 P1 组件。纯函数。"""
    assert isinstance(state, DashboardState), (
        f"state must be DashboardState, got {type(state).__name__}"
    )
    _trace("build_main_p1 start diagnostics=%d", len(state.diagnostics))

    out = MainP1Components(
        p1_grid=_build_p1_grid(state.diagnostics),
        card_p1=html.Div(),                    # 结构熵仪表盘已迁至 FigX.2 → sidebar_right
        p1_group_analysis=_build_p1_group_analysis(state),
    )
    _trace("build_main_p1 done")
    return out
