from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import dash_bootstrap_components as dbc
from dash import dcc, html
import math

from dash_app.services.copy import (
    get_app_label,
    get_param_explanation,
    get_sidebar_left_label,
    get_sidebar_left_title,
    get_status_message,
)


# 色面 class 名（与上方 Alert / defense-traffic 同色系，由 custom.css 提供背景）
_FILL_CLS = {
    "red":    "defense-rgy-fill-danger",
    "yellow": "defense-rgy-fill-warn",
    "green":  "defense-rgy-fill-success",
}


def _unpack_tau_l2_l1(raw: Any) -> Tuple[float, float]:
    """Parse RangeSlider value [τ_L2, τ_L1] on 0.2–0.95 with τ_L2 < τ_L1."""
    a, b = 0.45, 0.7
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        try:
            a = float(raw[0])
            b = float(raw[1])
        except (TypeError, ValueError):
            return a, b
    if a >= b:
        a = min(a, b - 0.02)
    a = max(0.2, min(0.93, a))
    b = max(0.21, min(0.95, b))
    if b <= a:
        b = min(0.95, a + 0.02)
    return a, b


def _defense_rgy_rail(tau_l2: float, tau_l1: float) -> html.Div:
    """可信度得分轴（0～1）红黄绿分区 + τ_L2 / τ_L1 竖线；分区上标 L2 | L1 | L0（无长文案）。"""
    a = max(0.0, min(1.0, float(tau_l2)))
    b = max(0.0, min(1.0, float(tau_l1)))
    if a >= b:
        a = max(0.05, b - 0.08)
    r_w = max(a, 1e-6)
    y_w = max(b - a, 1e-6)
    g_w = max(1.0 - b, 1e-6)
    h_bar = 30
    seg_style = {"minWidth": 0}
    track = html.Div(
        [
            html.Div(
                [html.Span(get_sidebar_left_label("tau_rgy_l2", "L2"), className="defense-zone-mid")],
                className=f"defense-rgy-seg {_FILL_CLS['red']}",
                style={**seg_style, "flex": f"{r_w} 1 0"},
            ),
            html.Div(
                [html.Span(get_sidebar_left_label("tau_rgy_l1", "L1"), className="defense-zone-mid")],
                className=f"defense-rgy-seg {_FILL_CLS['yellow']}",
                style={**seg_style, "flex": f"{y_w} 1 0"},
            ),
            html.Div(
                [html.Span(get_sidebar_left_label("tau_rgy_l0", "L0"), className="defense-zone-mid")],
                className=f"defense-rgy-seg {_FILL_CLS['green']}",
                style={**seg_style, "flex": f"{g_w} 1 0"},
            ),
        ],
        className="defense-rgy-track defense-neon-track defense-rgy-track--labeled",
        style={"minHeight": h_bar, "display": "flex", "width": "100%"},
    )
    def _tau_drag_hit(edge: str, frac: float) -> html.Div:
        """可拖动的分界热区（宽命中区 + 内层白竖线）。"""
        pct = max(0.0, min(1.0, float(frac))) * 100.0
        return html.Div(
            [
                html.Div(
                    className="defense-rgy-vline defense-neon-vline defense-tau-drag-line-inner",
                ),
            ],
            className=f"defense-tau-drag defense-tau-drag-{edge}",
            style={
                "position": "absolute",
                "left": f"{pct:.2f}%",
                "top": 0,
                "bottom": 0,
                "width": "28px",
                "marginLeft": "0",
                "transform": "translateX(-50%)",
                "cursor": "ew-resize",
                "zIndex": 4,
                "touchAction": "none",
                "pointerEvents": "auto",
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "stretch",
            },
            **{"data-tau-edge": edge},
        )

    overlay = html.Div(
        [
            _tau_drag_hit("l2", a),
            _tau_drag_hit("l1", b),
        ],
        className="defense-rgy-overlay defense-rgy-overlay--tau-drag",
        style={
            "position": "absolute",
            "left": 0,
            "right": 0,
            "top": 0,
            "height": h_bar,
            "minHeight": h_bar,
            # 需要允许子元素接收 pointer 事件；否则白线命中区无法拖拽
            "pointerEvents": "auto",
            "zIndex": 4,
        },
    )
    anno_layer = html.Div(
        [
            html.Span("0", className="defense-tau-axis-0 mono"),
            html.Span("1", className="defense-tau-axis-1 mono"),
            html.Div(
                [
                    html.Div(f"{a:.2f}", className="defense-tau-anno-num mono"),
                    html.Div("τ_L2", className="defense-tau-anno-var"),
                ],
                className="defense-tau-anno defense-tau-anno--l2",
                style={"left": f"{a * 100:.2f}%"},
            ),
            html.Div(
                [
                    html.Div(f"{b:.2f}", className="defense-tau-anno-num mono"),
                    html.Div("τ_L1", className="defense-tau-anno-var"),
                ],
                className="defense-tau-anno defense-tau-anno--l1",
                style={"left": f"{b * 100:.2f}%"},
            ),
        ],
        className="defense-tau-anno-layer",
    )
    wrap = html.Div(
        [track, overlay, anno_layer],
        className="defense-rgy-wrap",
        style={"position": "relative", "marginBottom": "0.35rem"},
    )
    return html.Div(
        [wrap],
        className="defense-rgy-rail defense-neon-rail defense-tau-rail-root",
        **{"data-l2": f"{a:.4f}", "data-l1": f"{b:.4f}"},
    )


