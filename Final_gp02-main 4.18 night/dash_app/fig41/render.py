"""Fig4.1 渲染 — 把 :class:`Fig41Bundle` 转成 Dash / Plotly 组件。

每个子函数只做一件事：
* :func:`_build_hero_alert`       — Part 1 右栏：当前标的 + 大跌提示（亮红 / 银灰）
* :func:`_build_section_std`      — Part 2：Std 大字展示
* :func:`_build_section_crash`    — Part 3：大跌点阵 + 占比
* :func:`_build_section_tail`     — Part 4：厚尾点阵 + 占比
* :func:`_build_verdict_card`     — Part 5：三维度交通灯 + verdict
* :func:`_build_conclusion_section` — Part 6：最终 4.1 结论分析（读 p4_conclusion_analysis.md）
* :func:`_build_main_panel`       — 组合 Part 2–6
* :func:`_build_fallback_panel`   — 快照缺失 ``post`` 时的 markdown 回退
* :func:`_build_fig_daily_returns` — Chart 1 折线图（唯一图表；Chart 2 已于契约层移除）

**纯函数**：
* 入口断言输入类型；
* 不修改 bundle / context / 任何传入对象；
* 所有文案通过 ``get_status_message`` 读取，允许用户通过
  ``status_messages.md`` 直接改。
"""

from __future__ import annotations

import dataclasses
import logging
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from dash_app.fig41.contracts import (
    Fig41Bundle,
    Fig41Components,
    Fig41Context,
    Fig41DualVerdict,
    Fig41Hits,
    Fig41PostAlarm,
)
from dash_app.services.copy import get_md_text, get_status_message

logger = logging.getLogger("dash_app.fig41.render")
_TRACE = os.environ.get("DEBUG_FIG41", "0").strip() not in ("", "0", "false", "False")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if _TRACE:
        try:
            print(f"[fig41.render] {msg % args}" if args else f"[fig41.render] {msg}")
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# 格式化                                                                       #
# --------------------------------------------------------------------------- #


def _fmt_pct(x: Optional[float]) -> str:
    if x is None:
        return "—"
    try:
        xf = float(x)
        return f"{xf:.1%}" if math.isfinite(xf) else "—"
    except (TypeError, ValueError):
        return "—"


def _fmt_num(x: Optional[float]) -> str:
    if x is None:
        return "—"
    try:
        xf = float(x)
        return f"{xf:.4f}" if math.isfinite(xf) else "—"
    except (TypeError, ValueError):
        return "—"


def _dot(color: str) -> html.Span:
    return html.Span(
        "●",
        style={"color": color, "fontSize": "12px", "lineHeight": "12px"},
    )


def _verdict_color(verdict: str) -> str:
    """verdict → dbc.Alert color。"""
    if verdict == "成功":
        return "success"
    if verdict == "较成功":
        return "warning"
    return "danger"


# --------------------------------------------------------------------------- #
# Hero                                                                         #
# --------------------------------------------------------------------------- #


# Part 1 / Part 3 视觉语言：亮红（大跌）· 银灰（未大跌）
_CRASH_COLOR_ON = "#ff1744"   # 亮红
_CRASH_COLOR_OFF = "#c0c0c0"  # 银灰
# Part 2 视觉语言：宝蓝（越基线 → 分散）· 银灰（正常）
_STD_COLOR_ON = "#1565c0"     # 宝蓝（Royal Blue）
_STD_COLOR_OFF = "#c0c0c0"    # 银灰
# Part 4 视觉语言：紫（厚尾）· 黄（正常）
_TAIL_COLOR_ON = "#b388ff"    # 紫
_TAIL_COLOR_OFF = "#ffd600"   # 黄

