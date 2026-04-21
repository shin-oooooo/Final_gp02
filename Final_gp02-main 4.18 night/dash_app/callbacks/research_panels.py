"""Research-panel callbacks."""
from typing import Any, List, Optional

import dash
from dash import MATCH, Input, Output, State, dcc, html

from dash_app.services.copy import get_md_text
from dash_app.ui.layout import (
    _analysis_card,
    _default_data_json_path,
    _p0_resolved_window_strings,
    _templates,
    explain_title_from_figures as _explain_title,
)
from dash_app.render.explain import (
    build_fig42_body,
    build_figx1_explain_body,
    build_figx2_explain_body,
    build_figx3_explain_body,
    build_figx4_explain_body,
    build_figx5_explain_body,
    build_figx6_explain_body,
    build_figure_caption_bundle,
    me_phase0_intro_md,
    p1_stat_method,
    p2_fig21_intro,
    p2_pixel_shadow_intro,
    p3_section_31_adaptive,
    p3_section_32_dual_mc,
)
from dash_app.render.explain._loaders import load_fig4_template
from research.schemas import DefensePolicyConfig

import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def register_research_panels_callbacks(app):
    @app.callback(
        Output("p0-intro-me-md", "children"),
        Input("last-snap", "data"),
        prevent_initial_call=False,
    )
    def _p0_intro_time_windows(snap: Any):
        return me_phase0_intro_md(*_p0_resolved_window_strings(snap if isinstance(snap, dict) else None))

    @app.callback(
        Output({"type": "analysis-collapse", "index": MATCH}, "is_open"),
        Input({"type": "analysis-toggle", "index": MATCH}, "n_clicks"),
        State({"type": "analysis-collapse", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )
    def _toggle_analysis(n, is_open):
        if n:
            return not is_open
        return is_open

    @app.callback(
        # --- 侧栏 FigX 讲解 + caption bundle ---
        Output("figure-caption-bundle", "data", allow_duplicate=True),
        Output("sb2-explain-slot-01", "children", allow_duplicate=True),  # FigX.1
        Output("sb2-explain-slot-02", "children", allow_duplicate=True),  # FigX.2
        Output("sb2-explain-slot-03", "children", allow_duplicate=True),  # FigX.3
        Output("sb2-explain-slot-04", "children", allow_duplicate=True),  # FigX.4
        Output("sb2-explain-slot-05", "children", allow_duplicate=True),  # FigX.5
        Output("sb2-explain-slot-06", "children", allow_duplicate=True),  # FigX.6
        # --- 主栏 P4 动态内容（需快照）---
        Output("p4-fig41-analysis-md", "children", allow_duplicate=True),
        Output("p4-experiments-stack", "children", allow_duplicate=True),
        # --- 主栏 P0 四张动态文本卡（需快照）---
        Output("p0-heatmap-text", "children", allow_duplicate=True),
        Output("p0-beta-text-stack", "children", allow_duplicate=True),
        Output("p0-asset-class-analysis", "children", allow_duplicate=True),
        Output("about-phase0-logic", "children", allow_duplicate=True),
        # --- 主栏 P1/P2/P3 + P4 静态讲解卡的内层 md slot（只更新文字，不重建整张卡）---
        # 不再覆写 *-explain-card 的 children（会导致 analysis-toggle/collapse id 重复，
        # 使 _toggle_analysis MATCH 回调失效），只更新卡内的 *-explain-md Div。
        Output("p1-stat-method-md", "children", allow_duplicate=True),
        Output("p2-fig21-explain-md", "children", allow_duplicate=True),
        Output("p2-fig22-explain-md", "children", allow_duplicate=True),
        Output("p3-fig31-explain-md", "children", allow_duplicate=True),
        Output("p3-fig33-explain-md", "children", allow_duplicate=True),
        Output("p3-fig33-explain-md-2", "children", allow_duplicate=True),
        Output("p4-fig41-explain-md", "children", allow_duplicate=True),
        Output("p4-fig42-explain-md", "children", allow_duplicate=True),
        Input("radio-ui-mode", "data"),
        Input("lang-rebuild-tick", "data"),
        # last-snap 改为 State：管线完成不再触发本回调，避免每次跑批都覆写讲解卡
        # （从而也避免 analysis-toggle/collapse id 重复导致折叠失效）。
        State("last-snap", "data"),
        State("defense-policy-config", "data"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def _caption_refresh_on_mode(
        mode: Optional[str],
        _lang_tick: Any,
        snap: Any,
        pol_j: Any,
        theme: Optional[str],
    ):
        """模式 / 语言切换时**只刷新讲解类内容**，不重跑管线。

        覆盖范围：
        * 侧栏 FigX.1–6 讲解卡 + caption bundle（7 槽，需快照）
        * 主栏 P4：Fig4.1 analysis 主面板 + Fig4.2 实验栈（2 槽，需快照）
        * 主栏 P0：4 张动态文本卡（3 body + 1 about，共 4 槽，需快照）
        * 主栏 P1/P2/P3 + P4 的 7 张**静态讲解卡**：p1-stat-method、p2-fig21、p2-fig22、
          p3-fig31、p3-fig33、p4-fig41、p4-fig42（全部无快照也可切；有快照时
          p4-fig42 的占位符会被 ``build_fig42_body`` 替换为实际数值）。

        触发源：
        * ``radio-ui-mode``：Invest / Research 切换（不需要等管线跑完）。
        * ``lang-rebuild-tick``：语言按钮切换后由 ``app_shell`` 中的语言重建回调原子写入；
          监听 tick 而不是 ``lang-store`` 本身，可以**确保**讲解内容在 layout
          children 重建完成之后才覆盖到新挂载的组件上，避免竞争。
        """
        # 惰性 import 以避免启动时循环依赖
        from dash_app.dash_ui_helpers import _p4_experiments_stack_block
        from dash_app.fig41 import Fig41Context, build_fig41, extract_fig41_bundle
        from dash_app.render import build_main_p0, extract_dashboard_state

        NU = dash.no_update
        mode_eff = mode or "invest"

        # ── 静态讲解卡 md slot：只更新内层文字，不重建整张卡 ──
        # 各 Output 对应的是 ``*-explain-md`` Div 的 children（即 dcc.Markdown.children 字符串），
        # 而非整张 _analysis_card。这样 analysis-toggle / analysis-collapse 的 id
        # 从不被覆写，_toggle_analysis MATCH 回调始终有效。
        p1_md   = dcc.Markdown(p1_stat_method(mode_eff),           mathjax=True, className="mb-0 phase-doc-body", style={"lineHeight": "1.8"})
        p2_21_md = dcc.Markdown(p2_pixel_shadow_intro(mode_eff),   mathjax=True, className="mb-0 phase-doc-body", style={"lineHeight": "1.8"})
        p2_22_md = dcc.Markdown(p2_fig21_intro(mode_eff),          mathjax=True, className="mb-0 phase-doc-body", style={"lineHeight": "1.8"})
        p3_31_md = dcc.Markdown(p3_section_31_adaptive(mode_eff),  mathjax=True, className="mb-0 phase-doc-body", style={"lineHeight": "1.8"})
        p3_33_md = dcc.Markdown(p3_section_32_dual_mc(mode_eff),   mathjax=True, className="mb-0 phase-doc-body", style={"lineHeight": "1.8"})
        # Fig3.3 第二张「双轨蒙特卡洛模拟」只在投资模式出现；研究模式返回空字符串。
        p3_33_md2 = dcc.Markdown(
            "" if mode_eff == "research" else get_md_text("Inv/Fig3.3-Inv_2.md", ""),
            mathjax=True, className="mb-0 phase-doc-body", style={"lineHeight": "1.8"},
        )
        p4_41_md = dcc.Markdown(load_fig4_template("1", mode_eff), mathjax=True, className="mb-0 phase-doc-body", style={"lineHeight": "1.8"})

        has_snap = isinstance(snap, dict) and bool(snap.get("phase2"))

        if not has_snap:
            # 无快照时：p4_fig42 也用原始模板（占位符保持 ``{mc_content}`` 等字面）；
            # 有快照时下方会再用 ``build_fig42_body`` 覆盖。
            p4_42_md = dcc.Markdown(load_fig4_template("2", mode_eff), mathjax=True, className="mb-0 phase-doc-body", style={"lineHeight": "1.8"})
            return (
                NU,                          # caption bundle
                NU, NU, NU, NU, NU, NU,      # FigX.1-6
                NU, NU,                      # P4 fig41-analysis-md + experiments-stack
                NU, NU, NU, NU,              # P0 four
                p1_md, p2_21_md, p2_22_md, p3_31_md, p3_33_md, p3_33_md2,
                p4_41_md, p4_42_md,
            )

        try:
            pol = DefensePolicyConfig.model_validate(pol_j or {})
        except Exception:
            pol = DefensePolicyConfig()

        p2 = snap.get("phase2") or {}
        meta = (snap.get("phase0") or {}).get("meta") or {}
        syms: List[str] = list(meta.get("symbols_resolved") or [])
        if not syms:
            syms = list((snap.get("phase3") or {}).get("weights", {}).keys())
        jp = _default_data_json_path()
        tpl = _templates(theme or "dark")

        # ── 侧栏 FigX.1-6 讲解（标题由 figures_titles.md 控制）──
        figx1 = _analysis_card(
            _explain_title("fig_x_1_explain", mode, "FigX.1 讲解"),
            build_figx1_explain_body(mode, snap, pol, p2, meta, syms, jp),
        )
        figx2 = _analysis_card(
            _explain_title("fig_x_2_explain", mode, "FigX.2 讲解"),
            build_figx2_explain_body(mode, snap, pol, p2, meta, syms, jp),
        )
        figx3 = _analysis_card(
            _explain_title("fig_x_3_explain", mode, "FigX.3 讲解"),
            build_figx3_explain_body(mode, snap, pol, p2, meta, syms, jp),
        )
        figx4 = _analysis_card(
            _explain_title("fig_x_4_explain", mode, "FigX.4 讲解"),
            build_figx4_explain_body(mode, snap, pol, p2, meta, syms, jp),
        )
        figx5 = _analysis_card(
            _explain_title("fig_x_5_explain", mode, "FigX.5 讲解"),
            build_figx5_explain_body(mode, snap, pol, p2, meta, syms, jp),
        )
        figx6 = _analysis_card(
            _explain_title("fig_x_6_explain", mode, "FigX.6 讲解"),
            build_figx6_explain_body(mode, snap, pol, p2, meta, syms, jp),
        )

        # ── P0 四张动态文本卡（通过 DashboardState 重建，与 pipeline 同一逻辑）──
        state = extract_dashboard_state(
            snap, pol,
            symbols=syms,
            api_err=None,
            s_val=float(meta.get("defense_sentiment_min_st") or -0.1),
            theme=theme,
            p2_sym_state=None,
            ui_mode=mode,
        )
        p0_comp = build_main_p0(state)
        p0_heatmap = p0_comp.p0_heatmap_text
        p0_beta_stack = p0_comp.p0_beta_text_stack
        p0_asset_class = p0_comp.p0_asset_class_analysis
        p0_about = p0_comp.about_p0

        # ── P4：Fig4.1 analysis panel（fig41 模块主路径；fallback 讲解文本走 build_fig41_explain_body）──
        fig41_bundle = extract_fig41_bundle(snap, pol)
        fig41_ctx = Fig41Context(
            tpl=tpl, ui_mode=mode, snap_json=snap, policy=pol,
            p2=p2, meta=meta, symbols=syms,
        )
        fig41_components = build_fig41(fig41_bundle, fig41_ctx)
        p4_fig41_panel = fig41_components.panel

        # ── P4：Fig4.2 实验栈（只剩三权重对比图）──
        p4_experiments = _p4_experiments_stack_block(snap, tpl, mode)

        # ── P4：Fig4.2 讲解 md slot（有快照 → 占位符替换）──
        p3 = snap.get("phase3") or {}
        dv = p3.get("defense_validation") if isinstance(p3.get("defense_validation"), dict) else {}
        p4_42_md = dcc.Markdown(
            build_fig42_body(mode, snap, dv),
            mathjax=True, className="mb-0 phase-doc-body", style={"lineHeight": "1.8"},
        )

        # ── caption bundle ──
        caption = build_figure_caption_bundle(mode, snap, pol, p2, meta)

        return (
            caption,
            figx1, figx2, figx3, figx4, figx5, figx6,
            p4_fig41_panel, p4_experiments,
            p0_heatmap, p0_beta_stack, p0_asset_class, p0_about,
            p1_md, p2_21_md, p2_22_md, p3_31_md, p3_33_md, p3_33_md2,
            p4_41_md, p4_42_md,
        )