def _defense_tau_norm(tau: float, vmin: float, vmax: float) -> float:
    span = float(vmax) - float(vmin)
    if span <= 1e-12:
        return 0.5
    return max(0.0, min(1.0, (float(tau) - float(vmin)) / span))


def _defense_two_zone_rail_draggable(
    *,
    rail_id: str,
    slider_id: str,
    input_id: str,
    tau: float,
    vmin: float,
    vmax: float,
    left_color: str,
    right_color: str,
    tau_symbol: str,
    left_lbl: str,
    right_lbl: str,
) -> html.Div:
    """两段颜色条 + 可拖动阈值线（白线）。拖动通过 assets/defense_single_rail_drag.js 同步 slider.value。"""
    p = _defense_tau_norm(tau, vmin, vmax)
    lw = max(p, 1e-6)
    rw = max(1.0 - p, 1e-6)
    lc = _FILL_CLS.get(left_color, "defense-rgy-fill-success")
    rc = _FILL_CLS.get(right_color, "defense-rgy-fill-success")
    h_bar = 22
    track = html.Div(
        [
            html.Div(
                [html.Span(left_lbl, className="defense-zone-mid")],
                className=f"defense-rgy-seg {lc}",
                style={"minWidth": 0, "flex": f"{lw} 1 0"},
            ),
            html.Div(
                [html.Span(right_lbl, className="defense-zone-mid")],
                className=f"defense-rgy-seg {rc}",
                style={"minWidth": 0, "flex": f"{rw} 1 0"},
            ),
        ],
        className="defense-rgy-track defense-neon-track defense-rgy-track--labeled",
        style={"minHeight": h_bar, "display": "flex", "width": "100%"},
    )

    drag = html.Div(
        [html.Div(className="defense-rgy-vline defense-neon-vline defense-single-drag-line-inner")],
        className="defense-single-drag",
        style={
            "position": "absolute",
            "left": f"{p * 100:.2f}%",
            "top": 0,
            "bottom": 0,
            "width": "28px",
            "marginLeft": "0",
            "transform": "translateX(-50%)",
            "cursor": "ew-resize",
            "zIndex": 4,
            "touchAction": "none",
            "pointerEvents": "auto",
            "display": "flex",
            "justifyContent": "center",
            "alignItems": "stretch",
        },
        **{
            "data-target": slider_id,
            "data-input": input_id,
            "data-min": str(vmin),
            "data-max": str(vmax),
        },
    )
    overlay = html.Div(
        [drag],
        className="defense-rgy-overlay defense-rgy-overlay--single-drag",
        style={
            "position": "absolute",
            "left": 0,
            "right": 0,
            "top": 0,
            "height": h_bar,
            "minHeight": h_bar,
            "pointerEvents": "none",
            "zIndex": 4,
        },
    )
    axis_nums = html.Div(
        [
            html.Span(f"{float(vmin):.2f}", className="defense-axis-num mono defense-axis-num--min"),
            html.Span(f"{float(tau):.2f}", className="defense-axis-num mono defense-axis-num--cur"),
            html.Span(f"{float(vmax):.2f}", className="defense-axis-num mono defense-axis-num--max"),
        ],
        className="defense-axis-row",
    )
    axis_var = html.Div([html.Span(tau_symbol, className="defense-axis-var mono")], className="defense-var-row")
    wrap = html.Div(
        [track, overlay, axis_nums, axis_var],
        className="defense-rgy-wrap defense-single-rail-root",
        id=rail_id,
        style={"position": "relative", "marginBottom": "0.35rem"},
        **{"data-v": f"{float(tau):.4f}"},
    )
    return html.Div([wrap], className="defense-rgy-rail defense-neon-rail")


