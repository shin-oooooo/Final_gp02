"""Main panel layout for Phase 2 (model selection, density, shadow validation)."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from dash_app.render.explain import (
    P2_FIG21_INTRO_MD,
    P2_PIXEL_SHADOW_INTRO_MD,
)
from dash_app.ui.layout import (
    _analysis_card,
    _fig_explain_title,
    _figure_wrap,
    _placeholder_fig,
)
from dash_app.services.copy import get_app_label, get_status_message

_P2_MODEL_LABEL = {"naive": "Naive", "arima": "ARIMA", "lightgbm": "LightGBM", "kronos": "Kronos"}
_P2_MODEL_COLOR = {"naive": "#aaaaaa", "arima": "#00e676", "lightgbm": "#c39bff", "kronos": "#ff7f0e"}


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
    """Centered ticker + shadow-validated best model displayed inline in small coloured text."""
    per = (p2.get("best_model_per_symbol") or {}).get(symbol) if symbol else None
    pk = str(per) if per else ""
    per_label = _P2_MODEL_LABEL.get(pk, pk or "—")
    col = _P2_MODEL_COLOR.get(pk, "#cfd8dc")
    return html.Div(
        [
            html.Div(
                [
                    html.Span(
                        symbol or "—",
                        className="fw-bold text-info",
                        style={"fontSize": "2.4rem", "letterSpacing": "0.05em", "lineHeight": "1.2"},
                    ),
                    html.Span(
                        f"  {per_label}",
                        className="fw-bold ms-3",
                        style={"fontSize": "1.1rem", "color": col, "verticalAlign": "middle"},
                    ),
                ],
                className="d-flex align-items-baseline justify-content-center",
            ),
        ],
        className="text-center pt-1",
    )


def _p2_best_model_meta(p2: Dict[str, Any]) -> Any:
    """One-line strip below the hero: global MSE winner + consistency score."""
    cons = float(p2.get("credibility_score", p2.get("consistency_score")) or 0.0)
    g_key, g_mse = _p2_global_best_model(p2)
    g_label = _P2_MODEL_LABEL.get(g_key, g_key or "—")
    g_col = _P2_MODEL_COLOR.get(g_key, "#90a4ae")
    if g_mse is not None:
        mse_line = get_app_label(
            "p2_mse_best_prefix",
            "MSE 均值最优 ≈ {mse}×10⁻⁴",
        ).format(mse=f"{g_mse * 1e4:.2f}")
    else:
        mse_line = get_app_label("p2_shadow_mse_unavailable", "全样本影子 MSE 不可用")
    cred_hint = get_app_label(
        "p2_credibility_hint",
        "可信度得分 = {score}（α·JSD 基准 + 覆盖惩罚；侧栏可调 α/β）",
    ).format(score=f"{cons:.3f}")
    return html.Div([
        html.Span(get_status_message("best_model_fullsample", "全样本平均最准："), className="text-muted me-2"),
        html.Span(g_label, className="fw-bold me-2",
                  style={"color": g_col, "fontSize": "1.05rem"}),
        html.Span(mse_line, className="small text-muted"),
        html.Br(),
        html.Span(cred_hint, className="small text-muted"),
    ], className="small")


def _p2_mu_sigma_table(
    model_mu: Dict[str, Any],
    model_sigma: Dict[str, Any],
    symbol: Optional[str],
    model_mu_test_ts: Optional[Dict[str, Any]] = None,
    model_sigma_test_ts: Optional[Dict[str, Any]] = None,
) -> Any:
    """Small table showing μ̂ and σ̂ for the four models at the selected symbol."""
    if not symbol:
        return html.P(get_status_message("select_symbol_prompt", "请选择标的以查看 μ、σ。"), className="small text-muted mb-0")
    rows = []
    for m in ["naive", "arima", "lightgbm", "kronos"]:
        mu = sg = None
        if model_mu_test_ts and model_sigma_test_ts:
            ts_m = (model_mu_test_ts.get(m) or {}).get(symbol) or []
            ts_s = (model_sigma_test_ts.get(m) or {}).get(symbol) or []
            if ts_m and ts_s:
                mu, sg = ts_m[-1], ts_s[-1]
        if mu is None:
            mu = model_mu.get(m, {}).get(symbol)
            sg = model_sigma.get(m, {}).get(symbol)
        def _fmt(v: Any) -> str:
            try:
                return f"{float(v):.6f}" if v is not None and math.isfinite(float(v)) else "—"
            except Exception:
                return "—"
        rows.append(html.Tr([
            html.Td(_P2_MODEL_LABEL.get(m, m)),
            html.Td(_fmt(mu), className="font-monospace"),
            html.Td(_fmt(sg), className="font-monospace"),
        ]))
    return dbc.Table([
        html.Thead(html.Tr([
            html.Th(get_app_label("p2_table_header_model", "模型")),
            html.Th(get_app_label("p2_table_header_mu", "μ̂（OOS末日）")),
            html.Th(get_app_label("p2_table_header_sigma", "σ̂")),
        ])),
        html.Tbody(rows),
    ], bordered=True, hover=True, size="sm", className="mb-0 small")


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
    cap = get_app_label(
        "p2_prob_caption",
        "三模型概率验证（样本外 NLL + DM(HAC) vs Naive + 区间覆盖率）",
    )
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
                    className="d-flex flex-wrap align-items-center gap-1",
                ),
            ],
            className="mb-0 mt-1",
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


def _p2_jsd_failure_merge_panel(
    p2: Dict[str, Any],
    jsd_thr: float,
    jsd_pairs_mean: float,
    p2_val: Optional[str],
    cred_lo: float,
    cred_hi: float,
) -> Any:
    """右侧资料：可信度分解、三边 JSD、概率检验表（与快照一致）。"""
    lb_ac1 = bool(p2.get("logic_break_from_ac1", False))
    lb_sem = bool(p2.get("logic_break_semantic_cosine_negative", False))
    sem_ok = bool(p2.get("semantic_numeric_cosine_computed", False))
    cos_sn = float(p2.get("cosine_semantic_numeric") or 0.0)
    ac1v = float(p2.get("train_return_ac1") or 0.0)
    logic_lines: List[str] = []
    if lb_ac1:
        logic_lines.append(
            get_app_label(
                "p2_logic_ac1_line",
                "- 训练期市场收益 AC1={ac1} 低于 τ_AC1（逻辑断裂）。",
            ).format(ac1=f"{ac1v:.4f}")
        )
    if sem_ok:
        _cos_prefix = get_app_label(
            "p2_logic_cos_line_prefix",
            "- 测试窗 S_t 与数值预测 μ（截面均值）滚动余弦相似度 {cos}",
        ).format(cos=f"{cos_sn:.4f}")
        _suffix = (
            get_app_label("p2_logic_cos_break_suffix", "；语义与数值趋势背离（逻辑断裂）")
            if lb_sem
            else "。"
        )
        logic_lines.append(f"{_cos_prefix}{_suffix}")
    if logic_lines:
        _hdr = get_app_label("p2_logic_break_header_prefix", "逻辑断裂提示")
        logic_block = f"\n\n**{_hdr}**\n\n" + "\n".join(logic_lines)
    else:
        logic_block = ""

    base = float(p2.get("credibility_base_jsd") or 0.0)
    pen = float(p2.get("credibility_coverage_penalty") or 0.0)
    cred = float(p2.get("credibility_score", p2.get("consistency_score")) or 0.0)
    g_tri = float(p2.get("jsd_triangle_mean", 0.0))
    g_ka = float(p2.get("jsd_kronos_arima_mean", 0.0))
    g_kg = float(p2.get("jsd_kronos_gbm_mean", 0.0))
    g_ga = float(p2.get("jsd_gbm_arima_mean", 0.0))

    jmap = p2.get("jsd_by_symbol") or {}
    jsd_row: Optional[Dict[str, Any]] = None
    if p2_val and isinstance(jmap, dict) and p2_val in jmap and isinstance(jmap[p2_val], dict):
        jsd_row = jmap[p2_val]
    if jsd_row:
        jka = float(jsd_row.get("kronos_arima", g_ka))
        jkg = float(jsd_row.get("kronos_gbm", g_kg))
        jga = float(jsd_row.get("gbm_arima", g_ga))
        jsd_tri_disp = float(jsd_row.get("triangle", g_tri))
        jsd_note = get_app_label(
            "p2_caption_jsd_current",
            "*三边与 **JSD_三角均值（当前标的）** 为 **{sym}** 在测试窗上的日度平均；全市场聚合三角均值＝{g_tri}。*",
        ).format(sym=p2_val, g_tri=f"{g_tri:.4f}")
    else:
        jka, jkg, jga, jsd_tri_disp = g_ka, g_kg, g_ga, g_tri
        jsd_note = (
            get_app_label(
                "p2_caption_missing_sym",
                "*三边与三角均值为全市场聚合（当前标的无分项缓存时请重新跑批以写入 `jsd_by_symbol`）。*",
            )
            if p2_val
            else get_app_label("p2_caption_global", "*三边与三角均值为全市场聚合。*")
        )

    nll = p2.get("prob_nll_mean") or {}
    dm_p = p2.get("prob_dm_pvalue_vs_naive") or {}
    cov = p2.get("prob_coverage_95") or {}
    cov_naive = p2.get("prob_coverage_naive")

    def _nf(key: str, default: float = 0.0) -> float:
        try:
            v = nll.get(key)
            return float(v) if v is not None else default
        except (TypeError, ValueError):
            return default

    def _df(key: str, default: float = float("nan")) -> float:
        try:
            v = dm_p.get(key)
            if v is None:
                return default
            return float(v)
        except (TypeError, ValueError):
            return default

    def _cf(key: str, default: float = float("nan")) -> float:
        try:
            v = cov.get(key)
            if v is None:
                return default
            return float(v)
        except (TypeError, ValueError):
            return default

    def _dm_cell(key: str) -> str:
        if key == "naive":
            return "—"
        x = _df(key)
        return f"{x:.3f}" if math.isfinite(x) else "—"

    def _nll_cell(key: str) -> str:
        if key not in nll or nll.get(key) is None:
            return "—"
        return f"{_nf(key):.3f}"

    def _cov_cell(key: str) -> str:
        if key == "naive" and cov_naive is not None:
            try:
                return f"{float(cov_naive):.2f}"
            except (TypeError, ValueError):
                pass
        x = _cf(key)
        return f"{x:.2f}" if math.isfinite(x) else "—"

    table_md = f"""
