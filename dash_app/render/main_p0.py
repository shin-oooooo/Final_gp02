"""主栏 P0 渲染 — 资产相关性 / Beta / 环境报告。

**7 个槽位**（对应 ``ui/main_p0.py`` 骨架）：
header-status, fig-p0-corr, fig-p0-beta,
p0-heatmap-text, p0-beta-text-stack, p0-asset-class-analysis,
about-phase0-logic

历史上的 ``diagnostic-summary``（系统级诊断 headline）与 ``p0-noise-level``
（Defense-Tag 噪声级说明）已从主栏删除，等价信息由顶栏 defense-tag +
侧栏 FigX 诊断承担，避免重复显示。
"""

from __future__ import annotations

import logging
import os
from typing import Any

import dash_bootstrap_components as dbc
from dash import dcc, html

from dash_app.render.contracts import DashboardState, MainP0Components

logger = logging.getLogger("dash_app.render.main_p0")
_TRACE = os.environ.get("DEBUG_RENDER", "0").strip() not in ("", "0", "false", "False")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if _TRACE:
        try:
            print(f"[main_p0] {msg % args}" if args else f"[main_p0] {msg}")
        except Exception:
            pass


def _build_fig_correlation(state: DashboardState) -> Any:
    from dash_app.figures import fig_correlation_heatmap

    corr_src = state.env.get("train_corr_preview") or {}
    return fig_correlation_heatmap(
        corr_src, state.symbols, state.tpl,
        tech=state.tech_m, hedge=state.hedge_m, safe=state.safe_m,
        cross_threshold=0.3, benchmark=state.benchmark,
        figure_title="Figure0.2",
    )


def _build_fig_beta(state: DashboardState) -> Any:
    from dash_app.figures import fig_beta_regime_compare

    return fig_beta_regime_compare(
        dict(state.p0.get("beta_steady") or {}),
        dict(state.p0.get("beta_stress") or {}),
        state.symbols, state.benchmark, state.tpl,
        figure_title="Figure0.3",
    )


def _build_heatmap_text_panel(state: DashboardState) -> Any:
    from dash_app.render.explain import p0_heatmap_body, p0_heatmap_card_title

    return dbc.Card(
        [
            dbc.CardHeader(p0_heatmap_card_title(state.env), className="phase-card-header-title"),
            dbc.CardBody(
                dcc.Markdown(p0_heatmap_body(state.ui_mode or "invest"), className="mb-0 phase-doc-body")
            ),
        ],
        className="shadow-sm border-secondary phase-text-panel h-100",
    )


def _build_beta_text_stack(state: DashboardState) -> Any:
    from dash_app.render.explain import (
        p0_beta_card_title,
        p0_beta_cheatsheet,
        p0_beta_nonsteady,
    )

    mode = state.ui_mode or "invest"
    nonsteady_card = dbc.Card(
        [
            dbc.CardHeader(
                '2026 年 4 月初市场进入典型"非稳态区间"：',
                className="phase-card-header-title",
            ),
            dbc.CardBody(
                dcc.Markdown(p0_beta_nonsteady(mode), className="mb-0 phase-doc-body")
            ),
        ],
        className="shadow-sm border-secondary phase-text-panel h-100",
    )
    cheatsheet_card = dbc.Card(
        [
            dbc.CardHeader("Beta 含义速查", className="phase-card-header-title"),
            dbc.CardBody(
                dcc.Markdown(p0_beta_cheatsheet(mode), className="mb-0 phase-doc-body")
            ),
        ],
        className="shadow-sm border-secondary phase-text-panel h-100",
    )
    return html.Div(
        [
            dbc.Card(
                dbc.CardHeader(
                    p0_beta_card_title(state.defense_level),
                    className="phase-card-header-title",
                ),
                className="shadow-sm border-secondary phase-text-panel mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(cheatsheet_card, xs=12, md=6, className="mb-2"),
                    dbc.Col(nonsteady_card, xs=12, md=6, className="mb-2"),
                ],
                className="g-2 align-items-stretch",
            ),
        ],
    )


def _build_asset_class_card(state: DashboardState) -> Any:
    from dash_app.render.explain import p0_beta_by_class

    return dbc.Card(
        [
            dbc.CardHeader("各资产类分析", className="phase-card-header-title"),
            dbc.CardBody(
                dcc.Markdown(p0_beta_by_class(state.ui_mode or "invest"), className="mb-0 phase-doc-body")
            ),
        ],
        className="shadow-sm border-secondary phase-text-panel",
    )


def _build_about_p0(state: DashboardState) -> Any:
    """Phase 0 逻辑说明 Alert。"""
    from dash_app.render.explain import about_phase0_logic

    orth = state.env.get("orthogonality_check") or {}
    warn = bool(orth.get("warning")) and "削弱" in str(orth.get("message", ""))
    return dbc.Alert(
        dcc.Markdown(about_phase0_logic(state.p0, state.env), className="mb-0 phase-doc-body"),
        color="warning" if warn else "secondary",
        className="py-2 mb-0 phase-text-panel",
    )


def build_main_p0_components(state: DashboardState) -> MainP0Components:
    """构造主栏 P0 组件。纯函数。"""
    assert isinstance(state, DashboardState), (
        f"state must be DashboardState, got {type(state).__name__}"
    )
    _trace("build_main_p0 start symbols=%d", len(state.symbols))

    out = MainP0Components(
        header=html.Div(),
        fig_corr=_build_fig_correlation(state),
        fig_beta=_build_fig_beta(state),
        p0_heatmap_text=_build_heatmap_text_panel(state),
        p0_beta_text_stack=_build_beta_text_stack(state),
        p0_asset_class_analysis=_build_asset_class_card(state),
        about_p0=_build_about_p0(state),
    )
    _trace("build_main_p0 done")
    return out