# ---------------------------------------------------------------------------
# Single-arg rail helpers (extracted 2026-04-21 to remove the 11-kwarg
# duplication across sidebar_left init + defense_rails callbacks; underlying
# ``_defense_two_zone_rail_draggable`` signature is intentionally unchanged).
# ---------------------------------------------------------------------------

def _make_tau_h1_rail(tau: float) -> html.Div:
    """τ_H1 (结构熵) rail — values clamped to [0.2, 0.8]."""
    return _defense_two_zone_rail_draggable(
        rail_id="rail-h1-inner", slider_id="sl-tau-h1", input_id="inp-tau-h1",
        tau=tau, vmin=0.2, vmax=0.8,
        left_color="yellow", right_color="green", tau_symbol="τ_H1",
        left_lbl=get_sidebar_left_label("tau_h1_left_lbl", "L1"),
        right_lbl=get_sidebar_left_label("tau_h1_right_lbl", "L0"),
    )


def _make_tau_vol_rail(tau: float) -> html.Div:
    """τ_vol (年化波动) rail — values clamped to [0.10, 0.70]."""
    return _defense_two_zone_rail_draggable(
        rail_id="rail-vol-inner", slider_id="sl-tau-vol", input_id="inp-tau-vol",
        tau=tau, vmin=0.10, vmax=0.70,
        left_color="green", right_color="yellow", tau_symbol="τ_vol",
        left_lbl=get_sidebar_left_label("tau_vol_left_lbl", "L0"),
        right_lbl=get_sidebar_left_label("tau_vol_right_lbl", "L1"),
    )


def _make_tau_ac1_rail(tau: float) -> html.Div:
    """τ_AC1 (一阶自相关) rail — values clamped to [-0.40, 0.15]."""
    return _defense_two_zone_rail_draggable(
        rail_id="rail-ac1-inner", slider_id="sl-tau-ac1", input_id="inp-tau-ac1",
        tau=tau, vmin=-0.40, vmax=0.15,
        left_color="yellow", right_color="green", tau_symbol="τ_AC1",
        left_lbl=get_sidebar_left_label("tau_ac1_left_lbl", "L1"),
        right_lbl=get_sidebar_left_label("tau_ac1_right_lbl", "L0"),
    )


def _defense_zone_lbl_style(center_pct: float) -> dict:
    return {
        "position": "absolute",
        "left": f"{max(0.0, min(100.0, center_pct)):.2f}%",
        "top": "50%",
        "transform": "translate(-50%, -50%)",
        "textAlign": "center",
    }


def _sidebar_block_head(text: str, *, first: bool = False) -> html.H6:
    cls = "sidebar-block-head mb-2 " + ("mt-0" if first else "mt-3")
    return html.H6(text, className=cls)


def _help_card_body(title: str, explanation_key: Optional[str]) -> html.Div:
    """统一构造问号卡片体：title + explanation（无说明时回退占位符）。"""
    body_text = ""
    if explanation_key:
        body_text = get_param_explanation(explanation_key, "")
    if not body_text:
        body_text = get_status_message("desc_placeholder", "（说明待补充）")
    return html.Div(
        [
            html.Div(title, className="param-help-card-title"),
            html.Div(body_text, className="param-help-card-body text-muted small mb-0"),
        ],
        className="param-help-card",
    )