# 统一说明卡样式：黑底 + 深灰框（Part 2/3/4 共用）
_INFO_CARD_CLASS = "py-3 px-3 mb-2 rounded fig41-info-card"
_INFO_CARD_STYLE = {
    "backgroundColor": "#000000",
    "border": "1px solid #444",
    "minHeight": "90px",
}
# 汉字 label / 数值 字号：数值稍大于汉字，避免数字过于喧宾夺主
_INFO_LABEL_STYLE = {
    "fontSize": "1.15rem",
    "fontWeight": 700,
    "color": "#cfd2d8",
}
_INFO_BIG_STYLE = {
    "fontSize": "1.4rem",
    "fontWeight": 800,
    "letterSpacing": "0.02em",
}
_INFO_OP_STYLE = {
    "fontSize": "1.3rem",
    "fontWeight": 800,
    "color": "#cfd2d8",
}


def _compare_op(v: Optional[float], b: Optional[float]) -> str:
    """返回 '>' / '=' / '<'；任一无效返回 '—'。"""
    try:
        if v is None or b is None:
            return "—"
        vf, bf = float(v), float(b)
    except (TypeError, ValueError):
        return "—"
    if not (math.isfinite(vf) and math.isfinite(bf)):
        return "—"
    if abs(vf - bf) <= 1e-12:
        return "="
    return ">" if vf > bf else "<"


def _info_card(
    *,
    label: str,
    value_text: str,
    baseline_text: str,
    value_color: str,
    op: str,
) -> Any:
    """统一说明卡：`LABEL：X  >/=/<  基线值：Y`（黑底 · 深灰框）。

    汉字 1.15rem 加粗；数值 1.4rem 加粗；op 1.3rem；满足"汉字增大、数值缩小
    但数值仍稍大于汉字"的排版约束。
    """
    return html.Div(
        [
            html.Div(
                [
                    html.Span(f"{label}：", className="me-1", style=_INFO_LABEL_STYLE),
                    html.Span(str(value_text), style={**_INFO_BIG_STYLE, "color": value_color}),
                    html.Span(f"　{op}　", className="mx-2", style=_INFO_OP_STYLE),
                    html.Span("基线值：", className="me-1", style=_INFO_LABEL_STYLE),
                    html.Span(str(baseline_text), style={**_INFO_BIG_STYLE, "color": "#e0e0e0"}),
                ],
                className="d-flex flex-wrap align-items-center",
            ),
        ],
        className=_INFO_CARD_CLASS,
        style=_INFO_CARD_STYLE,
    )


def _build_alarm_date_banner(date_iso: Optional[str], title: str) -> Any:
    """Fig 4.1a/4.1b 顶行：`{title}：YY.MM.DD`（黑底 · 黄字 · 大字）。

    Args:
        date_iso: ISO 日期（YYYY-MM-DD）；None 或无效 → 显示 `—`。
        title: 信号中文标题（如 "模型—模型应力预警日"）。
    """
    label = "—"
    if isinstance(date_iso, str) and len(date_iso) >= 10:
        try:
            y, m, d = date_iso[:10].split("-")
            label = f"{y[-2:]}.{m}.{d}"
        except Exception:
            label = date_iso
    return html.Div(
        [
            html.Span(
                f"{title}：",
                style={
                    "color": "#ffd600",
                    "fontSize": "1.15rem",
                    "fontWeight": 700,
                    "letterSpacing": "0.04em",
                },
            ),
            html.Span(
                label,
                style={
                    "color": "#ffd600",
                    "fontSize": "1.6rem",
                    "fontWeight": 900,
                    "letterSpacing": "0.05em",
                    "marginLeft": "0.25rem",
                },
            ),
        ],
        className="py-3 px-4 mb-2 rounded",
        style={
            "backgroundColor": "#000000",
            "border": "1px solid #444",
            "display": "flex",
            "alignItems": "center",
            "flexWrap": "wrap",
            "minHeight": "70px",
        },
    )


