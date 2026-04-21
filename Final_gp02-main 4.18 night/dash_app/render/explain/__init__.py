"""统一讲解层 — 按 UI 区域组织所有前端可见文字的生成逻辑。

目录结构 = UI 区域；bug 定位的唯一索引：

* ``main_p0/``    主栏 P0 讲解（相关性 / Beta / 环境报告 / 逻辑说明）
* ``main_p1/``    主栏 P1 讲解（分组分析）
* ``main_p2/``    主栏 P2 讲解（影子 / Figure2.1 / Figure2.2）
* ``main_p3/``    主栏 P3 讲解（AdaptiveOptimizer / 双轨 MC）
* ``main_p4/``    主栏 P4 讲解（Fig4.1 fallback + Fig4.2）
* ``sidebar_right/``  侧栏 FigX.1-6 讲解卡 + 对应 defense-tag 条件行
* ``topbar/``     顶栏系统诊断 + Phase 0 聚合条件行

公共基础设施：

* ``_loaders.py``    FigX.*.md / Fig4.*.md 模板加载 + 占位符替换
* ``_formatters.py`` 复用的 MD 格式化工具
"""

from __future__ import annotations

# ── main panels ─────────────────────────────────────────────────────────────
from dash_app.render.explain.main_p0.bodies import (
    ME_PHASE0_TAB_INTRO_BODY,
    P0_BETA_BY_CLASS_MD,
    P0_BETA_CHEATSHEET_MD,
    P0_BETA_NONSTEADY_MD,
    P0_HEATMAP_BODY_MD,
    p0_beta_by_class,
    p0_beta_cheatsheet,
    p0_beta_nonsteady,
    p0_heatmap_body,
)
from dash_app.render.explain.main_p0.card_titles import (
    p0_beta_card_title,
    p0_heatmap_card_title,
)
from dash_app.render.explain.main_p0.narrative import (
    about_phase0_logic,
    me_phase0_intro_md,
)
from dash_app.render.explain.main_p1.bodies import (
    ME_PHASE1_INTRO,
    P1_STAT_METHOD_MD,
    p1_stat_method,
)
from dash_app.render.explain.main_p1.narrative import narrative_p1_group_analysis
from dash_app.render.explain.main_p2.bodies import (
    ME_PHASE2_INTRO,
    P2_FIG21_INTRO_MD,
    P2_PIXEL_SHADOW_INTRO_MD,
    p2_fig21_intro,
    p2_pixel_shadow_intro,
)
from dash_app.render.explain.main_p3.bodies import (
    ME_PHASE3_INTRO,
    P3_SECTION_31_ADAPTIVE_MD,
    P3_SECTION_32_DUAL_MC_MD,
    p3_section_31_adaptive,
    p3_section_31_table_md,
    p3_section_32_dual_mc,
    p3_section_32_dual_mc_md_list,
)
from dash_app.render.explain.main_p4.bodies import ME_PHASE4_INTRO
from dash_app.render.explain.main_p4.fig41 import build_fig41_explain_body
from dash_app.render.explain.main_p4.fig42 import build_fig42_body

# ── sidebar_right ───────────────────────────────────────────────────────────
from dash_app.render.explain.sidebar_right.figx1 import (
    build_figx1_explain_body,
    figx1_condition_line,
)
from dash_app.render.explain.sidebar_right.figx2 import (
    build_figx2_explain_body,
    figx2_condition_line,
)
from dash_app.render.explain.sidebar_right.figx3 import (
    build_figx3_explain_body,
    figx3_condition_line,
    format_adf_diagnostic_detail,
)
from dash_app.render.explain.sidebar_right.figx4 import (
    build_figx4_explain_body,
    figx4_condition_line,
)
from dash_app.render.explain.sidebar_right.figx5 import (
    build_figx5_explain_body,
    figx5_condition_line,
)
from dash_app.render.explain.sidebar_right.figx6 import (
    build_figx6_explain_body,
    figx6_condition_line,
)

# ── topbar ──────────────────────────────────────────────────────────────────
from dash_app.render.explain.topbar.defense_intro import render_defense_intro_alerts
from dash_app.render.explain.topbar.diagnosis import system_diagnosis_headline
from dash_app.render.explain.topbar.p0_aggregate_line import p0_aggregate_condition_line

# ── FigX 讲解卡片 bundle（所有 FigX 变量注入 + 模板替换的通用入口）──────────
from dash_app.render.explain.figure_captions import build_figure_caption_bundle

__all__ = [
    # main_p0
    "ME_PHASE0_TAB_INTRO_BODY",
    "P0_BETA_BY_CLASS_MD",
    "P0_BETA_CHEATSHEET_MD",
    "P0_BETA_NONSTEADY_MD",
    "P0_HEATMAP_BODY_MD",
    "p0_beta_card_title",
    "p0_heatmap_card_title",
    "p0_heatmap_body",
    "p0_beta_cheatsheet",
    "p0_beta_nonsteady",
    "p0_beta_by_class",
    "about_phase0_logic",
    "me_phase0_intro_md",
    # main_p1
    "ME_PHASE1_INTRO",
    "P1_STAT_METHOD_MD",
    "p1_stat_method",
    "narrative_p1_group_analysis",
    # main_p2
    "ME_PHASE2_INTRO",
    "P2_FIG21_INTRO_MD",
    "P2_PIXEL_SHADOW_INTRO_MD",
    "p2_pixel_shadow_intro",
    "p2_fig21_intro",
    # main_p3
    "ME_PHASE3_INTRO",
    "P3_SECTION_31_ADAPTIVE_MD",
    "P3_SECTION_32_DUAL_MC_MD",
    "p3_section_31_adaptive",
    "p3_section_31_table_md",
    "p3_section_32_dual_mc",
    "p3_section_32_dual_mc_md_list",
    # main_p4
    "ME_PHASE4_INTRO",
    "build_fig41_explain_body",
    "build_fig42_body",
    # sidebar_right
    "build_figx1_explain_body",
    "build_figx2_explain_body",
    "build_figx3_explain_body",
    "build_figx4_explain_body",
    "build_figx5_explain_body",
    "build_figx6_explain_body",
    "figx1_condition_line",
    "figx2_condition_line",
    "figx3_condition_line",
    "figx4_condition_line",
    "figx5_condition_line",
    "figx6_condition_line",
    "format_adf_diagnostic_detail",
    # topbar
    "system_diagnosis_headline",
    "p0_aggregate_condition_line",
    "render_defense_intro_alerts",
    # figure_captions bundle
    "build_figure_caption_bundle",
]