def _sidebar_help_title_line(
    title: str,
    explanation_key: Optional[str] = None,
) -> html.Div:
    """小标题级（单参数）问号行：标签 + 问号触发 + 说明卡片。

    ``explanation_key`` 命中 ``sidebar_left_params_explanations.md`` 则弹出
    详细说明；未传或未命中则显示占位符（保持旧行为向后兼容）。
    """
    return html.Div(
        [
            dbc.Label(title, className="sidebar-param-title mb-0 flex-grow-1"),
            html.Span(
                "?",
                className="param-help-trigger",
                role="button",
                tabIndex=0,
            ),
            _help_card_body(title, explanation_key),
        ],
        className="param-help-wrap d-flex flex-wrap align-items-center gap-2 w-100 mb-1",
    )


def _sidebar_block_head_with_help(
    title: str,
    explanation_key: Optional[str] = None,
    *,
    first: bool = False,
) -> html.Div:
    """子标题级问号：区块标题 + 右侧问号 + 说明卡片。

    用于 Sidebars.md 要求「批注于子标题」的分组（JSD 应力 / 可信度 / 影子择模 /
    模型预测 / Level 1 λ / 双轨蒙特卡洛）。组内每个控件不再另挂问号。
    """
    cls = "sidebar-block-head mb-2 " + ("mt-0" if first else "mt-3")
    return html.Div(
        [
            html.H6(title, className=cls + " mb-0 flex-grow-1"),
            html.Span(
                "?",
                className="param-help-trigger",
                role="button",
                tabIndex=0,
            ),
            _help_card_body(title, explanation_key),
        ],
        className="param-help-wrap d-flex flex-wrap align-items-center gap-2 w-100 mb-1 sidebar-block-head-wrap",
    )


def _sidebar_params_settings_card() -> dbc.Card:
    """侧栏参数：按 ``content/sidebar_left.md`` 的 10 个子标题组织区块。

    - **防御等级参数**：4 个 τ 控件，每个小标题右侧挂问号（``tau_l2_l1`` / ``tau_h1`` /
      ``tau_vol`` / ``tau_ac1``）。
    - **JSD应力 / 可信度 / 影子测试 / 模型生成预测 / Level 1 λ / 双轨蒙特卡洛**：
      6 个分组无小标题，问号挂在子标题右侧（``block_*``）；组内控件用 ``dbc.Label``
      作为小字辅助标签。
    - **模型—市场载荷背离 / 预警成功验证 / 模型更新时间**：保持原结构。
    """
    return dbc.Card(
        dbc.CardBody(
            [
                *_sidebar_block_defense_params(),
                *_sidebar_block_jsd_stress_params(),
                *_sidebar_block_credibility_params(),
                *_sidebar_block_shadow_params(),
                *_sidebar_block_model_predict_params(),
                *_sidebar_block_lambda_params(),
                *_sidebar_block_mc_params(),
                *_sidebar_block_load_test_params(),
                *_sidebar_block_verify_params(),
            ],
            className="pt-2 pb-2",
        ),
        className="mb-2 border-secondary shadow-sm defense-params-sliders",
    )


# --------------------------------------------------------------------------- #
# 分区 builders：一个子标题 = 一个 builder，签名一致（无参数，返回控件 List）    #
# --------------------------------------------------------------------------- #