def _build_hero_alert(bundle: Fig41Bundle) -> Any:
    """Part 1 右栏：**当前标的 + 大跌提示**（亮红：R^(h) < 阈值；银灰：≥ 阈值）。

    放大字号 / 加厚 / 匹配 ``_info_card`` 的尺寸，使左右栏视觉平衡。
    """
    assert isinstance(bundle, Fig41Bundle), f"bundle must be Fig41Bundle, got {type(bundle).__name__}"

    focus_label = get_status_message("fig41_hero_focus_label", "当前标的：")

    # 大跌提示：亮红 / 银灰 / 未知
    if bundle.focus_is_crash is True:
        bg, border, fg, status_text = _CRASH_COLOR_ON, "#ff1744", "#ffffff", "大跌"
    elif bundle.focus_is_crash is False:
        bg, border, fg, status_text = _CRASH_COLOR_OFF, "#8c8c8c", "#1a1a1a", "未大跌"
    else:
        bg, border, fg, status_text = "#2b2f36", "#3b4150", "#cfd2d8", "—"

    detail = get_status_message(
        "fig41_hero_crash_detail",
        "R^(5)={rh}　阈值={thr}",
    ).format(rh=_fmt_pct(bundle.focus_Rh), thr=_fmt_pct(bundle.focus_crash_thr_Rh))

    _trace("hero focus=%s is_crash=%s Rh=%s thr=%s",
           bundle.focus_symbol, bundle.focus_is_crash,
           bundle.focus_Rh, bundle.focus_crash_thr_Rh)
    return html.Div(
        [
            html.Span(
                f"{focus_label}{bundle.focus_symbol}",
                style={"color": fg, "fontSize": "1.15rem", "fontWeight": 800},
            ),
            html.Span(
                f"　{status_text}",
                className="ms-2",
                style={"color": fg, "fontSize": "1.6rem", "fontWeight": 900},
            ),
            html.Span(
                f"　{detail}",
                className="ms-3",
                style={"color": fg, "fontSize": "1.0rem", "opacity": 0.9},
            ),
        ],
        className="py-3 px-4 mb-2 rounded",
        style={
            "backgroundColor": bg,
            "border": f"1px solid {border}",
            "minHeight": "90px",
            "display": "flex",
            "alignItems": "center",
            "flexWrap": "wrap",
        },
    )


# --------------------------------------------------------------------------- #
# 点阵                                                                         #
# --------------------------------------------------------------------------- #


# 点阵统一参数：更大、按列对齐（标的与点上下同列）
_DOT_CELL_WIDTH = "46px"
_DOT_FONT_SIZE = "28px"
_DOT_ROW_LABEL_WIDTH = "42px"


def _dot_big(color: str) -> html.Span:
    return html.Span(
        "●",
        style={
            "color": color,
            "fontSize": _DOT_FONT_SIZE,
            "lineHeight": _DOT_FONT_SIZE,
            "textAlign": "center",
            "display": "inline-block",
            "width": "100%",
        },
    )


def _label_cell(text: str) -> html.Div:
    return html.Div(
        text,
        style={
            "fontSize": "0.85rem",
            "color": "#9aa0a6",
            "textAlign": "center",
            "minWidth": _DOT_CELL_WIDTH,
            "flex": "0 0 auto",
        },
    )


def _dot_cell(color: str) -> html.Div:
    return html.Div(
        _dot_big(color),
        style={
            "minWidth": _DOT_CELL_WIDTH,
            "flex": "0 0 auto",
            "textAlign": "center",
        },
    )


def _grid_1xN(
    flags: Dict[str, Any],
    symbols: List[str],
    *,
    on: str,
    off: str,
) -> html.Div:
    """单行点阵：点行 + 标的行同列对齐（列宽固定 ``_DOT_CELL_WIDTH``）。"""
    assert isinstance(symbols, list), "symbols must be list"

    dot_row = html.Div(
        [_dot_cell(on if bool(flags.get(s)) else off) for s in symbols],
        className="d-flex flex-row flex-wrap",
    )
    label_row = html.Div(
        [_label_cell(s) for s in symbols],
        className="d-flex flex-row flex-wrap mt-1",
    )
    return html.Div([dot_row, label_row])


