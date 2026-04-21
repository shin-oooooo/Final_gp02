"""Shared Dash UI helpers (extracted from app.py)."""
from __future__ import annotations

import copy
import math
import re
import os
from typing import Any, Dict, List, Optional, Set, Tuple

import dash_bootstrap_components as dbc
from dash import dcc, html

from dash_app.services.copy import get_figure_title, get_status_message
from dash_app.render.explain import build_fig42_body, p0_aggregate_condition_line
from dash_app.figures import fig_p3_triple_test_equity

from dash_app.constants import (
    _CAT_COLORS,
    _CAT_LABELS,
    _CATS,
    _DEFAULT_UNIVERSE,
    _EXTRA_COLORS,
    _P2_MODEL_COLOR,
    _P2_MODEL_LABEL,
)
from dash_app.ui.layout import _default_data_json_path, _figure_wrap
from dash_app.ui.p0_universe_helpers import (
    _build_p0_asset_tree,
    _cat_header_dimmed,
    _coerce_sym_list,
    _flatten_universe,
    _merge_alias_weight_keys,
    _normalize_weight_dict,
    _p0_diag_line,
    _p0_slim_asset_row,
    _phase0_from_universe_after_strikes,
    _phase0_from_universe_store,
    _remove_symbols_from_universe,
    _struck_resolved_symbols,
    _symbol_parent_category_keys,
    _symbols_in_category,
    _universe_extra_color,
)
from research.pipeline import run_pipeline, snapshot_to_jsonable
from research.schemas import DefensePolicyConfig, Phase0Input
from research.sentiment_proxy import get_sentiment_detail, get_sentiment_score

def _p2_global_best_model(p2: Dict[str, Any]) -> Tuple[str, Optional[float]]:
    """Return (model_key, mse) for the model with the lowest shadow MSE across all assets."""
    candidates: List[Tuple[str, float]] = []
    for key, fld in [("naive", "mse_naive"), ("arima", "mse_arima"),
                     ("lightgbm", "mse_lightgbm"), ("kronos", "mse_kronos")]:
        v = p2.get(fld)
        if v is not None and isinstance(v, (int, float)) and math.isfinite(float(v)):
            candidates.append((key, float(v)))
    if not candidates:
        return "", None
    return min(candidates, key=lambda x: x[1])


def _p2_best_model_hero(p2: Dict[str, Any], symbol: Optional[str]) -> Any:
    """Large-typography display: current ticker + shadow-validated best model (colour-matched)."""
    per = (p2.get("best_model_per_symbol") or {}).get(symbol) if symbol else None
    pk = str(per) if per else ""
    per_label = _P2_MODEL_LABEL.get(pk, pk or "—")
    col = _P2_MODEL_COLOR.get(pk, "#cfd8dc")
    return html.Div([
        html.Div(get_status_message("current_symbol_best_shadow", "当前标的 · 影子验证最优"), className="text-uppercase small text-muted mb-1"),
        html.Div(symbol or "—", className="fw-bold text-info mb-1",
                 style={"fontSize": "1.85rem", "letterSpacing": "0.04em", "lineHeight": "1.2"}),
        html.Div(per_label, className="fw-bold",
                 style={"fontSize": "2.25rem", "lineHeight": "1.15", "color": col,
                        "textShadow": "0 0 24px rgba(0,0,0,0.35)"}),
    ], className="ps-lg-2 pt-1")


def _p2_best_model_meta(p2: Dict[str, Any]) -> Any:
    """One-line strip below the hero: global MSE winner + consistency score."""
    cons = float(p2.get("credibility_score", p2.get("consistency_score")) or 0.0)
    g_key, g_mse = _p2_global_best_model(p2)
    g_label = _P2_MODEL_LABEL.get(g_key, g_key or "—")
    g_col = _P2_MODEL_COLOR.get(g_key, "#90a4ae")
    mse_line = f"MSE 均值最优 ≈ {g_mse * 1e4:.2f}×10⁻⁴" if g_mse is not None else "全样本影子 MSE 不可用"
    return html.Div([
        html.Span(get_status_message("best_model_fullsample", "全样本平均最准："), className="text-muted me-2"),
        html.Span(g_label, className="fw-bold me-2",
                  style={"color": g_col, "fontSize": "1.05rem"}),
        html.Span(mse_line, className="small text-muted"),
        html.Br(),
        html.Span(
            f"可信度得分 = {cons:.3f}（α·JSD 基准 + 覆盖惩罚；侧栏可调 α/β）",
            className="small text-muted",
        ),
    ], className="small")


