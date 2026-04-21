"""Dashboard 渲染层的数据契约（按 UI 区域一一对应）。

所有 dataclass 均 ``frozen=True``。每个字段直接对应回调里的一个 Output 槽位。

**简化原则**：仅保留前端网页真正出现/必需的槽位。历史上的隐藏占位已从
``ui/main_p2.py`` / ``ui/main_p3.py`` 布局、回调 Output 列表与本契约中一并删除。

共 **50 个槽位**（49 旧槽 + ``fig-p3-best-table`` 新增 1 槽；原 59，去掉 8 个隐藏占位后再加 1）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# --------------------------------------------------------------------------- #
# 共享上下文                                                                   #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class DashboardState:
    """渲染需要的**全部**上下文（一次性抽取）。"""

    snap_json: Dict[str, Any]
    policy: Any                               # DefensePolicyConfig

    p0: Dict[str, Any]
    p1: Dict[str, Any]
    p2: Dict[str, Any]
    p3: Dict[str, Any]
    meta: Dict[str, Any]
    env: Dict[str, Any]

    defense_level: int
    symbols: List[str]
    api_err: Optional[str]
    s_val: float
    ui_mode: Optional[str]
    tpl: str
    p2_sym_state: Optional[str]
    # Fig 4.1a (mm) / Fig 4.1b (mv) 的独立标的搜索值（可选）；由
    # ``dashboard_pipeline._render_dashboard_face`` 从两个独立的 dropdown
    # ``p4-verify-search`` / ``p4-verify-search-b`` 透传。``render/main_p4``
    # 用 ``p4_focus_a`` 做 4.1a 的 ``focus_override``，``p4_focus_b`` 做 4.1b 的。
    # 两者缺省时回退到 ``p2_sym_state`` 以兼容旧行为。
    p4_focus_a: Optional[str]
    p4_focus_b: Optional[str]
    json_path: str
    objective_name: str

    train_start: str
    train_end: str
    test_start: str
    test_end: str

    benchmark: str
    tech_m: List[str]
    hedge_m: List[str]
    safe_m: List[str]

    h_struct: float
    tau_h1: float
    tau_l1: float
    tau_l2: float
    tau_s_low: float
    tau_vol_melt: float
    tau_return_ac1: float
    semantic_cos_window: int
    jsd_tri: float
    jsd_thr: float
    jsd_pairs_mean: float
    consistency: float
    s_min_sb: float

    best_per_sym: Dict[str, str]
    model_mu: Dict[str, Any]
    model_sigma: Dict[str, Any]
    model_mu_test_ts: Dict[str, Any]
    model_sigma_test_ts: Dict[str, Any]
    test_forecast_dates: List[str]
    weights: Dict[str, Any]

    diagnostics: List[Dict[str, Any]]


# --------------------------------------------------------------------------- #
# 主栏 P0（7 槽；历史上的 diagnostic-summary 与 p0-noise-level 已剔除，         #
# 同等信息保留在顶栏 defense-tag + 侧栏 FigX 中）                              #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MainP0Components:
    header: Any                               # header-status
    fig_corr: Any                             # fig-p0-corr
    fig_beta: Any                             # fig-p0-beta
    p0_heatmap_text: Any                      # p0-heatmap-text
    p0_beta_text_stack: Any                   # p0-beta-text-stack
    p0_asset_class_analysis: Any              # p0-asset-class-analysis
    about_p0: Any                             # about-phase0-logic


# --------------------------------------------------------------------------- #
# 主栏 P1（3 槽）                                                              #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MainP1Components:
    p1_grid: Any                              # p1-asset-cards
    card_p1: Any                              # card-p1
    p1_group_analysis: Any                    # p1-group-analysis


# --------------------------------------------------------------------------- #
# 主栏 P2（5 槽 — 已剔除 8 个隐藏占位，详见 ui/main_p2.py）                      #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MainP2Components:
    p2_opts: List[Dict[str, str]]             # p2-symbol options
    p2_val: Optional[str]                     # p2-symbol value
    p2_best_hero: Any                         # p2-best-model
    fig_p2_pixels: Any                        # fig-p2-best-pixels
    fig_p2_dens: Any                          # fig-p2-density


# --------------------------------------------------------------------------- #
# 主栏 P3（5 槽 — 剔除 fig-p3-semantic / fig-p3-shadow；新增 fig-p3-best-table） #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MainP3Components:
    obj_banner: Any                           # objective-banner
    fig_mc: Any                               # fig-p3-mc (Figure3.3 可见)
    fig_w: Any                                # fig-p3-weights (Figure3.2 可见)
    card_p3: Any                              # card-p3 (保留可见占位)
    fig_best_table: Any = None                # fig-p3-best-table (Figure3.1 可见；默认 None 兼容旧构造)


# --------------------------------------------------------------------------- #
# 主栏 P4（11 槽 — Fig 4.1a（mm）4 槽 + Fig 4.1b（mv）4 槽 + Fig 4.1 结论 1 +
#                     实验栈 1 + Fig 4.2 结论 1）
#                                                                              #
# R2 起预警日 ``alarm_banner`` 与 ``analysis_md`` 拆成独立槽位，便于 UI 布局把
# *预警日 banner* 放到 *标的搜索栏* 上方；``analysis_md`` 只承载 Part 2-5 / fallback。
# R3 新增 ``p4_fig42_conclusion``：与 Fig 4.1 结论对称的独立 Card，位于 Fig 4.2
# experiments-stack 下方、讲解卡之上；文案来自 ``content-{LANG}/Res/Fig4.2-Res.md`` §9.1。
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MainP4Components:
    p4_experiments: Any                       # p4-experiments-stack
    # Fig 4.1a · 模型—模型应力
    p4_fig41_alarm_banner: Any                # p4-fig41-alarm-banner  (mm 预警日 banner；idle 态为空 Div)
    p4_fig41_jsd: Any                         # p4-fig41-jsd           (mm daily returns)
    p4_verify_hero: Any                       # p4-verify-hero         (mm hero；idle 态为空 Div)
    p4_fig41_analysis_md: Any                 # p4-fig41-analysis-md   (mm Part 2-5 / fallback)
    # Fig 4.1b · 模型应力—市场载荷方向
    p4_fig41b_alarm_banner: Any               # p4-fig41b-alarm-banner (mv 预警日 banner)
    p4_fig41b_jsd: Any                        # p4-fig41b-jsd          (mv daily returns)
    p4_fig41b_verify_hero: Any                # p4-fig41b-verify-hero  (mv hero)
    p4_fig41b_analysis_md: Any                # p4-fig41b-analysis-md  (mv Part 2-5 / fallback)
    # Fig 4.1 独立结论卡
    p4_fig41_conclusion: Any                  # p4-fig41-conclusion
    # Fig 4.2 独立结论卡（experiments-stack 之下、讲解卡之上）
    p4_fig42_conclusion: Any                  # p4-fig42-conclusion


# --------------------------------------------------------------------------- #
# 侧栏 2 (sidebar right)（21 槽）                                              #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SidebarRightComponents:
    p2_traffic: Any                           # sb2-p2-traffic-lights

    sb2_defense_badge: Any                    # sb2-defense-level-badge

    fig_sb2_st: Any                           # sb2-fig-st
    fig_sb2_h_struct: Any                     # sb2-fig-h-struct
    fig_sb2_consistency: Any                  # sb2-fig-consistency
    fig_sb2_jsd: Any                          # sb2-fig-jsd-stress
    fig_sb2_cosine: Any                       # sb2-fig-cosine

    sb2_jsd_reason: Any                       # sb2-fig-jsd-stress-reason
    sb2_cos_reason: Any                       # sb2-fig-cosine-reason
    sb2_st_reason: Any                        # sb2-fig-st-reason
    sb2_h_struct_reason: Any                  # sb2-fig-h-struct-reason
    sb2_consistency_reason: Any               # sb2-fig-consistency-reason

    caption_bundle: Dict[str, Any]            # figure-caption-bundle
    figx1_explain: Any                        # sb2-explain-slot-01
    figx2_explain: Any                        # sb2-explain-slot-02
    figx3_cards: Any                          # sb2-fig-vol-ac1-cards
    figx3_reason: Any                         # sb2-fig-vol-ac1-reason
    figx3_explain: Any                        # sb2-explain-slot-03
    figx4_explain: Any                        # sb2-explain-slot-04
    figx5_explain: Any                        # sb2-explain-slot-05
    figx6_explain: Any                        # sb2-explain-slot-06

    # 顶栏"当前防御状态"横向展开用的**原始** (body, severity) 6 元组；
    # key ∈ {"st","h_struct","figx3","consistency","jsd","cos"}。
    # 侧栏的 sb2_*_reason 已经按 ``_should_show_defense_tag`` 做过宽松过滤
    # （level 2 展 danger+warn+success），不够严；topbar 需要"只与当前等级严格
    # 相符"的过滤（L2 只展 danger、L1 只展 warn、L0 只展 success），因此必须
    # 拿到未过滤的原始 (body, severity) 自行渲染。
    topbar_reason_raw: Dict[str, Tuple[Any, str]] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# 顶栏动态（2 槽）                                                             #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class TopbarDynamicComponents:
    defense_intro_slot: Any                   # topbar-defense-intro-slot
    reasons_collapse: Any                     # topbar-defense-reasons-collapse