def _grid_5xN(
    tail_flags: List[List[int]],
    symbols: List[str],
    *,
    on: str,
    off: str,
) -> html.Div:
    """5×N 点阵：行 = 告警后第 k 天，列 = 标的；带顶部标的表头，严格按列对齐。"""
    assert isinstance(tail_flags, list), "tail_flags must be list"
    assert isinstance(symbols, list), "symbols must be list"

    # 顶部表头：占位 + 标的列
    header = html.Div(
        [html.Div("", style={"minWidth": _DOT_ROW_LABEL_WIDTH, "flex": "0 0 auto"})]
        + [_label_cell(s) for s in symbols],
        className="d-flex flex-row flex-wrap mb-1",
    )
    rows: List[Any] = [header]
    for i, row in enumerate(tail_flags[:5]):
        row_children: List[Any] = [
            html.Div(
                f"D{i + 1}",
                style={
                    "minWidth": _DOT_ROW_LABEL_WIDTH,
                    "flex": "0 0 auto",
                    "fontSize": "0.85rem",
                    "color": "#9aa0a6",
                    "lineHeight": _DOT_FONT_SIZE,
                    "textAlign": "right",
                    "paddingRight": "6px",
                },
            )
        ]
        for j, _s in enumerate(symbols):
            hit = int(row[j]) if j < len(row) else 0
            row_children.append(_dot_cell(on if hit else off))
        rows.append(html.Div(row_children, className="d-flex flex-row flex-wrap mb-1"))
    return html.Div(rows, className="d-flex flex-column")


# --------------------------------------------------------------------------- #
# 三段 section                                                                 #
# --------------------------------------------------------------------------- #


def _build_section_std(
    bundle: Fig41Bundle,
    tpl: str,  # 保留：与旧签名兼容；不再使用
) -> Any:
    """第二部分：**大字展示** 复合日收益 Std 值 vs Std 基线（越基线 → 亮红；否则 → 银灰）。"""
    _ = tpl  # noqa: F841 — 刻意保留以维持黑盒签名
    title = get_status_message("fig41_section2_title", "第二部分：分散提示（Std）")
    post = bundle.post
    std_v = post.cross_section_std_Rh if post else None
    std_thr = bundle.baselines.std_thr
    hit = bool(bundle.hits.std_above_baseline)
    # Part 2 专用视觉：越基线 → 宝蓝；否则 → 银灰（与 Part 3 亮红/银灰区分开）
    big_color = _STD_COLOR_ON if hit else _STD_COLOR_OFF

    label = get_status_message("fig41_section2_value_label", "复合日收益Std值")
    return html.Div(
        [
            html.H6(title, className="small text-muted mt-2"),
            _info_card(
                label=label,
                value_text=_fmt_num(std_v),
                baseline_text=_fmt_num(std_thr),
                value_color=big_color,
                op=_compare_op(std_v, std_thr),
            ),
        ]
    )


def _build_section_crash(
    post: Fig41PostAlarm,
    baseline_thr: Optional[float],
    hit: bool,
) -> Any:
    """第三部分：大跌点阵（亮红 / 银灰，列对齐）+ 统一说明卡。"""
    title = get_status_message("fig41_section3_title", "第三部分：大跌点阵与占比")
    ratio_lbl = get_status_message("fig41_section3_ratio_lbl", "大跌占比")

    value_color = _CRASH_COLOR_ON if hit else _CRASH_COLOR_OFF
    return html.Div(
        [
            html.H6(title, className="small text-muted mt-2"),
            dbc.Row(
                [
                    dbc.Col(
                        _grid_1xN(
                            post.per_symbol_crash,
                            post.symbols,
                            on=_CRASH_COLOR_ON,
                            off=_CRASH_COLOR_OFF,
                        ),
                        xs=12,
                        md=7,
                    ),
                    dbc.Col(
                        _info_card(
                            label=ratio_lbl,
                            value_text=_fmt_pct(post.crash_ratio),
                            baseline_text=_fmt_pct(baseline_thr),
                            value_color=value_color,
                            op=_compare_op(post.crash_ratio, baseline_thr),
                        ),
                        xs=12,
                        md=5,
                    ),
                ],
                className="g-2",
            ),
        ]
    )