| 模型 | NLL̄ | DM p（vs Naive） | Cov₉₅ |
|:---|---:|---:|---:|
| Naive | {_nll_cell("naive")} | {_dm_cell("naive")} | {_cov_cell("naive")} |
| ARIMA | {_nll_cell("arima")} | {_dm_cell("arima")} | {_cov_cell("arima")} |
| LGBM | {_nll_cell("lightgbm")} | {_dm_cell("lightgbm")} | {_cov_cell("lightgbm")} |
| Kronos | {_nll_cell("kronos")} | {_dm_cell("kronos")} | {_cov_cell("kronos")} |
""".strip()

    body_md = f"""
与 **Figure2.3–Figure2.5** 所用标的（下拉选择）一致：**{p2_val or "—"}**

**可信度**（侧栏「可信度输出下界～上界」内截断：**{cred_lo:.2f} ～ {cred_hi:.2f}**）

- **基准项**＝{base:.4f}
- **惩罚项**＝{pen:.4f}
- **可信度**＝**{cred:.4f}**（基准项 − 惩罚项，再经上下界截断）

*可信度与下表 NLL／DM／Cov 为测试窗内**全组合池化**，与下拉所选标的无关，并与左侧仪表盘一致。*

**三边 JSD（测试期）**

- JSD(Kronos, ARIMA)＝{jka:.4f}
- JSD(Kronos, LGBM)＝{jkg:.4f}
- JSD(LGBM, ARIMA)＝{jga:.4f}

