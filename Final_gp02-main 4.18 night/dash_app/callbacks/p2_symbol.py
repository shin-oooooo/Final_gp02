"""P2 symbol panel callbacks."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate

from dash_app.figures import fig_p2_best_model_pixels, fig_p2_density_heatmap

# Import shared helpers from the main app module.
from dash_app.ui.layout import _default_data_json_path, _templates
from dash_app.dash_ui_helpers import (
    _p2_best_model_hero,
    _p2_traffic_row,
)


def register_p2_symbol_callbacks(app):
    @app.callback(
        Output("p2-best-model", "children", allow_duplicate=True),
        Output("fig-p2-best-pixels", "figure", allow_duplicate=True),
        Output("fig-p2-density", "figure", allow_duplicate=True),
        Output("sb2-p2-traffic-lights", "children", allow_duplicate=True),
        Input("p2-symbol", "value"),
        State("last-snap", "data"),
        # theme-store 在 R1.10 后常驻 "dark"；从 Input 降为 State，callback 不
        # 再因主题值触发（值永远不变，订阅无意义）。
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def _upd_p2_fig(sym, snap, theme):
        """标的下拉变化时局部刷新 P2 可见组件。

        删除的冗余输出（均为前端隐藏占位）：
        * ``p2-best-model-meta`` — 被 ``display:none`` 包裹
        * ``p2-jsd-failure-merge`` — 被 ``display:none`` 包裹
        * ``fig-p2-mirror-best-pixels`` — 镜像槽；现已合并入 ``fig-p2-best-pixels``
        """
        if not snap or not sym:
            raise PreventUpdate
        tpl = _templates(theme or "dark")
        p2 = snap.get("phase2") or {}
        mu_ts = p2.get("model_mu_test_ts") or {}
        sig_ts = p2.get("model_sigma_test_ts") or {}
        tfd = p2.get("test_forecast_dates") or []
        json_path = _default_data_json_path()
        meta0 = (snap.get("phase0") or {}).get("meta") or {}
        syms: List[str] = list(meta0.get("symbols_resolved") or [])
        if not syms:
            syms = list((snap.get("phase3") or {}).get("weights", {}).keys())
        best_per_sym: Dict[str, str] = dict(p2.get("best_model_per_symbol") or {})
        _test_vals_dens: Optional[List[float]] = None
        if sym and tfd:
            try:
                from dash_app.figures import _test_returns as _tr

                _td, _tv = _tr(json_path, sym, tfd[0], tfd[-1])
                if _tv and len(_tv) == len(tfd):
                    _test_vals_dens = _tv
            except Exception:
                pass
        return (
            _p2_best_model_hero(p2, sym),
            fig_p2_best_model_pixels(
                best_per_sym, syms, sym, tpl, figure_title="Figure3.1"
            ),
            fig_p2_density_heatmap(
                tfd,
                mu_ts if isinstance(mu_ts, dict) else {},
                sig_ts if isinstance(sig_ts, dict) else {},
                sym,
                tpl,
                test_vals=_test_vals_dens,
                figure_title="Figure2.2",
            ),
            _p2_traffic_row(p2, large=True, badges_only=True),
        )

    @app.callback(
        Output("p2-symbol-hero", "children"),
        Input("p2-symbol", "value"),
        prevent_initial_call=False,
    )
    def _p2_symbol_hero(sym: Optional[str]):
        s = (sym or "—").strip()
        return html.Span(s or "—", className="display-6 fw-bold text-info")

    # ------------------------------------------------------------------ #
    # p4-verify-search 选项与初始值同步（搬自 P2 下拉，保持全站标的一致）
    # ------------------------------------------------------------------ #
    @app.callback(
        Output("p4-verify-search", "options"),
        Output("p4-verify-search", "value"),
        Input("symbols-store", "data"),
        Input("p2-symbol", "value"),
        prevent_initial_call=False,
    )
    def _sync_p4_search(symbols: Any, p2_val: Optional[str]):
        """p4-verify-search 的 options 复用 p2-symbol 的标的列表；value 默认跟随 p2。

        用户在 4.1a 顶部搜索后，callback 链路：
        ``p4-verify-search.value → dashboard_pipeline._run_pipeline_stores(p4_search=…)
        → p2_sel 覆盖 → render_dashboard_outputs(p2_sym_state=p2_sel)`` 最终进入
        ``render/main_p4._build_fig41_for_signal(focus_override=…)``。
        """
        if not isinstance(symbols, list):
            symbols = []
        opts: List[Dict[str, str]] = [{"label": str(s), "value": str(s)} for s in symbols]
        val = p2_val if (isinstance(p2_val, str) and p2_val in [o["value"] for o in opts]) else (
            opts[0]["value"] if opts else None
        )
        return opts, val