def _build_section_tail(
    post: Fig41PostAlarm,
    baseline_thr: Optional[float],
    hit: bool,
) -> Any:
    """第四部分：厚尾 5×N 点阵（紫 / 黄，列对齐）+ 统一说明卡。"""
    title = get_status_message("fig41_section4_title", "第四部分：厚尾点阵（5×N）与占比")
    ratio_lbl = get_status_message("fig41_section4_ratio_lbl", "单日单资产厚尾点占比")

    value_color = _TAIL_COLOR_ON if hit else _TAIL_COLOR_OFF
    return html.Div(
        [
            html.H6(title, className="small text-muted mt-2"),
            dbc.Row(
                [
                    dbc.Col(
                        _grid_5xN(
                            post.tail_flags_5xN,
                            post.symbols,
                            on=_TAIL_COLOR_ON,
                            off=_TAIL_COLOR_OFF,
                        ),
                        xs=12,
                        md=7,
                    ),
                    dbc.Col(
                        _info_card(
                            label=ratio_lbl,
                            value_text=_fmt_pct(post.tail_ratio),
                            baseline_text=_fmt_pct(baseline_thr),
                            value_color=value_color,
                            op=_compare_op(post.tail_ratio, baseline_thr),
                        ),
                        xs=12,
                        md=5,
                    ),
                ],
                className="g-2",
            ),
        ]
    )


# --------------------------------------------------------------------------- #
# Panel                                                                        #
# --------------------------------------------------------------------------- #


def _traffic_light_dot(label: str, hit: bool) -> Any:
    """大尺寸指示灯 + 小字标签（垂直堆叠，用于 Part 5）。

    hit=True → 绿色（#43a047）；否则 → 银灰。
    """
    color_on = "#43a047"
    color_off = "#6c757d"
    color = color_on if hit else color_off
    return html.Div(
        [
            html.Div(
                style={
                    "width": "44px",
                    "height": "44px",
                    "borderRadius": "50%",
                    "backgroundColor": color,
                    "boxShadow": f"0 0 14px {color}",
                    "margin": "0 auto",
                },
            ),
            html.Div(
                label,
                style={
                    "fontSize": "0.95rem",
                    "color": "#cfd2d8",
                    "textAlign": "center",
                    "marginTop": "0.4rem",
                    "fontWeight": 600,
                    "minWidth": "96px",
                },
            ),
        ],
        className="d-flex flex-column align-items-center px-2",
    )


def _verdict_text_color(verdict: str) -> str:
    """verdict 文字色：成功 = 绿；较成功 = 橙；失败 = 亮红；未知 = 灰。"""
    if verdict == "成功":
        return "#43a047"
    if verdict == "较成功":
        return "#ff9800"
    if verdict == "失败":
        return _CRASH_COLOR_ON
    return "#cfd2d8"