def _p2_traffic_row(p2: Dict[str, Any], *, large: bool = False, badges_only: bool = False) -> Any:
    """Red / yellow / green for ARIMA, LightGBM, Kronos (probabilistic OOS vs Naive)."""
    tl = p2.get("model_traffic_light") or {}

    def _badge(key: str, label: str) -> Any:
        c = str(tl.get(key) or "").lower()
        color = {"green": "success", "yellow": "warning", "red": "danger"}.get(c, "secondary")
        bcls = "p2-traffic-badge-lg me-2" if large else "me-1"
        return dbc.Badge(label, color=color, className=bcls, pill=large)

    nll = p2.get("prob_nll_mean") or {}
    dm_p = p2.get("prob_dm_pvalue_vs_naive") or {}
    cov = p2.get("prob_coverage_95") or {}
    detail = []
    for key, lab in [("arima", "ARIMA"), ("lightgbm", "LGBM"), ("kronos", "Kronos")]:
        if key in nll or key in dm_p:
            detail.append(
                f"{lab}: NLL̄={float(nll.get(key, 0)):.3f}, DM p={float(dm_p.get(key, 1)):.3f}, "
                f"Cov₉₅={float(cov.get(key, 0)):.2f}"
            )
    cap = "三模型概率验证（样本外 NLL + DM(HAC) vs Naive + 区间覆盖率）"
    fail = (
        html.Span(get_status_message("pipeline_full_failure", " 全流程失效"), className="text-danger fw-bold ms-2")
        if p2.get("prob_full_pipeline_failure")
        else html.Span()
    )
    if badges_only:
        return html.Div(
            [
                html.Div(
                    [_badge("arima", "ARIMA"), _badge("lightgbm", "LGBM"), _badge("kronos", "Kronos"), fail],
                    className="d-flex flex-wrap align-items-center justify-content-center gap-1",
                ),
            ],
            className="mb-0 mt-1 text-center",
        )
    if large:
        return html.Div(
            [
                html.Div(cap, className="p2-traffic-section-title text-uppercase text-info mb-2"),
                html.Div(
                    [_badge("arima", "ARIMA"), _badge("lightgbm", "LGBM"), _badge("kronos", "Kronos"), fail],
                    className="d-flex flex-wrap align-items-center gap-1",
                ),
                html.P(" · ".join(detail), className="p2-traffic-detail text-muted mb-0 mt-2") if detail else html.Div(),
            ],
            className="p2-traffic-wrap-lg mb-0 mt-2 pt-2 border-top border-secondary border-opacity-25",
        )
    return html.Div(
        [
            html.Span(f"{cap}：", className="small text-muted me-2"),
            _badge("arima", "ARIMA"),
            _badge("lightgbm", "LGBM"),
            _badge("kronos", "Kronos"),
            html.Span(
                get_status_message("pipeline_full_failure", " 全流程失效") if p2.get("prob_full_pipeline_failure") else "",
                className="small text-danger fw-bold ms-2",
            ),
            html.Br(),
            html.Span(" · ".join(detail), className="small text-muted") if detail else html.Span(),
        ],
        className="mb-0",
    )


# P0 universe helpers (_struck_resolved_symbols, _phase0_from_universe_*,
# _coerce_sym_list, _universe_extra_color, _symbols_in_category,
# _symbol_parent_category_keys, _cat_header_dimmed, _remove_symbols_from_universe,
# _normalize_weight_dict, _merge_alias_weight_keys, _flatten_universe,
# _p0_diag_line, _p0_slim_asset_row, _build_p0_asset_tree) now live in
# dash_app/ui/p0_universe_helpers.py — re-exported via the import block above.


# 防御原因 badge 末尾固定模式 "→ ... Level N ..." 的截断正则。
# 同时覆盖中文 "→ 防御等级切换至 Level 1" 与英文 "→ defense level switches to Level 2"
# 等表达。仅截掉 *最后一个* 引出 LevelN 的箭头分句，避免误伤句中早出现的箭头
# （如 FigX.5/6 的 "→{date}为首次预警日" — 这一段不含 Level 数字，不会被吃掉）。
_DEFENSE_LEVEL_TAIL_RE = re.compile(r"\s*→[^→]*?Level\s*\d.*$", re.IGNORECASE)