**JSD_三角均值（当前标的）**＝{jsd_tri_disp:.4f}

（动态阈值 {jsd_thr:.4f}；全样本对均值 {jsd_pairs_mean:.4f}；全市场聚合三角均值 {g_tri:.4f}）

{jsd_note}
{logic_block}

### 三模型概率预测失效验证

{table_md}
""".strip()

    return dbc.Card(
        dbc.CardBody(
            dcc.Markdown(
                body_md,
                mathjax=True,
                className="mb-0 phase-doc-body p2-jsd-data-md",
                style={"lineHeight": "1.75"},
            )
        ),
        className="shadow-sm border-warning border-opacity-25 h-100 p2-jsd-cred-card",
    )


def main_p2_panel() -> html.Div:
    """Return the full main-panel-p2 layout.

    已删除的 8 个前端不可见的占位（历史回调 Output 残留）：
    ``p2-semantic-numeric-block / p2-defense-reason / fig-p2-consistency /
    p2-jsd-failure-merge / fig-p2-forecast / p2-line-note / card-p2 /
    p2-best-model-meta``
    """
    return html.Div(
        id="main-panel-p2",
        className="main-tab-panel",
        style={"display": "none"},
        children=[
            _figure_wrap(
                0,
                [
                    dcc.Graph(
                        id="fig-p2-best-pixels",
                        figure=_placeholder_fig(),
                        config={"displayModeBar": False},
                        style={"height": "300px"},
                        className="mb-2",
                    ),
                    # Mode-aware container: updated by `_mode_main_panel_refresh` callback
                    html.Div(
                        id="p2-fig21-explain-card",
                        children=_analysis_card(
                            _fig_explain_title(2, 1, get_app_label(
                                "p2_fig21_caption",
                                "影子择模与像素矩阵（MSE / 影子验证 / 综合分）",
                            )),
                            P2_PIXEL_SHADOW_INTRO_MD,
                        ),
                    ),
                ],
                fig_label="Figure2.1",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Label(
                                get_app_label("p2_symbol_search_label", "标的（可搜索）"),
                                className="small text-muted mb-1",
                            ),
                            dcc.Dropdown(
                                id="p2-symbol",
                                clearable=False,
                                searchable=True,
                                placeholder=get_app_label("p2_symbol_search_placeholder", "搜索代码…"),
                                className="text-start",
                            ),
                        ],
                        xs=12,
                        md=6,
                        className="text-start",
                    ),
                ],
                className="mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            id="p2-best-model",
                            className="text-center mt-1",
                            children=html.Span("—", className="display-6 fw-bold text-info"),
                        ),
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            _figure_wrap(
                1,
                [
                    html.Div(
                        get_app_label(
                            "p2_density_hint",
                            "提示：高/低密度区对比已加强；单击图例可隐藏该模型密度与 μ 脊线。",
                        ),
                        className="small text-muted mb-2",
                    ),
                    dcc.Graph(
                        id="fig-p2-density",
                        figure=_placeholder_fig(),
                        config={"displayModeBar": False},
                        style={"height": "460px"},
                    ),
                    # Mode-aware container: updated by `_mode_main_panel_refresh` callback
                    html.Div(
                        id="p2-fig22-explain-card",
                        children=_analysis_card(
                            _fig_explain_title(2, 2, get_app_label(
                                "p2_fig22_caption",
                                "时间×收益密度（纵轴 · μ 脊线 · 着色）",
                            )),
                            P2_FIG21_INTRO_MD,
                        ),
                    ),
                ],
                fig_label="Figure2.2",
            ),
        ],
    )