def _build_verdict_card(hits: Fig41Hits) -> Any:
    """第五部分：三维度交通灯（左）+ 实验结果大字（右）；黑底深灰框，**无黄色背景**。"""
    title = get_status_message("fig41_section5_title", "第五部分：预警成功判定（三维度交通灯）")

    tpl_full = get_status_message(
        "fig41_hero_verdict_full", "实验结果：{verdict}（命中 {n_hit}/3）"
    )
    tpl_short = get_status_message(
        "fig41_hero_verdict_short", "实验结果：{verdict}"
    )
    verdict_text = (
        tpl_full.format(verdict=hits.verdict, n_hit=hits.n_hit)
        if hits.n_hit is not None
        else tpl_short.format(verdict=hits.verdict)
    )

    lights = html.Div(
        [
            _traffic_light_dot("Std 越基线", bool(hits.std_above_baseline)),
            _traffic_light_dot("大跌占比越基线", bool(hits.crash_ratio_above_baseline)),
            _traffic_light_dot("厚尾占比越基线", bool(hits.tail_ratio_above_baseline)),
        ],
        className="d-flex flex-row align-items-center",
    )
    verdict_block = html.Div(
        verdict_text,
        style={
            "fontSize": "1.6rem",
            "fontWeight": 900,
            "color": _verdict_text_color(hits.verdict),
            "letterSpacing": "0.03em",
            "textAlign": "right",
        },
    )
    body = dbc.Row(
        [
            dbc.Col(lights, xs=12, md=7),
            dbc.Col(verdict_block, xs=12, md=5, className="d-flex align-items-center justify-content-end"),
        ],
        className="g-2 align-items-center",
    )
    return html.Div(
        [
            html.H6(title, className="small text-muted mt-2"),
            html.Div(
                body,
                className="py-3 px-3 mb-2 rounded",
                style={
                    "backgroundColor": "#000000",
                    "border": "1px solid #444",
                    "minHeight": "110px",
                },
            ),
        ]
    )


def _select_conclusion_case(
    dual: Optional[Fig41DualVerdict],
    md_text: str,
) -> str:
    """根据 (mm_verdict, mv_verdict) 只保留对应情形段（A/B/C/D）+ 共用论点。

    映射表：
    * (mm pass, mv pass) → "## 情形 A"
    * (mm pass, mv fail) → "## 情形 B"
    * (mm fail, mv pass) → "## 情形 C"
    * (mm fail, mv fail) → "## 情形 D"

    每个情形段的边界：从对应 ``## 情形 X`` 标题开始，截到下一个 ``## `` 出现之前
    （但保留情形 B 内的 ``### `` 子标题，因为它们不是 ``## `` 级）。
    """
    def _is_pass(v: str) -> bool:
        return v in ("成功", "较成功")

    mm_pass = bool(dual and _is_pass(dual.mm_verdict))
    mv_pass = bool(dual and _is_pass(dual.mv_verdict))

    if mm_pass and mv_pass:
        case_hdr = "## 情形 A"
    elif mm_pass and not mv_pass:
        case_hdr = "## 情形 B"
    elif (not mm_pass) and mv_pass:
        case_hdr = "## 情形 C"
    else:
        case_hdr = "## 情形 D"

    def _extract_section(text: str, header: str) -> str:
        idx = text.find(header)
        if idx == -1:
            return ""
        rest = text[idx:]
        next_idx = rest.find("\n## ", 1)
        return rest if next_idx == -1 else rest[:next_idx]

    thesis = _extract_section(md_text, "## 论点")
    case_body = _extract_section(md_text, case_hdr)
    parts = [p for p in (thesis, case_body) if p]
    return "\n\n".join(parts) if parts else md_text


