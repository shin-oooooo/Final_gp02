"""侧栏 2 (sidebar right) 渲染 — 全部 FigX 相关内容在此。

**21 个槽位**：
* 1 个标的交通灯（数据来自 Phase 2 但显示在右栏）
* 1 个当前防御状态 badge
* 5 个主图（S_t / 结构熵 rail / 可信度 rail / JSD 应力 / 语义余弦）
* 5 条 reason 小条
* 1 个 caption bundle
* 6 张 FigX.1-6 讲解卡片
* 2 个 FigX.3 异常卡片 + 其 reason
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Tuple

from dash import html

from dash_app.render.contracts import DashboardState, SidebarRightComponents

logger = logging.getLogger("dash_app.render.sidebar_right")
_TRACE = os.environ.get("DEBUG_RENDER", "0").strip() not in ("", "0", "false", "False")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if _TRACE:
        try:
            print(f"[sidebar_right] {msg % args}" if args else f"[sidebar_right] {msg}")
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Reason 显示策略（本区域内部使用）                                            #
# --------------------------------------------------------------------------- #


def _should_show_defense_tag(severity: str, level: int) -> bool:
    """Level 2 显 danger+warn+success；Level 1 显 warn+success；Level 0 仅显 success。"""
    if level >= 2:
        return severity in ("danger", "warn", "success")
    if level == 1:
        return severity in ("warn", "success")
    return severity == "success"


def _reason_div(body: Any, severity: str, level: int) -> Any:
    """根据 should_show 决定是否渲染；否则返回空 Div。"""
    from dash_app.dash_ui_helpers import _div_from_fig_line

    if not _should_show_defense_tag(severity, level):
        return html.Div()
    return html.Div([_div_from_fig_line((body, severity))])


# --------------------------------------------------------------------------- #
# FigX.3 异常资产抽取 + 卡片                                                   #
# --------------------------------------------------------------------------- #


def _extract_figx3_items(
    diagnostics: List[Dict[str, Any]],
    tau_vol_melt: float,
    tau_ac1: float,
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
    """返回 (adf_fail_items, vol_items, ac1_items)。"""
    from dash_app.render.explain import format_adf_diagnostic_detail
    from research.defense_state import diagnostic_failed_adf

    adf_fail = [
        {"symbol": d.get("symbol", "?"), "value": format_adf_diagnostic_detail(d)}
        for d in diagnostics if diagnostic_failed_adf(d)
    ]
    vol = [
        {"symbol": d.get("symbol", "?"), "value": f"{float(d.get('vol_ann') or 0.0):.2%}"}
        for d in diagnostics if float(d.get("vol_ann") or 0.0) > tau_vol_melt
    ]
    ac1 = [
        {"symbol": d.get("symbol", "?"), "value": f"AC1={float(d.get('ac1') or 0.0):.4f}"}
        for d in diagnostics if float(d.get("ac1") or 0.0) < tau_ac1
    ]
    _trace("figx3 items: adf=%d vol=%d ac1=%d", len(adf_fail), len(vol), len(ac1))
    return adf_fail, vol, ac1


def _build_figx3_cards(
    adf_fail: List[Dict[str, str]],
    vol: List[Dict[str, str]],
    ac1: List[Dict[str, str]],
    tau_vol_melt: float,
    tau_ac1: float,
) -> Any:
    """FigX.3 异常资产三行卡片。"""
    from dash_app.ui.sidebar_right import _asset_anomaly_row

    if not adf_fail and not vol and not ac1:
        return html.Div(
            html.Div(
                "资产诊断正常：无 ADF 检验失败、无显著高波动或低自相关异常。",
                className="small text-muted",
            ),
            className="mb-2",
        )
    return html.Div(
        [
            _asset_anomaly_row("未通过 ADF 检验（训练窗对数收益）", adf_fail, "danger"),
            _asset_anomaly_row(f"高波动资产（> τ_vol={tau_vol_melt:.2%}）", vol, "danger"),
            _asset_anomaly_row(f"低 AC1 资产（< τ_ac1={tau_ac1:.4f}）", ac1, "warning"),
        ]
    )


# --------------------------------------------------------------------------- #
# 顶部：标的交通灯 + 防御状态 badge                                            #
# --------------------------------------------------------------------------- #


def _build_p2_traffic(state: DashboardState) -> Any:
    """sb2-p2-traffic-lights — 标的交通灯（ARIMA/LGBM/Kronos）。"""
    from dash_app.dash_ui_helpers import _p2_traffic_row

    return _p2_traffic_row(state.p2, large=True, badges_only=True)


def _build_defense_badge(state: DashboardState) -> Any:
    """侧栏顶部当前防御状态 badge。"""
    from dash_app.dash_ui_helpers import _defense_status_badge

    status_label, _ = _defense_status_badge(state.defense_level)
    cls = (
        "defense-reason-tag danger mb-0 py-2 small"
        if state.defense_level >= 2
        else (
            "defense-reason-tag warn mb-0 py-2 small"
            if state.defense_level == 1
            else "defense-reason-tag success mb-0 py-2 small"
        )
    )
    return html.Div(
        html.Div(f"当前防御状态：{status_label}", className="reason-body fw-bold"),
        className=cls,
    )


# --------------------------------------------------------------------------- #
# 5 个主图                                                                     #
# --------------------------------------------------------------------------- #


def _build_sb2_figures(state: DashboardState) -> Tuple[Any, Any, Any, Any, Any]:
    """S_t / 结构熵 rail / 可信度 rail / JSD 应力 / 余弦。"""
    from dash_app.figures import (
        fig_defense_jsd_stress_timeseries,
        fig_defense_semantic_cosine,
        fig_st_sentiment_path,
    )
    from dash_app.ui.metric_rails import credibility_rail, structural_entropy_rail

    tst_st = state.meta.get("test_sentiment_st")
    # `sentiment_st_trace` 由 research/sentiment/series.py 的 constant-trap guards
    # 注入（详见 ARCHITECTURE.md §7 step 3）。只要任一 guard 触发就会有
    # ``constant_trap_synthetic=True`` 字段，图内会出现橙黄警示横幅。
    st_trace = state.meta.get("sentiment_st_trace") if isinstance(state.meta, dict) else None
    fig_sb2_st = fig_st_sentiment_path(
        tst_st,
        state.s_val,
        state.tpl,
        figure_title="FigX.1",
        st_trace=st_trace if isinstance(st_trace, dict) else None,
    )
    fig_sb2_h = structural_entropy_rail(state.h_struct, state.tau_h1)
    fig_sb2_c = credibility_rail(state.consistency, state.tau_l2, state.tau_l1)
    fig_sb2_jsd = fig_defense_jsd_stress_timeseries(
        state.p2,
        float(state.p2.get("jsd_baseline_mean") or 0.0),
        float(getattr(state.policy, "k_jsd", 2.0) or 2.0),
        int(state.semantic_cos_window),
        state.tpl,
        baseline_eps=float(getattr(state.policy, "jsd_baseline_eps", 1e-9) or 1e-9),
        figure_title="FigX.5",
    )
    fig_sb2_cos = fig_defense_semantic_cosine(
        state.p2, state.meta, state.semantic_cos_window, state.tpl, figure_title="FigX.6",
    )
    return fig_sb2_st, fig_sb2_h, fig_sb2_c, fig_sb2_jsd, fig_sb2_cos


# --------------------------------------------------------------------------- #
# 6 条 reason 小条                                                             #
# --------------------------------------------------------------------------- #


_IDLE_REASON_BODIES: Dict[str, str] = {
    "st": "FigX.1: 未执行管线→当前变量对防御等级切换无影响",
    "h_struct": "FigX.2: 未执行管线→当前变量对防御等级切换无影响",
    "figx3": "FigX.3: 未执行管线→当前变量对防御等级切换无影响",
    "consistency": "FigX.4: 未执行管线→当前变量对防御等级切换无影响",
    "jsd": "FigX.5: 未执行管线→当前变量对防御等级切换无影响",
    "cos": "FigX.6: 未执行管线→当前变量对防御等级切换无影响",
}


def _build_reason_strip(
    state: DashboardState,
    figx3_items: Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]],
) -> Dict[str, Any]:
    """6 条 reason（FigX.1-6，figx3 用于顶栏 reasons-collapse 复用）。

    idle 态（``snap_json["_is_idle"] == True``）走占位分支：所有 6 张 reason
    返回 success 级别的占位（"未执行管线→当前变量对防御等级切换无影响"），
    避免因 ``h_struct=0`` / ``credibility=0`` 撞 FigX.2 / FigX.4 的 warn / danger
    分支而被 Level 0 过滤掉、导致"运行前 X.2 / X.4 defense-tag 不显示"。
    """
    from dash_app.render.explain import (
        figx1_condition_line, figx2_condition_line, figx3_condition_line,
        figx4_condition_line, figx5_condition_line, figx6_condition_line,
    )

    lvl = state.defense_level

    if bool(state.snap_json.get("_is_idle")):
        filtered = {
            f"{key}_reason": _reason_div(body, "success", lvl)
            for key, body in _IDLE_REASON_BODIES.items()
        }
        return {
            **filtered,
            "_raw": {key: (body, "success") for key, body in _IDLE_REASON_BODIES.items()},
        }

    adf_fail, vol, ac1 = figx3_items

    b1, s1 = figx1_condition_line(
        s_min=state.s_min_sb, tau_s_low=state.tau_s_low,
        c=state.consistency, tau_l1=state.tau_l1,
    )
    b2, s2 = figx2_condition_line(h_struct=state.h_struct, tau_h1=state.tau_h1)
    b3, s3 = figx3_condition_line(
        adf_fail_assets=adf_fail, vol_assets=vol, ac1_assets=ac1,
        tau_vol_melt=state.tau_vol_melt, tau_return_ac1=state.tau_return_ac1,
    )
    b4, s4 = figx4_condition_line(c=state.consistency, tau_l2=state.tau_l2, tau_l1=state.tau_l1)
    b5, s5 = figx5_condition_line(
        snap=state.snap_json, p2=state.p2, pol=state.policy,
        jsd_stress=bool(state.p2.get("jsd_stress")),
    )
    b6, s6 = figx6_condition_line(
        snap=state.snap_json, p2=state.p2, pol=state.policy, meta=state.meta,
        logic_break_cos=bool(state.p2.get("logic_break_semantic_cosine_negative")),
    )

    return {
        "st_reason": _reason_div(b1, s1, lvl),
        "h_struct_reason": _reason_div(b2, s2, lvl),
        "figx3_reason": _reason_div(b3, s3, lvl),
        "consistency_reason": _reason_div(b4, s4, lvl),
        "jsd_reason": _reason_div(b5, s5, lvl),
        "cos_reason": _reason_div(b6, s6, lvl),
        # 顶栏"严格只展示与当前防御等级严重度相符"的渲染走 raw 数据二次过滤；
        # 顺序沿用 FigX.1 → FigX.6。
        "_raw": {
            "st": (b1, s1),
            "h_struct": (b2, s2),
            "figx3": (b3, s3),
            "consistency": (b4, s4),
            "jsd": (b5, s5),
            "cos": (b6, s6),
        },
    }


# --------------------------------------------------------------------------- #
# FigX.1-6 讲解卡片 + caption bundle                                           #
# --------------------------------------------------------------------------- #


def _build_figx_explain_cards(state: DashboardState) -> Dict[str, Any]:
    """FigX.1-6 六张讲解卡片 + caption bundle。

    标题选择与 ``callbacks/research_panels.py::_explain_title`` 保持同源：研究模式
    优先 ``{base_key}_res``（「数据、参数与方法论详情」），缺失时回退到
    ``{base_key}``（「图表与方法简介」）；投资模式仅读 ``{base_key}``。
    """
    from dash_app.services.copy import get_figure_title
    from dash_app.render.explain import (
        build_figure_caption_bundle,
        build_figx1_explain_body, build_figx2_explain_body,
        build_figx3_explain_body, build_figx4_explain_body,
        build_figx5_explain_body, build_figx6_explain_body,
    )
    from dash_app.ui.layout import _analysis_card

    caption = build_figure_caption_bundle(
        state.ui_mode, state.snap_json, state.policy,
        state.p2, state.meta,
        jsd_thr_precomputed=float(state.jsd_thr),
    )

    mode = (state.ui_mode or "invest").strip().lower()

    def _pick_title(base_key: str, default_inv: str) -> str:
        if mode == "research":
            res_title = get_figure_title(f"{base_key}_res", "")
            if res_title:
                return res_title
        return get_figure_title(base_key, default_inv)

    def _card(title_key: str, title_default: str, body_builder) -> Any:
        return _analysis_card(
            _pick_title(title_key, title_default),
            body_builder(
                state.ui_mode, state.snap_json, state.policy,
                state.p2, state.meta, state.symbols, state.json_path,
            ),
        )

    return {
        "caption_bundle": caption,
        "figx1_explain": _card("fig_x_1_explain",
                               "FigX.1 讲解：测试窗 S_t（VADER 分段累积）",
                               build_figx1_explain_body),
        "figx2_explain": _card("fig_x_2_explain",
                               "FigX.2 讲解：结构熵与 Level 判定",
                               build_figx2_explain_body),
        "figx3_explain": _card("fig_x_3_explain",
                               "FigX.3 讲解：高波动与低自相关资产",
                               build_figx3_explain_body),
        "figx4_explain": _card("fig_x_4_explain",
                               "FigX.4 讲解：可信度评分与三态灯",
                               build_figx4_explain_body),
        "figx5_explain": _card("fig_x_5_explain",
                               "FigX.5 讲解：模型—模型应力检验",
                               build_figx5_explain_body),
        "figx6_explain": _card("fig_x_6_explain",
                               "FigX.6 讲解：语义–数值滚动余弦",
                               build_figx6_explain_body),
    }


# --------------------------------------------------------------------------- #
# 主入口                                                                       #
# --------------------------------------------------------------------------- #


def build_sidebar_right_components(state: DashboardState) -> SidebarRightComponents:
    """构造侧栏 2 全部 21 槽位。纯函数。

    Args:
        state: 已抽取好的 DashboardState。

    Returns:
        SidebarRightComponents — 包含所有 sb2-* / figure-caption-bundle /
        sb2-explain-slot-* / sb2-fig-vol-ac1-* 槽位。
    """
    assert isinstance(state, DashboardState), (
        f"state must be DashboardState, got {type(state).__name__}"
    )
    _trace("build_sidebar_right start defense_level=%d", state.defense_level)

    figx3_items = _extract_figx3_items(
        state.diagnostics, state.tau_vol_melt, state.tau_return_ac1,
    )
    fig_st, fig_h, fig_c, fig_jsd, fig_cos = _build_sb2_figures(state)
    reasons = _build_reason_strip(state, figx3_items)
    explains = _build_figx_explain_cards(state)

    adf_fail, vol, ac1 = figx3_items
    figx3_cards = _build_figx3_cards(
        adf_fail, vol, ac1, state.tau_vol_melt, state.tau_return_ac1,
    )

    out = SidebarRightComponents(
        p2_traffic=_build_p2_traffic(state),
        sb2_defense_badge=_build_defense_badge(state),
        fig_sb2_st=fig_st,
        fig_sb2_h_struct=fig_h,
        fig_sb2_consistency=fig_c,
        fig_sb2_jsd=fig_jsd,
        fig_sb2_cosine=fig_cos,
        sb2_jsd_reason=reasons["jsd_reason"],
        sb2_cos_reason=reasons["cos_reason"],
        sb2_st_reason=reasons["st_reason"],
        sb2_h_struct_reason=reasons["h_struct_reason"],
        sb2_consistency_reason=reasons["consistency_reason"],
        caption_bundle=explains["caption_bundle"],
        figx1_explain=explains["figx1_explain"],
        figx2_explain=explains["figx2_explain"],
        figx3_cards=figx3_cards,
        figx3_reason=reasons["figx3_reason"],
        figx3_explain=explains["figx3_explain"],
        figx4_explain=explains["figx4_explain"],
        figx5_explain=explains["figx5_explain"],
        figx6_explain=explains["figx6_explain"],
        topbar_reason_raw=reasons.get("_raw", {}),
    )
    _trace("build_sidebar_right done")
    return out
