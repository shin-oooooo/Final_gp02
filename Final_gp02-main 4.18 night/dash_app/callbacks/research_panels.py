"""Research-panel callbacks."""
from typing import Any, Dict, List, Optional

import dash_bootstrap_components as dbc
from dash import ALL, MATCH, Input, Output, State, dcc, html
from dash.exceptions import PreventUpdate

from dash_app.ui.layout import (
    _analysis_card,
    _default_data_json_path,
    _fig_explain_title,
    _p0_resolved_window_strings,
    _templates,
)
from dash_app.render.explain import (
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
from dash_app.services.copy import get_figure_title
from research.schemas import DefensePolicyConfig

import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _explain_title(base_key: str, mode: Optional[str], default_inv: str) -> str:
    """Pick the explain-card title honoring invest/research mode.

    研究模式优先读 ``{base_key}_res``（「数据、参数与方法论详情」），缺失时回退到
    ``{base_key}``（「图表与方法简介」）；投资模式仅读 ``{base_key}``。兜底字符串
    仅在 md/json 双缺失时使用。
    """
    m = (mode or "invest").strip().lower()
    if m == "research":
        res_title = get_figure_title(f"{base_key}_res", "")
        if res_title:
            return res_title
    return get_figure_title(base_key, default_inv)


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
        Output("sb2-explain-slot-03", "children", allow_duplicate=True),  # FigX.3（补漏）
        Output("sb2-explain-slot-04", "children", allow_duplicate=True),  # FigX.4
        Output("sb2-explain-slot-05", "children", allow_duplicate=True),  # FigX.5
        Output("sb2-explain-slot-06", "children", allow_duplicate=True),  # FigX.6
        # --- 主栏 P4 讲解（补漏）---
        Output("p4-fig41-analysis-md", "children", allow_duplicate=True),
        Output("p4-experiments-stack", "children", allow_duplicate=True),
        # --- 主栏 P0 四张动态文本卡（新增 Inv/Res 切换）---
        Output("p0-heatmap-text", "children", allow_duplicate=True),
        Output("p0-beta-text-stack", "children", allow_duplicate=True),
        Output("p0-asset-class-analysis", "children", allow_duplicate=True),
        Output("about-phase0-logic", "children", allow_duplicate=True),
        # --- 主栏 P1/P2/P3 静态讲解卡（新增 Inv/Res 切换）---
        Output("p1-stat-method-card", "children", allow_duplicate=True),
        Output("p2-fig21-explain-card", "children", allow_duplicate=True),
        Output("p2-fig22-explain-card", "children", allow_duplicate=True),
        Output("p3-adaptive-intro-card", "children", allow_duplicate=True),
        Output("p3-fig33-explain-card", "children", allow_duplicate=True),
        Input("radio-ui-mode", "data"),
        State("last-snap", "data"),
        State("defense-policy-config", "data"),
        State("theme-store", "data"),
        prevent_initial_call=True,
    )
    def _caption_refresh_on_mode(
        mode: Optional[str], snap: Any, pol_j: Any, theme: Optional[str]
    ):
        """模式切换时**只刷新讲解类内容**，不重跑管线。

        覆盖范围：
        * 侧栏 FigX.1–6 讲解卡 + caption bundle（7 槽）
        * 主栏 P4：Fig4.1 analysis md + Fig4.2 实验栈（2 槽）
        * 主栏 P0：4 张动态文本卡（3 body + 1 about）（4 槽）
        * 主栏 P1/P2/P3：5 张静态讲解卡容器（5 槽）
        合计 18 槽，全部无感切换 Inv/Res 版本 MD。
        """
        if not isinstance(snap, dict) or not snap.get("phase2"):
            raise PreventUpdate

        # 惰性 import 以避免启动时循环依赖
        from dash_app.dash_ui_helpers import _p4_experiments_stack_block
        from dash_app.fig41 import Fig41Context, build_fig41, extract_fig41_bundle
        from dash_app.render import build_main_p0, extract_dashboard_state
        from dash_app.ui.main_p3 import build_p3_adaptive_intro_column

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
        # 研究模式读 `fig_x_N_explain_res`（「数据、参数与方法论详情」），投资模式读
        # `fig_x_N_explain`（「图表与方法简介」）。
        figx1 = _analysis_card(
            _explain_title("fig_x_1_explain", mode, "FigX.1 讲解：测试窗 S_t（VADER 分段累积）"),
            build_figx1_explain_body(mode, snap, pol, p2, meta, syms, jp),
        )
        figx2 = _analysis_card(
            _explain_title("fig_x_2_explain", mode, "FigX.2 讲解：结构熵与 Level 判定"),
            build_figx2_explain_body(mode, snap, pol, p2, meta, syms, jp),
        )
        figx3 = _analysis_card(
            _explain_title("fig_x_3_explain", mode, "FigX.3 讲解：高波动与低自相关资产"),
            build_figx3_explain_body(mode, snap, pol, p2, meta, syms, jp),
        )
        figx4 = _analysis_card(
            _explain_title("fig_x_4_explain", mode, "FigX.4 讲解：可信度评分与三态灯"),
            build_figx4_explain_body(mode, snap, pol, p2, meta, syms, jp),
        )
        figx5 = _analysis_card(
            _explain_title("fig_x_5_explain", mode, "FigX.5 讲解：模型—模型应力检验"),
            build_figx5_explain_body(mode, snap, pol, p2, meta, syms, jp),
        )
        figx6 = _analysis_card(
            _explain_title("fig_x_6_explain", mode, "FigX.6 讲解：语义–数值滚动余弦"),
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

        # ── P4：Fig4.2 实验栈（包含三权重对比 + 讲解长文）──
        p4_experiments = _p4_experiments_stack_block(snap, tpl, mode)

        # ── P1/P2/P3 静态讲解卡（只换 MD 正文，标题不变）──
        p1_card = _analysis_card(
            _fig_explain_title(1, 1, "统计方法说明（ADF / Ljung-Box / P 值含义）"),
            p1_stat_method(mode or "invest"),
        )
        p2_fig21 = _analysis_card(
            _fig_explain_title(2, 1, "影子择模与像素矩阵（MSE / 影子验证 / 综合分）"),
            p2_pixel_shadow_intro(mode or "invest"),
        )
        p2_fig22 = _analysis_card(
            _fig_explain_title(2, 2, "时间×收益密度（纵轴 · μ 脊线 · 着色）"),
            p2_fig21_intro(mode or "invest"),
        )
        p3_adaptive = build_p3_adaptive_intro_column(p3_section_31_adaptive(mode or "invest"))
        p3_fig33 = _analysis_card(
            _fig_explain_title(3, 3, "双轨蒙特卡洛"),
            p3_section_32_dual_mc(mode or "invest"),
        )

        # ── caption bundle ──
        caption = build_figure_caption_bundle(mode, snap, pol, p2, meta)

        return (
            caption,
            figx1, figx2, figx3, figx4, figx5, figx6,
            p4_fig41_panel, p4_experiments,
            p0_heatmap, p0_beta_stack, p0_asset_class, p0_about,
            p1_card, p2_fig21, p2_fig22, p3_adaptive, p3_fig33,
        )