def build_fig41_conclusion_card(dual: Optional[Fig41DualVerdict]) -> Any:
    """**独立 Card**：最终 4.1 结论分析（仅展示情形 A / B，来自
    ``content-CHN/p4_conclusion_analysis.md``；占位符实时替换）。
    """
    title = get_status_message("fig41_section6_title", "最终 4.1 结论分析")
    md_text = get_md_text("p4_conclusion_analysis.md", "（缺 p4_conclusion_analysis.md）")

    def _fmt_d(x: Optional[str]) -> str:
        return x if x else "—"

    mm_v = dual.mm_verdict if dual else "—"
    mv_v = dual.mv_verdict if dual else "—"
    mm_d = _fmt_d(dual.mm_t0_date if dual else None)
    mv_d = _fmt_d(dual.mv_t0_date if dual else None)
    earliest = _fmt_d(dual.earliest_t0_date if dual else None)
    final = _fmt_d(dual.final_t0_date if dual else None)

    body_src = _select_conclusion_case(dual, md_text)
    body = (
        body_src
        .replace("{mm_verdict}", mm_v)
        .replace("{mv_verdict}", mv_v)
        .replace("{mm_t0_date}", mm_d)
        .replace("{mv_t0_date}", mv_d)
        .replace("{earliest_t0_date}", earliest)
        .replace("{final_t0_date}", final)
    )
    return dbc.Card(
        [
            dbc.CardHeader(title, className="py-2 small fw-bold"),
            dbc.CardBody(
                dcc.Markdown(body, className="small phase-doc-body mb-0"),
                className="p-3",
            ),
        ],
        className="mb-2 border-secondary shadow-sm",
    )


def _build_main_panel(
    bundle: Fig41Bundle,
    tpl: str,
) -> Any:
    """主分支：把 Part 2 / 3 / 4 / 5 组合成一个 ``html.Div``（不含结论，结论独立成卡）。"""
    assert bundle.post is not None, "_build_main_panel requires bundle.post not None"

    _trace("panel main-branch symbols=%d", len(bundle.post.symbols))
    return html.Div(
        [
            _build_section_std(bundle, tpl),
            _build_section_crash(
                bundle.post,
                bundle.baselines.crash_ratio_thr,
                bundle.hits.crash_ratio_above_baseline,
            ),
            _build_section_tail(
                bundle.post,
                bundle.baselines.tail_ratio_thr,
                bundle.hits.tail_ratio_above_baseline,
            ),
            _build_verdict_card(bundle.hits),
        ],
        className="mt-2",
    )


def _build_fallback_panel(context: Fig41Context) -> Any:
    """快照缺 ``post`` 时的 markdown fallback。"""
    # 惰性 import 避免循环
    from dash_app.render.explain import build_fig41_explain_body

    _trace("panel fallback-branch (no post data)")
    md = build_fig41_explain_body(
        context.ui_mode,
        context.snap_json,
        context.policy,
        context.p2,
        context.meta,
        context.symbols,
    )
    return dcc.Markdown(md, className="small text-muted phase-doc-body")


# --------------------------------------------------------------------------- #
# 图表                                                                         #
# --------------------------------------------------------------------------- #


def _build_fig_daily_returns(bundle: Fig41Bundle, tpl: str) -> go.Figure:
    """折线图：当前标的 t0+1..t0+5 日实际日收益（Chart 1，唯一图）。"""
    from dash_app.figures import fig_fig41_focus_daily_returns

    return fig_fig41_focus_daily_returns(
        bundle.focus_post_dates,
        bundle.focus_daily_returns,
        tpl,
        figure_title=None,
    )


