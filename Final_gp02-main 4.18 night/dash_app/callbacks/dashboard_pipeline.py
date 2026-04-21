"""Pipeline store + dashboard face callbacks (extracted from app.py)."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, html
from dash.exceptions import PreventUpdate

from dash_app.constants import _DEFAULT_UNIVERSE
from dash_app.dashboard_face_render import render_dashboard_outputs
from dash_app.dash_ui_helpers import (
    _execute_pipeline_for_dashboard,
    _flatten_universe,
)
from dash_app.services.copy import get_status_message
from dash_app.ui.sidebar_left import _unpack_tau_l2_l1
from research.schemas import DefensePolicyConfig

import copy


def register_dashboard_pipeline_callbacks(app: dash.Dash) -> None:
    def _build_idle_snapshot() -> Dict[str, Any]:
        """构造一个"空载"的快照，让下游 render 走正常路径得到占位组件。"""
        return {
            "defense_level": 0,
            "phase0": {"meta": {}, "environment_report": {},
                       "beta_steady": {}, "beta_stress": {},
                       "train_index": [], "test_index": []},
            "phase1": {"h_struct": 0.0, "diagnostics": []},
            "phase2": {"jsd_baseline_mean": 0.0,
                       "credibility_score": 0.0,
                       "consistency_score": 0.0,
                       "best_model_per_symbol": {},
                       "model_mu": {}, "model_sigma": {},
                       "model_mu_test_ts": {}, "model_sigma_test_ts": {},
                       "test_forecast_dates": []},
            "phase3": {"objective_name": "max_sharpe", "weights": {},
                       "mc_times": [], "mc_paths_baseline": [], "mc_paths_stress": [],
                       "defense_validation": {}},
        }

    def _pipeline_render_idle(theme: Optional[str], ui_mode: Optional[str]) -> Tuple[Any, ...]:
        """未点「保存并运行」：占位输出（53 元组，与 render_dashboard_outputs 同壳）。"""
        syms = _flatten_universe(copy.deepcopy(_DEFAULT_UNIVERSE))
        return render_dashboard_outputs(
            DefensePolicyConfig(),
            _build_idle_snapshot(),
            symbols=syms,
            api_err=None,
            s_val=-0.1,
            theme=theme,
            p2_sym_state=None,
            ui_mode=ui_mode,
        )

    def _pipeline_render_after_exception(tb_str: str, theme: Optional[str]) -> Tuple[Any, ...]:
        """管线抛错后的 53 元组：用 idle 壳 + 覆盖第 1 槽（diagnostic-summary）为错误 Alert。"""
        base = list(_pipeline_render_idle(theme, ui_mode=None))
        err_alert = dbc.Alert(
            [
                html.Strong(get_status_message("pipeline_error_title", "Pipeline 运行出错：")),
                html.Pre(
                    tb_str,
                    className="small mb-0 mt-1",
                    style={"whiteSpace": "pre-wrap", "fontSize": "11px"},
                ),
            ],
            color="danger",
            className="py-2 mb-2",
        )
        base[0] = err_alert                       # slot 1 = diagnostic-summary
        return tuple(base)
    
    @app.callback(
        Output("defense-policy-config", "data"),
        Output("last-snap", "data"),
        Output("symbols-store", "data"),
        Output("pipeline-render-ctx", "data"),
        Input("btn-run", "n_clicks"),
        State("sl-tau-l2-l1", "value"),
        State("sl-tau-h1", "value"),
        State("sl-tau-vol", "value"),
        State("sl-tau-ac1", "value"),
        State("sl-k-jsd", "value"),
        State("sl-jsd-baseline-eps-log", "value"),
        State("sl-cred-jsd-base", "value"),
        State("sl-cred-jsd-pen", "value"),
        State("sl-cred-pen-cap", "value"),
        State("sl-cred-min", "value"),
        State("sl-cred-max", "value"),
        State("sl-lambda", "value"),
        State("sl-scenario-step", "value"),
        State("sl-scenario-impact", "value"),
        State("sl-oos-steps", "value"),
        State("sl-shadow-alpha-mse", "value"),
        State("sl-shadow-holdout-days", "value"),
        State("asset-universe-store", "data"),
        State("p0-strike-store", "data"),
        State("sentiment-detail-store", "data"),
        State("sl-semantic-cos-window", "value"),
        State("sl-verify-train-tail-days", "value"),
        State("sl-verify-crash-q", "value"),
        State("sl-verify-std-q", "value"),
        State("sl-verify-tail-q", "value"),
        prevent_initial_call=True,
    )
    def _run_pipeline_stores(
        n,
        tau_l2_l1,
        tau_h1,
        tau_vol,
        tau_ac1,
        k_jsd,
        jsd_baseline_eps_log,
        cred_jsd_base,
        cred_jsd_pen,
        cred_pen_cap,
        cred_min,
        cred_max,
        lam,
        scenario_step,
        scenario_impact,
        oos_steps,
        shadow_alpha_mse,
        shadow_holdout_days,
        asset_universe,
        strike_store,
        sentiment_detail_store,
        semantic_cos_window,
        verify_train_tail_days,
        verify_crash_q,
        verify_std_q,
        verify_tail_q,
    ):
        if n is None:
            raise PreventUpdate
        # 勿在 n_clicks==0 时清空 Store：顶栏 clientside 会改写按钮 innerHTML，
        # 极端情况下可能触发「伪 0」事件；清空 last-snap 会让整页看起来像从未运行。
        if not n:
            raise PreventUpdate
        tau_l2, tau_l1 = _unpack_tau_l2_l1(tau_l2_l1)
        try:
            pol, snap_json, symbols, api_err, s_val = _execute_pipeline_for_dashboard(
                tau_l2,
                tau_l1,
                tau_h1,
                tau_vol,
                tau_ac1,
                k_jsd,
                jsd_baseline_eps_log,
                cred_jsd_base,
                cred_jsd_pen,
                cred_pen_cap,
                cred_min,
                cred_max,
                lam,
                None,
                scenario_step,
                scenario_impact,
                oos_steps=oos_steps,
                shadow_alpha_mse=shadow_alpha_mse,
                shadow_holdout_days=shadow_holdout_days,
                # NOTE: `data_max_age` / `auto_refresh` 的 UI 控件已随 R1.10 移除；
                # 调用 `run_pipeline` 时不再显式传这两个 kwargs，底层默认不触发
                # 数据自动刷新。`research.data_refresher` 仅在 data.json 缺失时
                # 由 `pipeline_exec/executor.py::_ensure_data_json_exists` 惰性调用。
                asset_universe=asset_universe,
                strike_store=strike_store,
                sentiment_detail=sentiment_detail_store,
                semantic_cos_window=semantic_cos_window,
                verify_train_tail_days=verify_train_tail_days,
                verify_crash_q=verify_crash_q,
                verify_std_q=verify_std_q,
                verify_tail_q=verify_tail_q,
            )
            return (
                pol.model_dump(),
                snap_json,
                symbols,
                {"kind": "ok", "api_err": api_err, "s_val": s_val},
            )
        except Exception:
            import traceback as _tb
    
            tb_str = _tb.format_exc()
            return (
                DefensePolicyConfig().model_dump(),
                None,
                [],
                {"kind": "error", "trace": tb_str},
            )
    
    @app.callback(
        # main_p0（9 槽）
        Output("diagnostic-summary", "children"),             # 1
        Output("header-status", "children"),                  # 2
        Output("fig-p0-corr", "figure"),                      # 3
        Output("fig-p0-beta", "figure"),                      # 4
        Output("p0-heatmap-text", "children"),                # 5
        Output("p0-beta-text-stack", "children"),             # 6
        Output("p0-asset-class-analysis", "children"),        # 7
        Output("p0-noise-level", "children"),                 # 8
        Output("about-phase0-logic", "children"),             # 9
        # main_p1（3 槽）
        Output("p1-asset-cards", "children"),                 # 10
        Output("card-p1", "children"),                        # 11
        Output("p1-group-analysis", "children"),              # 12
        # main_p2（5 槽；原 13 个中 8 个隐藏占位已删除）
        Output("p2-symbol", "options"),                       # 13
        Output("p2-symbol", "value"),                         # 14
        Output("p2-best-model", "children"),                  # 15
        Output("fig-p2-best-pixels", "figure"),               # 16
        Output("fig-p2-density", "figure"),                   # 17
        # main_p3（5 槽；原 4 槽 + 新增 fig-p3-best-table = Figure3.1）
        Output("objective-banner", "children"),               # 18
        Output("fig-p3-mc", "figure"),                        # 19
        Output("fig-p3-weights", "figure"),                   # 20
        Output("card-p3", "children"),                        # 21
        Output("fig-p3-best-table", "figure"),                # 22 Figure3.1
        # main_p4（8 槽：Fig4.1a × 3 + Fig4.1b × 3 + 结论 × 1 + 实验栈 × 1）
        Output("p4-experiments-stack", "children"),           # 23
        Output("p4-fig41-jsd", "figure"),                     # 24 Fig4.1a chart
        Output("p4-verify-hero", "children"),                 # 25 Fig4.1a hero
        Output("p4-fig41-analysis-md", "children"),           # 26 Fig4.1a banner+panel
        Output("p4-fig41b-jsd", "figure"),                    # 27 Fig4.1b chart
        Output("p4-fig41b-verify-hero", "children"),          # 28 Fig4.1b hero
        Output("p4-fig41b-analysis-md", "children"),          # 29 Fig4.1b banner+panel
        Output("p4-fig41-conclusion", "children"),            # 30 独立结论卡
        # sidebar_right（21 槽）
        Output("sb2-p2-traffic-lights", "children"),          # 31
        Output("sb2-defense-level-badge", "children"),        # 32
        Output("sb2-fig-st", "figure"),                       # 33
        Output("sb2-fig-h-struct", "children"),               # 34
        Output("sb2-fig-consistency", "children"),            # 35
        Output("sb2-fig-jsd-stress", "figure"),               # 36
        Output("sb2-fig-cosine", "figure"),                   # 37
        Output("sb2-fig-jsd-stress-reason", "children"),      # 38
        Output("sb2-fig-cosine-reason", "children"),          # 39
        Output("sb2-fig-st-reason", "children"),              # 40
        Output("sb2-fig-h-struct-reason", "children"),        # 41
        Output("sb2-fig-consistency-reason", "children"),     # 42
        Output("figure-caption-bundle", "data"),              # 43
        Output("sb2-explain-slot-01", "children"),            # 44 FigX.1
        Output("sb2-explain-slot-02", "children"),            # 45 FigX.2
        Output("sb2-fig-vol-ac1-cards", "children"),          # 46 FigX.3 cards
        Output("sb2-fig-vol-ac1-reason", "children"),         # 47 FigX.3 reason
        Output("sb2-explain-slot-03", "children"),            # 48 FigX.3 explain
        Output("sb2-explain-slot-04", "children"),            # 49 FigX.4
        Output("sb2-explain-slot-05", "children"),            # 50 FigX.5
        Output("sb2-explain-slot-06", "children"),            # 51 FigX.6
        # topbar（2 槽）
        Output("topbar-defense-intro-slot", "children"),      # 52
        Output("topbar-defense-reasons-collapse", "children"),# 53
        # inputs / state
        Input("last-snap", "data"),
        Input("defense-policy-config", "data"),
        Input("symbols-store", "data"),
        Input("pipeline-render-ctx", "data"),
        Input("sl-tau-l2-l1", "value"),
        Input("sl-tau-h1", "value"),
        State("theme-store", "data"),
        State("p2-symbol", "value"),
        State("p4-verify-search", "value"),
        State("radio-ui-mode", "data"),
        prevent_initial_call=False,
    )
    def _render_dashboard_face(
        last_snap,
        policy_data,
        symbols_store,
        render_ctx,
        tau_l2_l1_live,
        tau_h1_live,
        theme,
        p2_sym_state,
        p4_search,
        ui_mode,
    ):
        ctx = render_ctx if isinstance(render_ctx, dict) else {}
        kind = str(ctx.get("kind") or "idle")
        if kind == "idle":
            return _pipeline_render_idle(theme, ui_mode)
        if kind == "error":
            tb = str(ctx.get("trace") or "未知错误")
            return _pipeline_render_after_exception(tb, theme)
        if kind == "ok" and isinstance(last_snap, dict):
            pol = DefensePolicyConfig.model_validate(policy_data or {})
            # Live tau overrides (keep everything else from stored policy)
            try:
                a, b = _unpack_tau_l2_l1(tau_l2_l1_live)
                pol = pol.model_copy(update={"tau_l2": float(a), "tau_l1": float(b)})
            except Exception:
                pass
            try:
                if tau_h1_live is not None:
                    pol = pol.model_copy(update={"tau_h1": float(tau_h1_live)})
            except Exception:
                pass
            sym = symbols_store if isinstance(symbols_store, list) else []
            api_err_v = ctx.get("api_err")
            api_err: Optional[str] = api_err_v if isinstance(api_err_v, str) else None
            try:
                s_val = float(ctx.get("s_val", -0.1))
                if not math.isfinite(s_val):
                    s_val = -0.1
            except (TypeError, ValueError):
                s_val = -0.1
            # Optional: quick symbol override by P4 search box
            p2_sel = p2_sym_state
            if isinstance(p4_search, str) and p4_search.strip():
                q = p4_search.strip().upper()
                for s in sym:
                    if q in str(s).upper():
                        p2_sel = s
                        break
            return render_dashboard_outputs(pol, last_snap, sym, api_err, s_val, theme, p2_sel, ui_mode)
        return _pipeline_render_idle(theme, ui_mode)
    
