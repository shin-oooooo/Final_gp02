"""主栏 P4 渲染 — 预警有效性（Fig4.1a + Fig4.1b + 独立结论卡）+ 防御策略实验栈（Fig4.2）。

薄壳：
* **Fig4.1a**（模型—模型 / JSD） 与 **Fig4.1b**（模型应力—市场载荷方向 / 余弦）复用
  ``dash_app.fig41`` 子模块（同一套 contracts/extract/render），仅在调用时通过
  ``verify_key`` 切换数据源、通过 ``signal_label`` / ``alarm_date_iso`` 切换顶行 banner。
  两图各自使用独立的 ``focus_override``：4.1a 来自 ``state.p4_focus_a``
  （顶栏 ``p4-verify-search``），4.1b 来自 ``state.p4_focus_b``
  （顶栏 ``p4-verify-search-b``）。
* **Fig 4.1 独立结论卡**由 ``build_fig41_conclusion_card(dual)`` 产出；情形 A–D 内容来自
  ``content-CHN/p4_conclusion_analysis.md``。
* **Fig4.2 + 其他实验栈** 调用 ``dash_ui_helpers._p4_experiments_stack_block``。
* **Fig 4.2 独立结论卡**由 ``build_fig42_conclusion_card(snap, dv, ui_mode)`` 产出；
  情形 A–E 文案来自 ``content-{LANG}/Res/Fig4.2-Res.md §9.1``（E 追加 §9.2 归因）。

**11 个主栏 P4 槽位**：
``p4-experiments-stack``、
``p4-fig41-alarm-banner / p4-fig41-jsd / p4-verify-hero / p4-fig41-analysis-md``（Fig 4.1a）、
``p4-fig41b-alarm-banner / p4-fig41b-jsd / p4-fig41b-verify-hero / p4-fig41b-analysis-md``（Fig 4.1b）、
``p4-fig41-conclusion``（Fig 4.1 独立结论）、
``p4-fig42-conclusion``（Fig 4.2 独立结论）。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from dash_app.fig41 import (
    Fig41Components,
    Fig41Context,
    Fig41DualVerdict,
    build_fig41,
    build_fig41_conclusion_card,
    extract_fig41_bundle,
)
from dash_app.render.contracts import DashboardState, MainP4Components
from dash_app.render.explain.main_p4.fig42_conclusion import (
    build_fig42_conclusion_card,
)
from dash_app.services.copy import get_status_message

logger = logging.getLogger("dash_app.render.main_p4")
_TRACE = os.environ.get("DEBUG_RENDER", "0").strip() not in ("", "0", "false", "False")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if _TRACE:
        try:
            print(f"[main_p4] {msg % args}" if args else f"[main_p4] {msg}")
        except Exception:
            pass


def _build_p4_experiments(state: DashboardState) -> Any:
    """P4 实验栈（Fig4.2 三权重等）。"""
    from dash_app.dash_ui_helpers import _p4_experiments_stack_block

    return _p4_experiments_stack_block(state.snap_json, state.tpl, state.ui_mode)


def _build_fig41_for_signal(
    state: DashboardState,
    *,
    verify_key: str,
    signal_label: str,
    alarm_date_iso: Optional[str],
    focus_override: Optional[str],
) -> Fig41Components:
    """调用 fig41 子模块，抽取指定 verify_key 的 bundle 并渲染。

    Args:
        focus_override: 该图专属的 P4 搜索框值（4.1a 用 ``p4-verify-search``，
            4.1b 用 ``p4-verify-search-b``）。两图搜索框相互独立，不再共用
            ``p2_sym_state``；旧行为由调用方在外层做必要的回退。
    """
    bundle = extract_fig41_bundle(
        state.snap_json, state.policy, verify_key=verify_key
    )
    context = Fig41Context(
        tpl=state.tpl,
        ui_mode=state.ui_mode,
        snap_json=state.snap_json,
        policy=state.policy,
        p2=state.p2,
        meta=state.meta,
        symbols=state.symbols,
        focus_override=focus_override,
        signal_label=signal_label,
        alarm_date_iso=alarm_date_iso,
    )
    return build_fig41(bundle, context)


def _extract_dual_for_conclusion(state: DashboardState) -> Optional[Fig41DualVerdict]:
    """从任一 bundle 读 ``dual``（两路字段本来就装在同一 snapshot 里，结果等价）。"""
    bundle = extract_fig41_bundle(state.snap_json, state.policy)
    return bundle.dual


def build_main_p4_components(state: DashboardState) -> MainP4Components:
    """构造主栏 P4 全部 11 个槽位（Fig 4.1a × 4 + Fig 4.1b × 4 + Fig 4.1 结论 +
    实验栈 + Fig 4.2 结论）。纯函数。"""
    assert isinstance(state, DashboardState), (
        f"state must be DashboardState, got {type(state).__name__}"
    )
    _trace("build_main_p4 start")

    # 双路：mm（JSD）+ mv（余弦）
    # 预先从综合 bundle 拿 dual，用于 banner 的准确日期
    dual = _extract_dual_for_conclusion(state)
    mm_label = get_status_message("fig41_banner_mm_title", "模型—模型应力预警日")
    mv_label = get_status_message("fig41_banner_mv_title", "模型应力—市场载荷方向预警日")

    # 两图独立的 focus：分别来自 p4-verify-search / p4-verify-search-b。
    # 兼容旧行为：若某一侧未提供（None），则回退到 p2_sym_state。
    focus_a = state.p4_focus_a if isinstance(state.p4_focus_a, str) and state.p4_focus_a else None
    focus_b = state.p4_focus_b if isinstance(state.p4_focus_b, str) and state.p4_focus_b else None
    if focus_a is None and isinstance(state.p2_sym_state, str):
        focus_a = state.p2_sym_state
    if focus_b is None and isinstance(state.p2_sym_state, str):
        focus_b = state.p2_sym_state

    comp_mm = _build_fig41_for_signal(
        state,
        verify_key="fig41_verify_mm",
        signal_label=mm_label,
        alarm_date_iso=(dual.mm_t0_date if dual else None),
        focus_override=focus_a,
    )
    comp_mv = _build_fig41_for_signal(
        state,
        verify_key="fig41_verify_mv",
        signal_label=mv_label,
        alarm_date_iso=(dual.mv_t0_date if dual else None),
        focus_override=focus_b,
    )

    conclusion_card = build_fig41_conclusion_card(dual)

    # Fig 4.2 独立结论卡（情形 A–E；E 情形附 §9.2 归因）
    p3 = state.snap_json.get("phase3") if isinstance(state.snap_json, dict) else {}
    dv = (p3 or {}).get("defense_validation") if isinstance(p3, dict) else {}
    fig42_conclusion_card = build_fig42_conclusion_card(
        state.snap_json, dv if isinstance(dv, dict) else {}, state.ui_mode
    )

    out = MainP4Components(
        p4_experiments=_build_p4_experiments(state),
        # Fig 4.1a · mm
        p4_fig41_alarm_banner=comp_mm.alarm_banner,
        p4_fig41_jsd=comp_mm.fig_daily_returns,
        p4_verify_hero=comp_mm.hero,
        p4_fig41_analysis_md=comp_mm.panel,
        # Fig 4.1b · mv
        p4_fig41b_alarm_banner=comp_mv.alarm_banner,
        p4_fig41b_jsd=comp_mv.fig_daily_returns,
        p4_fig41b_verify_hero=comp_mv.hero,
        p4_fig41b_analysis_md=comp_mv.panel,
        # Fig 4.1 独立结论卡
        p4_fig41_conclusion=conclusion_card,
        # Fig 4.2 独立结论卡
        p4_fig42_conclusion=fig42_conclusion_card,
    )
    _trace("build_main_p4 done")
    return out