def _maybe_rebind_focus(bundle: Fig41Bundle, override: Optional[str]) -> Fig41Bundle:
    """当 context.focus_override 命中 ``post.symbols`` 时，把 ``focus_*`` 一次性切到新标的。

    纯函数：返回新的 ``Fig41Bundle``；原 bundle 不变。依赖 post 中的
    ``per_symbol_Rh`` / ``per_symbol_daily_returns`` / ``tail_left_thr`` / ``tail_right_thr``
    （extract 层已备齐）。若 override 无效或旧快照缺失 per-symbol 数据，原样返回。
    """
    if not isinstance(override, str) or not override.strip():
        return bundle
    new_focus = override.strip()
    if bundle.post is None or new_focus not in bundle.post.symbols:
        return bundle
    post = bundle.post

    # 数值
    new_Rh = post.per_symbol_Rh.get(new_focus)
    daily = list(post.per_symbol_daily_returns.get(new_focus) or [])
    thr_Rh = bundle.baselines.per_symbol_crash_thr.get(new_focus)

    # focus_is_crash：仅当 Rh 与阈值都可用时判定
    is_crash: Optional[bool]
    try:
        if new_Rh is not None and thr_Rh is not None and math.isfinite(float(new_Rh)) and math.isfinite(float(thr_Rh)):
            is_crash = bool(float(new_Rh) < float(thr_Rh))
        elif new_Rh is not None and bundle.focus_crash_thr_Rh is not None:
            # 回退：使用原焦点阈值（至少让 Rh 可比较；更严格仍建议 pipeline 下发每标阈值）
            is_crash = bool(float(new_Rh) < float(bundle.focus_crash_thr_Rh))
        else:
            is_crash = None
    except (TypeError, ValueError):
        is_crash = None

    # 左右尾占比
    ql = post.tail_left_thr
    qr = post.tail_right_thr
    lh: List[int] = []
    rh: List[int] = []
    for r in daily:
        try:
            rf = float(r)
        except (TypeError, ValueError):
            rf = float("nan")
        lh.append(int(math.isfinite(rf) and ql is not None and rf < float(ql)))
        rh.append(int(math.isfinite(rf) and qr is not None and rf > float(qr)))
    n = max(1, len(daily))
    left_ratio = float(sum(lh) / n) if lh else None
    right_ratio = float(sum(rh) / n) if rh else None

    _trace("rebind focus: %s -> %s (Rh=%s, thr=%s)", bundle.focus_symbol, new_focus, new_Rh, thr_Rh)
    return dataclasses.replace(
        bundle,
        focus_symbol=new_focus,
        focus_Rh=new_Rh,
        focus_crash_thr_Rh=thr_Rh if thr_Rh is not None else bundle.focus_crash_thr_Rh,
        focus_is_crash=is_crash,
        focus_daily_returns=daily,
        focus_tail_left_ratio=left_ratio,
        focus_tail_right_ratio=right_ratio,
    )


# --------------------------------------------------------------------------- #
# 公共入口                                                                     #
# --------------------------------------------------------------------------- #


def build_fig41_components(
    bundle: Fig41Bundle,
    context: Fig41Context,
) -> Fig41Components:
    """根据 Bundle + Context 组装 4 个组件（含顶行预警日 banner）。

    **纯函数**：不修改 bundle / context；所有副作用（日志除外）通过返回值体现。

    - ``context.signal_label`` / ``context.alarm_date_iso`` 用于顶行 banner；
      未提供时按 bundle.dual 回退（4.1 综合卡的默认行为）。
    """
    bundle = _maybe_rebind_focus(bundle, context.focus_override)
    assert isinstance(bundle, Fig41Bundle), (
        f"bundle must be Fig41Bundle, got {type(bundle).__name__}"
    )
    assert isinstance(context, Fig41Context), (
        f"context must be Fig41Context, got {type(context).__name__}"
    )

    _trace("build_fig41 start has_post=%s verdict=%s",
           bundle.has_post, bundle.hits.verdict)

    hero = _build_hero_alert(bundle)

    # 顶行预警日 banner：优先用 context 显式给的 (signal_label, alarm_date_iso)；
    # 未提供时回退到 bundle.dual.final_t0_date + 通用标题。
    sig_title = getattr(context, "signal_label", None) or get_status_message(
        "fig41_banner_generic_title", "最终预警日"
    )
    alarm_iso = getattr(context, "alarm_date_iso", None)
    if alarm_iso is None and bundle.dual is not None:
        alarm_iso = bundle.dual.final_t0_date
    alarm_banner = _build_alarm_date_banner(alarm_iso, sig_title)

    if bundle.has_post:
        panel = _build_main_panel(bundle, context.tpl)
    else:
        panel = _build_fallback_panel(context)

    fig_daily = _build_fig_daily_returns(bundle, context.tpl)

    _trace("build_fig41 done")
    return Fig41Components(
        hero=hero,
        panel=panel,
        fig_daily_returns=fig_daily,
        alarm_banner=alarm_banner,
    )