def _truncate_defense_reason(body: str) -> str:
    """Strip the trailing '→ … Level N …' clause from a defense-reason badge.

    Per Feedback (R2.4)：badge 仅显示触发原因，不重复显示等级（等级已由顶部
    badge 颜色 / 文案承载）。
    """
    if not isinstance(body, str):
        return body
    truncated = _DEFENSE_LEVEL_TAIL_RE.sub("", body)
    return truncated.rstrip(" ，,;；。.")


def _defense_cond_div(body: str, *, danger: bool = False, warn: bool = False) -> html.Div:
    if danger:
        cls = "defense-reason-tag danger mb-2"
    elif warn:
        cls = "defense-reason-tag warn mb-2"
    else:
        cls = "defense-reason-tag success mb-2"
    return html.Div(html.Div(_truncate_defense_reason(body), className="reason-body"), className=cls)


def _div_from_fig_line(body_sev: Tuple[str, str]) -> html.Div:
    body, sev = body_sev
    return _defense_cond_div(body, danger=sev == "danger", warn=sev == "warn")


def _sb2_idle_reason_block(fig_lbl: str) -> html.Div:
    return html.Div(
        [
            _defense_cond_div(
                f"{fig_lbl}: 未执行管线→当前变量对防御等级切换无影响",
                danger=False,
                warn=False,
            ),
            html.P("—", className="small text-muted mb-0"),
        ],
    )



def _defense_status_badge(level: int) -> Tuple[str, str]:
    if level >= 2:
        return "Level 2（熔断）", "danger"
    if level == 1:
        return "Level 1（警戒）", "warning"
    return "Level 0（基准）", "success"


def _fmt_p3_val(x: Any, nd: int = 4) -> str:
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(xf):
        return "—"
    return f"{xf:.{nd}f}"


def _p0_defense_reason_tag_html(
    env: Dict[str, Any],
    defense_level: int,
    snap_json: Dict[str, Any],
    p1: Dict[str, Any],
    p2: Dict[str, Any],
    pol: Any,
) -> html.Div:
    """Phase 0：与 resolve_defense_level 对齐的聚合条件行（无标题）。"""
    o = env.get("orthogonality_check") or {}
    if bool(o.get("warning")) and "削弱" in str(o.get("message", "")):
        return _defense_cond_div(
            "P0: 训练期科技–避险相关性偏高→分散化对冲前提减弱（对照解读 Universe）",
            warn=True,
        )
    h_struct = float(p1.get("h_struct", 1.0) or 1.0)
    body, sev = p0_aggregate_condition_line(
        defense_level=int(defense_level),
        snap=snap_json,
        p1=p1,
        p2=p2,
        pol_tau_h1=float(getattr(pol, "tau_h1", 0.5) or 0.5),
        pol_tau_l2=float(getattr(pol, "tau_l2", 0.45) or 0.45),
        pol_tau_l1=float(getattr(pol, "tau_l1", 0.70) or 0.70),
        pol_tau_s_low=float(getattr(pol, "tau_s_low", -0.20) or -0.20),
        s_min=float(
            ((snap_json.get("phase0") or {}).get("meta") or {}).get("defense_sentiment_min_st", -0.1) or -0.1
        ),
    )
    return _defense_cond_div(body, danger=sev == "danger", warn=sev == "warn")


