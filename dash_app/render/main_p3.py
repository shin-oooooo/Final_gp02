"""主栏 P3 渲染 — 目标 banner / Fig3.1 最佳模型 μ/σ 表 / MC / 权重。

**5 个可见槽位**（原 4 槽 + ``fig-p3-best-table``）：
objective-banner, fig-p3-mc, fig-p3-weights, card-p3, fig-p3-best-table
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dash import html

from dash_app.render.contracts import DashboardState, MainP3Components

logger = logging.getLogger("dash_app.render.main_p3")
_TRACE = os.environ.get("DEBUG_RENDER", "0").strip() not in ("", "0", "false", "False")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if _TRACE:
        try:
            print(f"[main_p3] {msg % args}" if args else f"[main_p3] {msg}")
        except Exception:
            pass


def _build_objective_banner(state: DashboardState) -> Any:
    from dash_app.dash_ui_helpers import _objective_alert

    return _objective_alert(state.defense_level, state.objective_name, state.api_err)


def _build_fig_mc(state: DashboardState) -> Any:
    """Figure3.3 · 双轨 Monte Carlo。"""
    from dash_app.figures import fig_mc_dual_track

    mc_t = state.p3.get("mc_times") or []
    mc_b = state.p3.get("mc_paths_baseline") or []
    mc_s = state.p3.get("mc_paths_stress") or []
    worst_i = int(state.p3.get("mc_worst_stress_path_index", 0))
    mdd_pct = state.p3.get("mc_expected_max_drawdown_pct")
    mdd_f = float(mdd_pct) if mdd_pct is not None else None

    return fig_mc_dual_track(
        mc_t, mc_b, mc_s, worst_i, state.tpl,
        mdd_stress_pct=mdd_f,
        path_median_nojump=state.p3.get("mc_path_median_nojump"),
        path_jump_p5=state.p3.get("mc_path_jump_p5"),
        figure_title="Figure3.3",
    )


def _build_fig_weights(state: DashboardState) -> Any:
    """Figure3.2 · 自适应优化权重对比。"""
    from dash_app.figures import fig_weights_compare

    return fig_weights_compare(state.weights, state.symbols, state.tpl, figure_title="Figure3.2")


def _build_fig_best_table(state: DashboardState) -> Any:
    """Figure3.1 · 各标的最佳模型 μ̂ / σ̂（无竖框三行表）。

    数据源：``state.best_per_sym`` + ``state.model_mu`` + ``state.model_sigma``
    （OOS 时序存在则取末日，退回全样本标量字典；取值规则与
    ``ui/main_p2.py::_p2_mu_sigma_table`` 一致）。
    """
    from dash_app.render.fig_p3_best_table import fig_p3_best_mu_sigma_table

    return fig_p3_best_mu_sigma_table(
        state.best_per_sym,
        state.model_mu,
        state.model_sigma,
        state.symbols,
        state.tpl,
        model_mu_test_ts=state.model_mu_test_ts,
        model_sigma_test_ts=state.model_sigma_test_ts,
        figure_title="Figure3.1",
    )


def build_main_p3_components(state: DashboardState) -> MainP3Components:
    """构造主栏 P3 组件。纯函数。"""
    assert isinstance(state, DashboardState), (
        f"state must be DashboardState, got {type(state).__name__}"
    )
    _trace("build_main_p3 start objective=%s", state.objective_name)

    out = MainP3Components(
        obj_banner=_build_objective_banner(state),
        fig_mc=_build_fig_mc(state),
        fig_w=_build_fig_weights(state),
        card_p3=html.Div(),
        fig_best_table=_build_fig_best_table(state),
    )
    _trace("build_main_p3 done")
    return out