def _sidebar_block_defense_params() -> List[Any]:
    """① 防御等级参数（4 个 τ，小标题级问号挂在每条上）。"""
    return [
        _sidebar_block_head(get_sidebar_left_title("defense_params", "防御等级参数"), first=True),
        _sidebar_help_title_line(
            get_sidebar_left_label("help_tau_l2_l1", "τ_L2 / τ_L1 可信度阈值"),
            "tau_l2_l1",
        ),
        _sidebar_rail_tau_l2_l1_row(),
        dcc.RangeSlider(
            id="sl-tau-l2-l1",
            min=0.2, max=0.95, step=0.01, value=[0.45, 0.7],
            allowCross=False, pushable=0.02, updatemode="mouseup", tooltip=None,
            className="dash-slider defense-tau-range-sync d-none",
        ),
        _sidebar_help_title_line(
            get_sidebar_left_label("help_tau_h1", "τ_H1 结构熵阈值"),
            "tau_h1",
        ),
        _sidebar_rail_input_row(
            html.Div(
                id="defense-rail-h1",
                children=[_make_tau_h1_rail(0.5)],
            ),
            dbc.Input(
                id="inp-tau-h1", type="number",
                min=0.2, max=0.8, step=0.01, value=0.5, size="sm", className="w-100",
            ),
        ),
        dcc.Slider(
            id="sl-tau-h1", min=0.2, max=0.8, step=0.01, value=0.5,
            updatemode="mouseup", tooltip=None, className="dash-slider d-none",
        ),
        _sidebar_help_title_line(
            get_sidebar_left_label("help_tau_vol", "τ_vol 年化波动阈值"),
            "tau_vol",
        ),
        _sidebar_rail_input_row(
            html.Div(
                id="defense-rail-vol",
                children=[_make_tau_vol_rail(0.32)],
            ),
            dbc.Input(
                id="inp-tau-vol", type="number",
                min=0.10, max=0.70, step=0.01, value=0.32, size="sm", className="w-100",
            ),
        ),
        dcc.Slider(
            id="sl-tau-vol", min=0.10, max=0.70, step=0.01, value=0.32,
            updatemode="mouseup", tooltip=None, className="dash-slider d-none",
        ),
        _sidebar_help_title_line(
            get_sidebar_left_label("help_tau_ac1", "τ_AC1 一阶自相关系数阈值"),
            "tau_ac1",
        ),
        _sidebar_rail_input_row(
            html.Div(
                id="defense-rail-ac1",
                children=[_make_tau_ac1_rail(-0.08)],
            ),
            dbc.Input(
                id="inp-tau-ac1", type="number",
                min=-0.40, max=0.15, step=0.01, value=-0.08, size="sm", className="w-100",
            ),
        ),
        dcc.Slider(
            id="sl-tau-ac1", min=-0.40, max=0.15, step=0.01, value=-0.08,
            updatemode="mouseup", tooltip=None, className="dash-slider d-none",
        ),
    ]


def _aux_label(text: str) -> dbc.Label:
    """无小标题分区中，控件上方的小字灰色辅助标签。"""
    return dbc.Label(text, className="sidebar-param-aux small mb-1")