def _p3_semantic_prior_section(dv: Dict[str, Any], meta: Dict[str, Any]) -> dbc.Card:
    pol_tau_s = dv.get("research_tau_s_low")
    min_st = dv.get("research_defense_sentiment_min_st")
    win_lbl = dv.get("research_test_window_label") or "—"
    sem_day = dv.get("research_semantic_alarm_day_offset")
    prc_day = dv.get("research_price_instability_day_offset")
    lead = dv.get("research_semantic_lead_trading_days")
    early = dv.get("research_early_april_2026_window")
    scen_step = dv.get("research_scenario_inject_step")
    st_meta = meta.get("test_sentiment_st") if isinstance(meta, dict) else None
    lines = [
        "### 语义先验（测试窗，与 Phase 2 / 防御判定同源）",
        "",
        f"- **测试窗**：{win_lbl}",
        f"- **语义阈**：当分段累积 **S_t** 低于 **τ_S_low = {_fmt_p3_val(pol_tau_s, 3)}** 视为下行语义告警。"
        f" 防御聚合使用 **min(S_t) ≈ {_fmt_p3_val(min_st, 3)}**（全窗路径谷底，与跳跃参数映射一致）。",
        "",
        "#### 事件序：非结构化信号 vs 价格不稳",
        "",
    ]
    if sem_day is not None:
        lines.append(
            f"- **语义告警日**：测试窗内**首个** S_t < τ_S_low 的交易日序号 **{int(sem_day)}**（从 0 起计）。"
        )
    else:
        lines.append("- **语义告警日**：未触发，或 S_t 与交易日未对齐 / 缺失。")
    if prc_day is not None:
        lines.append(
            f"- **价格不稳日**：等权组合 **5 日滚动波动**首次高于**全窗 85% 分位**的日序号 **{int(prc_day)}**。"
        )
    else:
        lines.append("- **价格不稳日**：未触发或未计算。")
    if lead is not None:
        try:
            ld = int(lead)
            if ld > 0:
                lines.append(
                    f"- **语义提前量**：**{ld}** 个交易日（价格序号 − 语义序号；**正值**表示语义先验更早)。"
                )
            elif ld == 0:
                lines.append("- **语义提前量**：与价格波动信号同日或不可分先后。")
            else:
                lines.append(
                    f"- **语义提前量**：**{ld}** 日（负值表示价格波动类信号更早）。"
                )
        except (TypeError, ValueError):
            lines.append("- **语义提前量**：—")
    if early:
        lines.append("- **时间锚**：测试窗与 **2026 年 4 月上旬**相交，对齐「非稳态」叙事设定。")
    if scen_step is not None:
        lines.append(
            f"- **情景注入步**：蒙特卡洛在第 **{int(scen_step)}** 步注入确定性对数冲击（与压力轨一致）。"
        )
    if isinstance(st_meta, dict) and st_meta.get("dates"):
        lines.append("- **S_t 路径**：见上方「测试窗 S_t」图；本卡为管线写入的离散对照指标。")
    return dbc.Card(
        [
            dbc.CardHeader("语义先验与信息流", className="phase-card-header-title"),
            dbc.CardBody(dcc.Markdown("\n".join(lines), className="mb-0 phase-doc-body small")),
        ],
        className="shadow-sm border-secondary phase-text-panel mt-2",
    )


def _p3_failure_identification_card(dv: Dict[str, Any]) -> dbc.Card:
    """失效识别 vs 参照压力日：结构熵 / JSD 应力 / 可信度 / 语义–数值余弦的提前量。"""

    def _row_ix(x: Any) -> str:
        if x is None:
            return "—"
        try:
            return str(int(x))
        except (TypeError, ValueError):
            return "—"

    ref_lbl = str(dv.get("research_failure_ref_label") or "—")
    verdict = str(dv.get("research_failure_early_warning_verdict") or "—")
    ah = dv.get("research_alarm_day_rolling_h_struct")
    aj = dv.get("research_alarm_day_rolling_jsd_stress")
    ac = dv.get("research_alarm_day_credibility_l1")
    ao = dv.get("research_alarm_day_semantic_cosine_negative")
    lh = dv.get("research_lead_ref_vs_h_struct")
    lj = dv.get("research_lead_ref_vs_jsd_stress")
    lc = dv.get("research_lead_ref_vs_credibility")
    lo = dv.get("research_lead_ref_vs_semantic_cosine")
    lines = [
        "### 失效识别有效性（提前 1～5 交易日口径）",
        "",
        f"- **参照压力日**：{ref_lbl}",
        "",
        "#### 各信号在测试窗内的**首次**告警行（0 起，与 Phase2 测试行对齐）",
        "",
        f"- **滚动结构熵** < τ_h1：第 **{_row_ix(ah)}** 行",
        f"- **三角 JSD 动态应力**（滚动 W=semantic_cosine_window 日 > k_jsd×训练基线）：第 **{_row_ix(aj)}** 行",
        f"- **可信度代理** ≤ τ_L1：第 **{_row_ix(ac)}** 行",
        f"- **语义–数值滚动余弦** < 0：第 **{_row_ix(ao)}** 行",
        "",
        "#### 相对参照日的提前量（正 = 信号早于参照）",
        "",
        f"- 结构熵：**{_row_ix(lh)}** 行　JSD 应力：**{_row_ix(lj)}** 行　"
        f"可信度：**{_row_ix(lc)}** 行　余弦：**{_row_ix(lo)}** 行",
        "",
        "#### 结论（管线自动判定）",
        "",
        verdict,
    ]
    return dbc.Card(
        [
            dbc.CardHeader("失效识别与提前量", className="phase-card-header-title"),
            dbc.CardBody(dcc.Markdown("\n".join(lines), className="mb-0 phase-doc-body small")),
        ],
        className="shadow-sm border-info border-opacity-25 phase-text-panel mt-2",
    )


