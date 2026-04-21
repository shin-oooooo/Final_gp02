"""Dashboard 渲染总入口 — 薄 orchestrator。

**职责**：
1. 调 :func:`extract_dashboard_state` 得共享 state
2. 依次调各 UI 区域的 ``build_*`` 函数
3. 按 callback Output 顺序打包 **53 元组**（新增 Fig4.1b 3 槽 + 独立结论 1 槽；Chart 2 已移除）

**不要在这里写业务逻辑**。任何新 UI 内容都应该加到对应区域的
``render/<region>.py`` 文件里。槽位顺序必须与 ``callbacks/dashboard_pipeline.py``
中 ``_render_dashboard_face`` 的 Output 列表完全一致。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from dash_app.render import (
    build_main_p0,
    build_main_p1,
    build_main_p2,
    build_main_p3,
    build_main_p4,
    build_sidebar_right,
    build_topbar_dynamic,
    extract_dashboard_state,
)
from research.schemas import DefensePolicyConfig

# 必须与 ``callbacks/dashboard_pipeline.py`` 中 ``_render_dashboard_face`` 的 Output 个数一致。
DASHBOARD_FACE_OUTPUT_COUNT = 53


class DashboardFaceOutputTupleLenError(RuntimeError):
    """``render_dashboard_outputs`` / ``_render_dashboard_face`` 返回值元组长度非法。"""


logger = logging.getLogger("dash_app.dashboard_face_render")
_TRACE = os.environ.get("DEBUG_RENDER", "0").strip() not in ("", "0", "false", "False")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if _TRACE:
        try:
            print(f"[dashboard_face_render] {msg % args}" if args else f"[dashboard_face_render] {msg}")
        except Exception:
            pass


def render_dashboard_outputs(
    pol: DefensePolicyConfig,
    snap_json: Dict[str, Any],
    symbols: List[str],
    api_err: Optional[str],
    s_val: float,
    theme: Optional[str],
    p2_sym_state: Optional[str],
    ui_mode: Optional[str] = None,
) -> Tuple[Any, ...]:
    """管线成功时的 **53 元组**总装函数（新增 Fig4.1b 3 槽 + 独立结论 1 槽）。

    **纯函数**：不修改 snap_json / pol；所有 component 都是新对象。

    Args:
        pol: 管线使用的 ``DefensePolicyConfig``。
        snap_json: Pipeline 快照。
        symbols: 当前标的列表。
        api_err: 若 API 失败时为错误信息，否则 None。
        s_val: 整体情绪分 (S_t)。
        theme: Bootstrap 主题（``"light"`` / ``"dark"``）。
        p2_sym_state: 当前 P2 标的下拉值。
        ui_mode: ``"invest"`` / ``"research"``。

    Returns:
        53 个 Dash 组件 / 数据按 Output 顺序排列的 tuple。
    """
    assert isinstance(snap_json, dict), (
        f"snap_json must be dict, got {type(snap_json).__name__}"
    )
    assert isinstance(symbols, list), (
        f"symbols must be list, got {type(symbols).__name__}"
    )
    _trace("render start level=%s api_err=%s", snap_json.get("defense_level"), api_err)

    # 1. 共享 state
    state = extract_dashboard_state(
        snap_json, pol,
        symbols=symbols, api_err=api_err, s_val=s_val,
        theme=theme, p2_sym_state=p2_sym_state, ui_mode=ui_mode,
    )

    # 2. 各 UI 区域组件
    p0 = build_main_p0(state)
    p1 = build_main_p1(state)
    p2 = build_main_p2(state)
    p3 = build_main_p3(state)
    p4 = build_main_p4(state)
    sr = build_sidebar_right(state)
    tb = build_topbar_dynamic(
        state,
        sb2_st_reason=sr.sb2_st_reason,
        sb2_h_struct_reason=sr.sb2_h_struct_reason,
        figx3_reason=sr.figx3_reason,
        sb2_consistency_reason=sr.sb2_consistency_reason,
        sb2_jsd_reason=sr.sb2_jsd_reason,
        sb2_cos_reason=sr.sb2_cos_reason,
    )

    # 3. 按 callback Output 顺序打包（与 dashboard_pipeline.py 内列表严格对齐）
    out = (
        # main_p0 (9)
        p0.diag_alert,                        # 1  diagnostic-summary
        p0.header,                            # 2  header-status
        p0.fig_corr,                          # 3  fig-p0-corr
        p0.fig_beta,                          # 4  fig-p0-beta
        p0.p0_heatmap_text,                   # 5  p0-heatmap-text
        p0.p0_beta_text_stack,                # 6  p0-beta-text-stack
        p0.p0_asset_class_analysis,           # 7  p0-asset-class-analysis
        p0.noise_level_card,                  # 8  p0-noise-level
        p0.about_p0,                          # 9  about-phase0-logic
        # main_p1 (3)
        p1.p1_grid,                           # 10 p1-asset-cards
        p1.card_p1,                           # 11 card-p1
        p1.p1_group_analysis,                 # 12 p1-group-analysis
        # main_p2 (5)
        p2.p2_opts,                           # 13 p2-symbol options
        p2.p2_val,                            # 14 p2-symbol value
        p2.p2_best_hero,                      # 15 p2-best-model
        p2.fig_p2_pixels,                     # 16 fig-p2-best-pixels
        p2.fig_p2_dens,                       # 17 fig-p2-density
        # main_p3 (5; 原 4 槽 + 尾部新增 Figure3.1 最佳模型 μ/σ 表)
        p3.obj_banner,                        # 18 objective-banner
        p3.fig_mc,                            # 19 fig-p3-mc
        p3.fig_w,                             # 20 fig-p3-weights
        p3.card_p3,                           # 21 card-p3
        p3.fig_best_table,                    # 22 fig-p3-best-table (Figure3.1)
        # main_p4 (8 — Fig4.1a × 3 + Fig4.1b × 3 + 独立结论 × 1 + 实验栈 × 1)
        p4.p4_experiments,                    # 23 p4-experiments-stack
        # Fig 4.1a · 模型—模型
        p4.p4_fig41_jsd,                      # 24 p4-fig41-jsd
        p4.p4_verify_hero,                    # 25 p4-verify-hero
        p4.p4_fig41_analysis_md,              # 26 p4-fig41-analysis-md
        # Fig 4.1b · 模型应力—市场
        p4.p4_fig41b_jsd,                     # 27 p4-fig41b-jsd
        p4.p4_fig41b_verify_hero,             # 28 p4-fig41b-verify-hero
        p4.p4_fig41b_analysis_md,             # 29 p4-fig41b-analysis-md
        # 独立结论卡
        p4.p4_fig41_conclusion,               # 30 p4-fig41-conclusion
        # sidebar_right (21)
        sr.p2_traffic,                        # 31 sb2-p2-traffic-lights
        sr.sb2_defense_badge,                 # 32 sb2-defense-level-badge
        sr.fig_sb2_st,                        # 33 sb2-fig-st
        sr.fig_sb2_h_struct,                  # 34 sb2-fig-h-struct
        sr.fig_sb2_consistency,               # 35 sb2-fig-consistency
        sr.fig_sb2_jsd,                       # 36 sb2-fig-jsd-stress
        sr.fig_sb2_cosine,                    # 37 sb2-fig-cosine
        sr.sb2_jsd_reason,                    # 38 sb2-fig-jsd-stress-reason
        sr.sb2_cos_reason,                    # 39 sb2-fig-cosine-reason
        sr.sb2_st_reason,                     # 40 sb2-fig-st-reason
        sr.sb2_h_struct_reason,               # 41 sb2-fig-h-struct-reason
        sr.sb2_consistency_reason,            # 42 sb2-fig-consistency-reason
        sr.caption_bundle,                    # 43 figure-caption-bundle
        sr.figx1_explain,                     # 44 sb2-explain-slot-01
        sr.figx2_explain,                     # 45 sb2-explain-slot-02
        sr.figx3_cards,                       # 46 sb2-fig-vol-ac1-cards
        sr.figx3_reason,                      # 47 sb2-fig-vol-ac1-reason
        sr.figx3_explain,                     # 48 sb2-explain-slot-03
        sr.figx4_explain,                     # 49 sb2-explain-slot-04
        sr.figx5_explain,                     # 50 sb2-explain-slot-05
        sr.figx6_explain,                     # 51 sb2-explain-slot-06
        # topbar (2)
        tb.defense_intro_slot,                # 52 topbar-defense-intro-slot
        tb.reasons_collapse,                  # 53 topbar-defense-reasons-collapse
    )
    _trace("render done tuple_len=%d", len(out))
    print(f"DEBUG: Returning {len(out)} items")
    if len(out) != DASHBOARD_FACE_OUTPUT_COUNT:
        raise DashboardFaceOutputTupleLenError(
            f"render_dashboard_outputs: expected {DASHBOARD_FACE_OUTPUT_COUNT} values, got {len(out)}"
        )
    return out