def _sidebar_block_jsd_stress_params() -> List[Any]:
    """② JSD应力参数（无小标题；k_jsd、ε）。"""
    return [
        _sidebar_block_head_with_help(
            get_sidebar_left_title("jsd_stress_params", "JSD应力参数"),
            "block_jsd_stress",
        ),
        _aux_label(get_app_label("aux_k_jsd_scale", "k_jsd 基线放大倍数")),
        dcc.Slider(
            id="sl-k-jsd", min=1.0, max=4.0, step=0.1, value=2.0,
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
        _aux_label(get_app_label("aux_epsilon_floor", "ε 基线基准值")),
        dcc.Slider(
            id="sl-jsd-baseline-eps-log",
            min=-12.0, max=-3.0, step=0.25, value=-9.0,
            marks={-12: "1e-12", -9: "1e-9", -6: "1e-6", -3: "1e-3"},
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
    ]


def _sidebar_block_credibility_params() -> List[Any]:
    """③ 可信度参数（无小标题；α、β、γ、cred_min、cred_max）。"""
    return [
        _sidebar_block_head_with_help(
            get_sidebar_left_title("credibility_params", "可信度参数"),
            "block_credibility",
        ),
        _aux_label(get_app_label("aux_alpha_base", "α 基准项系数")),
        dcc.Slider(
            id="sl-cred-jsd-base",
            min=0.5, max=15.0, step=0.5, value=6.0,
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
        _aux_label(get_app_label("aux_beta_penalty", "β 惩罚项系数")),
        dcc.Slider(
            id="sl-cred-jsd-pen",
            min=0.0, max=2.0, step=0.05, value=0.12,
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
        _aux_label(get_app_label("aux_gamma_cap", "γ 惩罚上限")),
        dcc.Slider(
            id="sl-cred-pen-cap",
            min=0.05, max=1.0, step=0.05, value=0.35,
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
        _aux_label(get_sidebar_left_label("cred_min", "可信度输出下界")),
        dcc.Slider(
            id="sl-cred-min",
            min=-1.0, max=0.0, step=0.05, value=-0.5,
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
        _aux_label(get_sidebar_left_label("cred_max", "可信度输出上界")),
        dcc.Slider(
            id="sl-cred-max",
            min=0.5, max=1.0, step=0.05, value=1.0,
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
    ]


def _sidebar_block_shadow_params() -> List[Any]:
    """④ 影子测试（择模）参数（无小标题；α_MSE、shadow holdout）。"""
    return [
        _sidebar_block_head_with_help(
            get_sidebar_left_title("shadow_params", "影子测试（择模）参数"),
            "block_shadow",
        ),
        _aux_label(get_app_label("aux_shadow_alpha_mse", "α 为 MSE 权重，1−α 为 JSD 权重")),
        dcc.Slider(
            id="sl-shadow-alpha-mse",
            min=0.0, max=1.0, step=0.01, value=0.5,
            marks={0: "0 (JSD)", 0.5: "0.5", 1: "1 (MSE)"},
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
        _aux_label(get_app_label("aux_shadow_holdout", "影子 holdout 长度（仅训练窗尾部）")),
        dcc.Slider(
            id="sl-shadow-holdout-days",
            min=5, max=120, step=1, value=40,
            marks={5: "5", 40: "40", 80: "80", 120: "120"},
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
    ]


def _sidebar_block_model_predict_params() -> List[Any]:
    """⑤ 模型生成预测结果参数（无小标题；OOS 拟合步数）。"""
    return [
        _sidebar_block_head_with_help(
            get_sidebar_left_title("model_predict_params", "模型生成预测结果参数"),
            "block_model_predict",
        ),
        _aux_label(get_app_label("aux_oos_fit_steps", "OOS 拟合步数")),
        dcc.Slider(
            id="sl-oos-steps",
            min=1, max=44, step=1, value=10,
            marks={
                1: get_app_label("aux_oos_mark_fastest", "1（最快）"),
                10: "10",
                22: "22",
                44: get_app_label("aux_oos_mark_full", "全量"),
            },
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
    ]


def _sidebar_block_lambda_params() -> List[Any]:
    """⑥ Level 1 负面语义惩罚放大倍数 λ（无小标题）。"""
    return [
        _sidebar_block_head_with_help(
            get_sidebar_left_title("lambda_params", "Level 1 负面语义惩罚放大倍数λ"),
            "block_lambda",
        ),
        dcc.Slider(
            id="sl-lambda", min=0.0, max=2.0, step=0.05, value=0.5,
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
    ]


def _sidebar_block_mc_params() -> List[Any]:
    """⑦ 双轨蒙特卡洛参数（无小标题；scenario_step、scenario_impact）。"""
    return [
        _sidebar_block_head_with_help(
            get_sidebar_left_title("mc_params", "双轨蒙特卡洛参数"),
            "block_mc",
        ),
        _aux_label(get_app_label("aux_mc_scenario_step", "自测试集起点，「黑天鹅事件」注入的第 N 个交易日")),
        dcc.Slider(
            id="sl-scenario-step",
            min=1, max=44, step=1, value=30,
            marks={1: "1", 22: "22", 44: "44"},
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
        _aux_label(get_app_label("aux_mc_scenario_impact", "「黑天鹅事件」冲击幅度（对数收益率）")),
        dcc.Slider(
            id="sl-scenario-impact",
            min=-0.30, max=0.0, step=0.01, value=-0.12,
            marks={-0.30: "-30%", -0.12: "-12%", 0: "0"},
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
    ]


def _sidebar_block_load_test_params() -> List[Any]:
    """⑧ 模型—市场载荷背离检验参数（Sidebars.md 未改；保留原小标题结构）。"""
    return [
        _sidebar_block_head(
            get_sidebar_left_title("load_test_params", "模型—市场载荷背离检验参数")
        ),
        _sidebar_help_title_line(
            get_sidebar_left_label("help_semantic_cos_window", "W 计算滚动窗口长度")
        ),
        dcc.Slider(
            id="sl-semantic-cos-window",
            min=1, max=10, step=1, value=5,
            marks={1: "1", 5: "5", 10: "10"},
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
    ]


def _sidebar_block_verify_params() -> List[Any]:
    """⑨ 预警成功验证参数（Sidebars.md 未改；保留 4 个分位控件）。"""
    return [
        _sidebar_block_head(get_sidebar_left_title("verify_params", "预警成功验证参数")),
        _aux_label(get_sidebar_left_label("verify_train_window", "训练窗（天；用于尾部池化）")),
        dcc.Slider(
            id="sl-verify-train-tail-days",
            min=20, max=260, step=5, value=60,
            marks={20: "20", 60: "60", 120: "120", 260: "260"},
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
        _aux_label(get_sidebar_left_label("verify_crash_q", "大跌分位（%）")),
        dcc.Slider(
            id="sl-verify-crash-q",
            min=50, max=99, step=1, value=90,
            marks={50: "50", 75: "75", 90: "90", 99: "99"},
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
        _aux_label(get_sidebar_left_label("verify_std_q", "Std分位（%）")),
        dcc.Slider(
            id="sl-verify-std-q",
            min=50, max=99, step=1, value=90,
            marks={50: "50", 75: "75", 90: "90", 99: "99"},
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
        _aux_label(get_sidebar_left_label("verify_tail_q", "厚尾分位（%）")),
        dcc.Slider(
            id="sl-verify-tail-q",
            min=50, max=99, step=1, value=90,
            marks={50: "50", 75: "75", 90: "90", 99: "99"},
            updatemode="mouseup", tooltip=None, className="dash-slider",
        ),
    ]


def _sidebar_rail_input_row(rail: Any, inputs_inner: Any) -> dbc.Row:
    """md 及以上：色条在左、输入在右；窄屏：条在上、输入在下。"""
    return dbc.Row(
        [
            dbc.Col(rail, xs=12, md=8, lg=8, className="sidebar-rail-col pe-md-2"),
            dbc.Col(
                html.Div(inputs_inner, className="sidebar-rail-inputs"),
                xs=12,
                md=4,
                lg=4,
                className="sidebar-rail-inputs-col",
            ),
        ],
        className="g-2 align-items-stretch mb-2 sidebar-rail-input-row",
    )


def _sidebar_rail_tau_l2_l1_row() -> dbc.Row:
    """τ_L2/τ_L1：色条与其它阈值条同宽；数值框上下排列并略增高。"""
    return dbc.Row(
        [
            dbc.Col(
                html.Div(
                    id="defense-rgy-rail-main",
                    children=[_defense_rgy_rail(0.45, 0.7)],
                    className="defense-switch-dial w-100",
                ),
                xs=12,
                md=8,
                lg=8,
                className="sidebar-rail-col sidebar-rail-col--tau pe-md-2",
            ),
            dbc.Col(
                html.Div(
                    [
                        dbc.Input(
                            id="inp-tau-l2",
                            type="number",
                            min=0.2,
                            max=0.93,
                            step=0.01,
                            value=0.45,
                            size="sm",
                            className="w-100 sidebar-tau-l2l1-input",
                        ),
                        dbc.Input(
                            id="inp-tau-l1",
                            type="number",
                            min=0.21,
                            max=0.95,
                            step=0.01,
                            value=0.7,
                            size="sm",
                            className="w-100 sidebar-tau-l2l1-input",
                        ),
                    ],
                    className="sidebar-rail-inputs sidebar-tau-l2l1-inputs",
                ),
                xs=12,
                md=4,
                lg=4,
                className="sidebar-rail-inputs-col",
            ),
        ],
        className="g-2 align-items-stretch mb-2 sidebar-rail-input-row sidebar-rail-input-row--tau-l2-l1",
    )