def _p4_experiments_stack_block(snap_json: Dict[str, Any], tpl: str, ui_mode: Optional[str] = None) -> Any:
    """P4 主栏：防御机制有效性（原 Figure3.5 三块权益 + 终端/MC 文本 + 语义先验 + 失效提前量）。"""
    p3 = snap_json.get("phase3") or {}
    if not isinstance(p3, dict):
        p3 = {}
    p0_meta = (snap_json.get("phase0") or {}).get("meta") or {}
    dv_raw = p3.get("defense_validation")
    dv = dv_raw if isinstance(dv_raw, dict) else {}

    dates = snap_json.get("shadow_index_labels") or []
    y_ms = dv.get("test_equity_max_sharpe")
    y_cu = dv.get("test_equity_custom_weights")
    y_cv = dv.get("test_equity_cvar")
    fig_triple = fig_p3_triple_test_equity(
        dates, y_ms, y_cu, y_cv, tpl, figure_title=None
    )

    fig42_md = build_fig42_body(ui_mode, snap_json, dv)

    sem_card = _p3_semantic_prior_section(dv, p0_meta if isinstance(p0_meta, dict) else {})
    fail_card = _p3_failure_identification_card(dv)
    fig42_cap = get_figure_title(
        "fig_4_2",
        "Figure 4.2 · 防御策略有效性检验（三权重测试窗对照）",
    )
    return html.Div(
        [
            _figure_wrap(
                5,
                [
                    dcc.Graph(figure=fig_triple, config={"displayModeBar": True, "scrollZoom": False}),
                    dcc.Markdown(fig42_md, className="phase-doc-body small mb-2"),
                ],
                fig_label=fig42_cap,
            ),
            sem_card,
            fail_card,
        ],
        className="p4-experiments-stack",
    )


def _objective_alert(defense_level: int, objective_name: str, api_err: str | None) -> Any:
    if objective_name == "min_cvar" or defense_level >= 2:
        color = "danger"
        msg = html.Div(
            [
                html.Strong(get_status_message("objective_switched", "目标函数已切换：")),
                " 系统由 Max Sharpe 标准优化切换为 ",
                html.Code("Min CVaR"),
                "，以在模型分歧与尾部跳跃压力下压缩左尾损失。",
            ]
        )
    elif objective_name == "caution_semantic" or defense_level == 1:
        color = "warning"
        msg = html.Div(
            [
                html.Strong(get_status_message("objective_adjusted", "目标函数已调整：")),
                " 当前为语义约束下的谨慎目标（非纯夏普最大化），在情绪压力与 KL 信号下惩罚下行语义暴露。",
            ]
        )
    else:
        color = "info"
        msg = html.Div(
            [
                html.Strong(get_status_message("objective_label", "目标函数：")),
                " Level 0 下保持 ",
                html.Code("Max Sharpe"),
                " 基准；若统计与模型层触发熔断，将自动升格并切换优化目标。",
            ]
        )
    if api_err:
        msg = html.Div([msg, html.Hr(), html.Small(f"API 回退提示: {api_err}", className="text-warning")])
    return dbc.Alert(msg, color=color, className="py-2 mb-2 phase-text-panel phase-doc-body")


def _api_base() -> str | None:
    """Return API base URL, or None to use in-process pipeline (avoids same-port deadlock)."""
    raw = (os.environ.get("AIE1902_API_BASE") or "").strip()
    if not raw or raw.lower() in ("local", "skip", "none", "-"):
        return None
    raw = raw.rstrip("/")
    try:
        from urllib.parse import urlparse

        u = urlparse(raw)
        if u.scheme in ("http", "https") and u.hostname in ("127.0.0.1", "localhost", "::1"):
            app_port = int(os.environ.get("PORT") or "8000")
            url_port = u.port if u.port is not None else (443 if u.scheme == "https" else 80)
            if url_port == app_port:
                return None
    except (ValueError, TypeError):
        pass
    return raw


