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
        """构造一个"空载"的快照，让下游 render 走正常路径得到占位组件。

        关键：``_is_idle`` 标记让 ``render/sidebar_right.py::_build_reason_strip``
        识别"未运行管线"态，并为 FigX.1~6 返回 success 级别的占位 defense-tag。
        否则 ``h_struct=0.0`` 会撞 ``figx2_condition_line`` 的 if 分支（warn）、
        ``credibility_score=0.0`` 会撞 ``figx4_condition_line`` 的 if 分支（danger）;
        再加上 level 0 的过滤策略（只展 success），就会出现"运行前 FigX.2 /
        FigX.4 defense-tag 看不到"的现象。
        """
        return {
            "_is_idle": True,
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
        """未点「保存并运行」：占位输出（54 元组，与 render_dashboard_outputs 同壳）。"""
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
        """管线抛错后的 54 元组：用 idle 壳 + 覆盖第 1 槽（header-status）为错误 Alert。"""
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
        base[0] = err_alert                       # slot 1 = header-status
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
        # main_p0（7 槽；历史 9 槽中的 diagnostic-summary / p0-noise-level 已删除）
        Output("header-status", "children"),                  # 1
        Output("fig-p0-corr", "figure"),                      # 2
        Output("fig-p0-beta", "figure"),                      # 3
        Output("p0-heatmap-text", "children"),                # 4
        Output("p0-beta-text-stack", "children"),             # 5
        Output("p0-asset-class-analysis", "children"),        # 6
        Output("about-phase0-logic", "children"),             # 7
        # main_p1（3 槽）
        Output("p1-asset-cards", "children"),                 # 8
        Output("card-p1", "children"),                        # 9
        Output("p1-group-analysis", "children"),              # 10
        # main_p2（5 槽；原 13 个中 8 个隐藏占位已删除）
        Output("p2-symbol", "options"),                       # 11
        Output("p2-symbol", "value"),                         # 12
        Output("p2-best-model", "children"),                  # 13
        Output("fig-p2-best-pixels", "figure"),               # 14
        Output("fig-p2-density", "figure"),                   # 15
        # main_p3（5 槽；原 4 槽 + 新增 fig-p3-best-table = Figure3.1）
        Output("objective-banner", "children"),               # 16
        Output("fig-p3-mc", "figure"),                        # 17
        Output("fig-p3-weights", "figure"),                   # 18
        Output("card-p3", "children"),                        # 19
        Output("fig-p3-best-table", "figure"),                # 20 Figure3.1
        # main_p4（11 槽：Fig4.1a × 4 + Fig4.1b × 4 + Fig4.1 结论 + 实验栈 + Fig4.2 结论）
        Output("p4-experiments-stack", "children"),           # 21
        Output("p4-fig41-alarm-banner", "children"),          # 22 Fig4.1a alarm day banner
        Output("p4-fig41-jsd", "figure"),                     # 23 Fig4.1a chart
        Output("p4-verify-hero", "children"),                 # 24 Fig4.1a hero
        Output("p4-fig41-analysis-md", "children"),           # 25 Fig4.1a Part 2-5 / fallback
        Output("p4-fig41b-alarm-banner", "children"),         # 26 Fig4.1b alarm day banner
        Output("p4-fig41b-jsd", "figure"),                    # 27 Fig4.1b chart
        Output("p4-fig41b-verify-hero", "children"),          # 28 Fig4.1b hero
        Output("p4-fig41b-analysis-md", "children"),          # 29 Fig4.1b Part 2-5 / fallback
        Output("p4-fig41-conclusion", "children"),            # 30 Fig4.1 独立结论卡
        Output("p4-fig42-conclusion", "children"),            # 31 Fig4.2 独立结论卡
        # sidebar_right（21 槽）
        Output("sb2-p2-traffic-lights", "children"),          # 32
        Output("sb2-defense-level-badge", "children"),        # 33
        Output("sb2-fig-st", "figure"),                       # 34
        Output("sb2-fig-h-struct", "children"),               # 35
        Output("sb2-fig-consistency", "children"),            # 36
        Output("sb2-fig-jsd-stress", "figure"),               # 37
        Output("sb2-fig-cosine", "figure"),                   # 38
        Output("sb2-fig-jsd-stress-reason", "children"),      # 39
        Output("sb2-fig-cosine-reason", "children"),          # 40
        Output("sb2-fig-st-reason", "children"),              # 41
        Output("sb2-fig-h-struct-reason", "children"),        # 42
        Output("sb2-fig-consistency-reason", "children"),     # 43
        Output("figure-caption-bundle", "data"),              # 44
        Output("sb2-explain-slot-01", "children"),            # 45 FigX.1
        Output("sb2-explain-slot-02", "children"),            # 46 FigX.2
        Output("sb2-fig-vol-ac1-cards", "children"),          # 47 FigX.3 cards
        Output("sb2-fig-vol-ac1-reason", "children"),         # 48 FigX.3 reason
        Output("sb2-explain-slot-03", "children"),            # 49 FigX.3 explain
        Output("sb2-explain-slot-04", "children"),            # 50 FigX.4
        Output("sb2-explain-slot-05", "children"),            # 51 FigX.5
        Output("sb2-explain-slot-06", "children"),            # 52 FigX.6
        # topbar（2 槽）
        Output("topbar-defense-intro-slot", "children"),      # 53
        Output("topbar-defense-reasons-collapse", "children"),# 54
        # inputs / state
        Input("last-snap", "data"),
        Input("defense-policy-config", "data"),
        Input("symbols-store", "data"),
        Input("pipeline-render-ctx", "data"),
        Input("sl-tau-l2-l1", "value"),
        Input("sl-tau-h1", "value"),
        # 语言切换由 ``app_shell._lang_rebuild_children`` 重建 ``lang-aware-children``
        # 后原子写入；本回调监听 tick 重新渲染整张面板，确保新挂载的组件用新语言
        # 文案重新填充图表与文字（见 ui/layout.py 顶部说明）。
        Input("lang-rebuild-tick", "data"),
        # 研究 / 投资按钮：提升为 Input，使未点「保存并运行」时切换也能**实时**触发
        # 整面板重绘（P0/P1/P2/P3/P4 + sidebar_right 的所有 mode-aware 组件），
        # 不必等 ``_caption_refresh_on_mode`` 那 20 叠部分覆盖。
        Input("radio-ui-mode", "data"),
        # Fig4.1a / 4.1b 两个独立的标的搜索框：提升为 Input，使抽换标的时右侧
        # hero / 预警日 banner / Chart 1 能立刻刷新。
        Input("p4-verify-search", "value"),
        Input("p4-verify-search-b", "value"),
        State("theme-store", "data"),
        State("p2-symbol", "value"),
        prevent_initial_call=False,
    )
    def _render_dashboard_face(
        last_snap,
        policy_data,
        symbols_store,
        render_ctx,
        tau_l2_l1_live,
        tau_h1_live,
        _lang_tick,
        ui_mode,
        p4_search_a,
        p4_search_b,
        theme,
        p2_sym_state,
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

            # 两个搜索框完全独立：只要命中当前 symbols 列表就生效，否则回退到 p2_sym_state。
            def _resolve_focus(q: Any) -> Optional[str]:
                if not isinstance(q, str) or not q.strip():
                    return None
                qu = q.strip().upper()
                for s in sym:
                    if qu in str(s).upper():
                        return s
                return None

            focus_a = _resolve_focus(p4_search_a) or (p2_sym_state if isinstance(p2_sym_state, str) else None)
            focus_b = _resolve_focus(p4_search_b) or (p2_sym_state if isinstance(p2_sym_state, str) else None)

            return render_dashboard_outputs(
                pol, last_snap, sym, api_err, s_val, theme, p2_sym_state, ui_mode,
                p4_focus_a=focus_a, p4_focus_b=focus_b,
            )
        return _pipeline_render_idle(theme, ui_mode)
    
