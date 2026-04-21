"""主栏 P2 渲染 — 标的下拉 / 影子择模结果 / 像素矩阵 / 密度热图。

**5 个可见槽位**（原 13 个中 8 个隐藏占位已删除）：
p2-symbol options / value, p2-best-model, fig-p2-best-pixels, fig-p2-density
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from dash_app.render.contracts import DashboardState, MainP2Components

logger = logging.getLogger("dash_app.render.main_p2")
_TRACE = os.environ.get("DEBUG_RENDER", "0").strip() not in ("", "0", "false", "False")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if _TRACE:
        try:
            print(f"[main_p2] {msg % args}" if args else f"[main_p2] {msg}")
        except Exception:
            pass


def _resolve_p2_symbol_selection(
    symbols: List[str],
    p2_sym_state: Optional[str],
) -> Tuple[List[Dict[str, str]], Optional[str]]:
    """生成标的下拉的 options + 当前 value。"""
    assert isinstance(symbols, list), "symbols must be list"

    opts = [{"label": s, "value": s} for s in symbols]
    val = p2_sym_state if p2_sym_state in symbols else (symbols[0] if symbols else None)
    return opts, val


def _fetch_test_density_series(
    json_path: str,
    sym: Optional[str],
    tfd: List[Any],
) -> Optional[List[float]]:
    """从 data.json 提取测试窗内该标的实际收益序列（密度图叠加用）；失败返回 None。"""
    if not sym or not tfd:
        return None
    try:
        from dash_app.figures import _test_returns as _tr
        _td, _tv = _tr(json_path, sym, tfd[0], tfd[-1])
        if _tv and len(_tv) == len(tfd):
            return _tv
    except Exception as exc:
        _trace("density fetch failed: %s", exc)
    return None


def build_main_p2_components(state: DashboardState) -> MainP2Components:
    """构造主栏 P2 组件。纯函数。"""
    assert isinstance(state, DashboardState), (
        f"state must be DashboardState, got {type(state).__name__}"
    )
    _trace("build_main_p2 start symbols=%d consistency=%.3f",
           len(state.symbols), state.consistency)

    from dash_app.dash_ui_helpers import _p2_best_model_hero
    from dash_app.figures import fig_p2_best_model_pixels, fig_p2_density_heatmap

    opts, val = _resolve_p2_symbol_selection(state.symbols, state.p2_sym_state)

    p2_best_hero = _p2_best_model_hero(state.p2, val)

    fig_p2_pixels = fig_p2_best_model_pixels(
        state.best_per_sym, state.symbols, val, state.tpl, figure_title="Figure3.1",
    )

    test_vals = _fetch_test_density_series(state.json_path, val, state.test_forecast_dates)
    fig_p2_dens = fig_p2_density_heatmap(
        state.test_forecast_dates,
        state.model_mu_test_ts if isinstance(state.model_mu_test_ts, dict) else {},
        state.model_sigma_test_ts if isinstance(state.model_sigma_test_ts, dict) else {},
        val, state.tpl,
        test_vals=test_vals, figure_title="Figure2.2",
    )

    out = MainP2Components(
        p2_opts=opts,
        p2_val=val,
        p2_best_hero=p2_best_hero,
        fig_p2_pixels=fig_p2_pixels,
        fig_p2_dens=fig_p2_dens,
    )
    _trace("build_main_p2 done val=%s has_density=%s", val, test_vals is not None)
    return out