def _snapshot_json_ok(snap: Any) -> bool:
    """True if API/local JSON has the phase dicts the Dash UI expects."""
    if not isinstance(snap, dict):
        return False
    for k in ("phase0", "phase1", "phase2", "phase3"):
        if not isinstance(snap.get(k), dict):
            return False
    return True


def _safe_analyze_via_api(
    policy: DefensePolicyConfig,
    sentiment: float,
    phase0: Dict[str, Any] | None = None,
    sentiment_detail: Dict[str, Any] | None = None,
    custom_portfolio_weights: Dict[str, float] | None = None,
) -> Tuple[Dict[str, Any] | None, str | None]:
    base = _api_base()
    if base is None:
        return None, None
    try:
        import requests

        body: Dict[str, Any] = {
            "sentiment": float(sentiment),
            "policy": policy.model_dump(),
            "data_path": _default_data_json_path(),
        }
        if phase0:
            body["phase0"] = phase0
        if sentiment_detail:
            body["sentiment_detail"] = sentiment_detail
        if custom_portfolio_weights:
            body["custom_portfolio_weights"] = custom_portfolio_weights
        r = requests.post(f"{base}/api/analyze", json=body, timeout=120)
        if r.status_code >= 400:
            return None, f"API {r.status_code}: {r.text[:300]}"
        data = r.json()
        if not _snapshot_json_ok(data):
            return None, "API returned JSON without phase0–phase3 dicts"
        return data, None
    except Exception as e:
        return None, repr(e)


def _execute_pipeline_for_dashboard(
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
    sentiment,
    scenario_step,
    scenario_impact,
    oos_steps=None,
    shadow_alpha_mse=None,
    shadow_holdout_days=None,
    asset_universe=None,
    strike_store=None,
    sentiment_detail=None,
    semantic_cos_window=None,
    verify_train_tail_days=None,
    verify_crash_q=None,
    verify_std_q=None,
    verify_tail_q=None,
) -> Tuple[DefensePolicyConfig, Dict[str, Any], List[str], Optional[str], float]:
    """Dashboard 侧管线执行 — **薄代理**。

    真正的逻辑已拆到 :mod:`dash_app.pipeline_exec` 模块（`policy_builder` +
    `sentiment_resolver` + `executor`）。本函数保留原签名与返回值，仅作为
    兼容层，便于老 callback 无改动调用。

    要调试某一步骤，请设置环境变量 ``DEBUG_PIPELINE_EXEC=1`` 后重跑；
    或直接调用新模块的公共 API（见 :func:`dash_app.pipeline_exec.execute_pipeline_for_dashboard`）。
    """
    _ = (scenario_step, scenario_impact)  # reserved for future scenario wiring

    from dash_app.pipeline_exec import (
        SliderInputs,
        execute_pipeline_for_dashboard as _exec,
    )

    inputs = SliderInputs(
        tau_l2=tau_l2,
        tau_l1=tau_l1,
        tau_h1=tau_h1,
        tau_vol=tau_vol,
        tau_ac1=tau_ac1,
        k_jsd=k_jsd,
        jsd_baseline_eps_log=jsd_baseline_eps_log,
        cred_jsd_base=cred_jsd_base,
        cred_jsd_pen=cred_jsd_pen,
        cred_pen_cap=cred_pen_cap,
        cred_min=cred_min,
        cred_max=cred_max,
        lam=lam,
        semantic_cos_window=semantic_cos_window,
        oos_steps=oos_steps,
        shadow_alpha_mse=shadow_alpha_mse,
        shadow_holdout_days=shadow_holdout_days,
        verify_train_tail_days=verify_train_tail_days,
        verify_crash_q=verify_crash_q,
        verify_std_q=verify_std_q,
        verify_tail_q=verify_tail_q,
    )
    result = _exec(
        inputs,
        sentiment_raw=sentiment,
        asset_universe=asset_universe,
        strike_store=strike_store,
        sentiment_detail_raw=sentiment_detail,
    )
    return result.to_tuple()

