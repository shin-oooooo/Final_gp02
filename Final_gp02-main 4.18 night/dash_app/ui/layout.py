"""Shared layout helpers and build_full_layout assembly."""

from __future__ import annotations

import copy
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from dash_app.render.explain import (
    me_phase0_intro_md,
    ME_PHASE1_INTRO,
    ME_PHASE2_INTRO,
    ME_PHASE3_INTRO,
    ME_PHASE4_INTRO,
)
from dash_app.features.research_trace import get_trace_modal_sections, load_code_excerpt
from research.schemas import Phase0Input
from dash_app.constants import _DEFAULT_UNIVERSE
from dash_app.services.copy import get_app_label, get_status_message, get_topbar_label

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _templates(theme: str) -> str:
    return "plotly_dark" if theme == "dark" else "plotly_white"


def _entropy_badge(h: float) -> str:
    if h >= 0.5:
        return "success"
    if h >= 0.4:
        return "warning"
    return "danger"


def _default_data_json_path() -> str:
    return os.path.normpath(
        os.environ.get("AIE1902_DATA_JSON") or os.path.join(_ROOT, "data.json")
    )


def _figure_wrap(color_idx: int, children: Any, fig_label: str | None = None) -> html.Div:
    """同一分页内：将单个 Figure 与其研究索引 / 讲解卡用细色框成组。
    若传入 fig_label（如 "Figure2.3"），在框顶插入 HTML 标题行（带下划线色线）。
    """
    body = children if isinstance(children, list) else [children]
    if fig_label:
        header = html.Div(fig_label, className="figure-unit-label")
        body = [header] + body
    return html.Div(body, className=f"figure-unit figure-unit--c{int(color_idx) % 6}")


def _fig_explain_title(phase: int, sub: int, caption: str) -> str:
    """Build a main-figure explanation card title.

    模板来自 ``all_labels.md`` 的 ``fig_explain_title_fmt`` 键；占位符 ``{phase}``、
    ``{sub}``、``{caption}`` 在此注入，便于中英文各自定义排版（如中文用「讲解：」、
    英文用「 · Explanation · 」）。
    """
    fmt = get_app_label("fig_explain_title_fmt", "Figure{phase}.{sub}讲解：{caption}")
    return fmt.format(phase=int(phase), sub=int(sub), caption=caption)


def _fmt_p(p: Any) -> str:
    if p is None:
        return "—"
    try:
        v = float(p)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(v):
        return "—"
    if v < 1e-6:
        return "<1e-6"
    if v < 0.0001:
        return "<0.0001"
    return f"{v:.4g}"


_PLACEHOLDER_COMPUTE_PROMPT_FALLBACK = "点击左侧「应用并重算」开始计算"


def _placeholder_fig(
    title: Optional[str] = None,
    template: str = "plotly_dark",
) -> go.Figure:
    if title is None:
        title = get_app_label("placeholder_compute_prompt", _PLACEHOLDER_COMPUTE_PROMPT_FALLBACK)
    fig = go.Figure()
    fig.update_layout(
        template=template,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[dict(
            text=title, xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color="#6c757d"),
            xanchor="center", yanchor="middle",
        )],
        margin=dict(l=20, r=20, t=10, b=10),
    )
    return fig


def _level_status_title(level: int) -> str:
    if level >= 2:
        return get_app_label("level_status_l2", "STATUS: Level 2 — 熔毁防御")
    if level == 1:
        return get_app_label("level_status_l1", "STATUS: Level 1 — 警戒防御")
    return get_app_label("level_status_l0", "STATUS: Level 0 — 标准防御")


def _level_badge_color(level: int) -> str:
    if level >= 2:
        return "danger"
    if level == 1:
        return "warning"
    return "success"


def _phase_intro_card(md: str) -> html.Div:
    return html.Div(
        dbc.Card(
            [
                dbc.CardHeader(
                    get_app_label("phase_intro_card_header", "Introduction（MeToAI §2）"),
                    className="phase-card-header-title",
                ),
                dbc.CardBody(dcc.Markdown(md, className="mb-0 phase-doc-body")),
            ],
            className="mb-2 shadow-sm border-secondary phase-text-panel",
        ),
        className="invest-interpretation-block",
    )


def _p0_resolved_window_strings(snap: Any) -> Tuple[str, str, str, str]:
    """train/test ISO dates: from last-snap phase0 meta, else Phase0Input() template."""
    p0d = Phase0Input()
    tr_s, tr_e = p0d.train_start, p0d.train_end
    te_s, te_e = p0d.test_start, p0d.test_end
    if isinstance(snap, dict) and isinstance(snap.get("phase0"), dict):
        p0 = snap["phase0"]
        meta = p0.get("meta") or {}
        rw = meta.get("resolved_windows") or {}
        tr_idx = p0.get("train_index") or []
        te_idx = p0.get("test_index") or []
        tr_s = str(rw.get("train_start") or (tr_idx[0] if tr_idx else tr_s))
        tr_e = str(rw.get("train_end") or (tr_idx[-1] if tr_idx else tr_e))
        te_s = str(rw.get("test_start") or (te_idx[0] if te_idx else te_s))
        te_e = str(rw.get("test_end") or (te_idx[-1] if te_idx else te_e))
    return tr_s, tr_e, te_s, te_e


def _phase_intro_p0_card() -> html.Div:
    ts = _p0_resolved_window_strings(None)
    return html.Div(
        dbc.Card(
            [
                dbc.CardHeader(
                    get_app_label("phase_intro_card_header", "Introduction（MeToAI §2）"),
                    className="phase-card-header-title",
                ),
                dbc.CardBody(
                    dcc.Markdown(
                        me_phase0_intro_md(*ts),
                        id="p0-intro-me-md",
                        className="mb-0 phase-doc-body",
                    )
                ),
            ],
            className="mb-2 shadow-sm border-secondary phase-text-panel",
        ),
        className="invest-interpretation-block",
    )


def _overview_card(tab: str, title: str, md_content: str, *, md_id: Optional[str] = None, is_open_default: bool = False) -> html.Div:
    body = dcc.Markdown(md_content, className="mb-0 phase-doc-body", id=md_id) if md_id else dcc.Markdown(md_content, className="mb-0 phase-doc-body")
    return html.Div(
        dbc.Card(
            [
                dbc.CardHeader(
                    html.Div(
                        [
                            html.Span(title, className="phase-card-header-title"),
                            html.I(className="fa fa-angle-down ms-2"),
                        ],
                        id={"type": "overview-card-header", "index": tab},
                        n_clicks=0,
                        style={"cursor": "pointer"},
                    ),
                    className="py-2",
                ),
                dbc.Collapse(
                    dbc.CardBody(body, className="pt-2 pb-3"),
                    id={"type": "overview-card-collapse", "index": tab},
                    is_open=is_open_default,
                ),
            ],
            className="mb-2 shadow-sm border-secondary phase-text-panel",
        ),
        id={"type": "overview-card-wrap", "index": tab},
        className="overview-card-wrap",
    )


def _loading_overlay_spinner(md_text: str) -> html.Div:
    """Shown as dcc.Loading custom_spinner while descendants are updating."""
    hint = md_text or get_app_label("loading_text", "正在计算…")
    return html.Div(
        [
            dbc.Card(
                [
                    dbc.CardHeader(
                        get_app_label("loading_card_title", "数据与图表加载中"),
                        className="py-2 small",
                    ),
                    dbc.CardBody(
                        dcc.Markdown(hint, className="mb-0 small phase-doc-body"),
                        className="py-2",
                    ),
                ],
                className="border-info shadow-sm mb-0 loading-dash-hint-card",
            ),
            dbc.Spinner(color="primary", size="lg", spinner_class_name="mt-2"),
        ],
        className="dash-loading-intro-wrap",
    )


def _main_tab_panel_styles(active: Optional[str]) -> List[Dict[str, str]]:
    t = (active or "p0").strip()
    keys = ("p0", "p1", "p2", "p3", "p4")
    return [{"display": "block" if t == k else "none"} for k in keys]


def _main_tab_seg_btn_class(active: Optional[str]) -> List[str]:
    t = (active or "p0").strip()
    keys = ("p0", "p1", "p2", "p3", "p4")
    return ["main-tab-seg-btn" + (" active" if t == k else "") for k in keys]


def _ui_mode_seg_btn_class(mode: Optional[str]) -> Tuple[str, str]:
    m = (mode or "invest").strip()
    inv = "ui-mode-seg-btn" + (" active" if m == "invest" else "")
    res = "ui-mode-seg-btn" + (" active" if m == "research" else "")
    return inv, res


def _analysis_card(title: str, md: str) -> html.Div:
    """投资向可折叠解读；研究+有快照时由 CSS 隐藏，由图下索引树承接。"""
    return html.Div(
        dbc.Card(
            [
                dbc.CardHeader(
                    dbc.Button(
                        [html.I(className="fa fa-book-open me-2"), title],
                        id={"type": "analysis-toggle", "index": title},
                        color="link",
                        className="text-start w-100 p-0 phase-card-header-title",
                        n_clicks=0,
                    ),
                    className="bg-transparent py-2",
                ),
                dbc.Collapse(
                    dbc.CardBody(
                        dcc.Markdown(md, mathjax=True, className="mb-0 phase-doc-body", style={"lineHeight": "1.8"}),
                        className="pt-2 pb-3",
                    ),
                    id={"type": "analysis-collapse", "index": title},
                    is_open=False,
                ),
            ],
            className="mb-2 shadow-sm border-secondary phase-text-panel",
        ),
        className="invest-interpretation-block",
    )


def _research_under_graph(uid: str) -> html.Div:
    """Placeholder container under each graph for research-mode index/accordion.

    Some panels import this helper to keep a stable DOM slot even when the
    research under-graph content is injected by other callbacks or disabled.
    """
    key = (uid or "").strip() or "graph"
    return html.Div(
        id={"type": "research-under-graph", "index": key},
        className="research-under-accordion",
        children=[],
    )


def _figx_card_header(title: str) -> dbc.CardHeader:
    return dbc.CardHeader(html.Span(title, className="small fw-bold"), className="py-1")


# NOTE: `_defense_cond_div` / `_div_from_fig_line` / `_sb2_idle_reason_block`
# 的权威实现在 ``dash_app/dash_ui_helpers.py``（含 R2.4 截断逻辑）。此处曾有
# 重复副本，2026-04 audit 确认无任何 import，统一删除，避免被误引用绕过截断。


def _sidebar_param_note(text: str) -> html.P:
    """参数上方说明（与控件一一对应，文案按需求原文）。"""
    return html.P(text, className="small mb-1 phase-doc-body defense-param-hint")


def _research_effective(mode: Optional[str], snap: Any) -> bool:
    """研究模式差异化 UI：仅在已有跑批快照后启用（运行前与投资视图一致）。"""
    if (mode or "invest") != "research":
        return False
    return isinstance(snap, dict) and bool(snap.get("phase0"))


def _trace_inline_accordion(repo_root: str, snap_d: Dict[str, Any], trace_key: str, uid: str) -> html.Div:
    """Full trace sections inline (replaces modal)."""
    sec = get_trace_modal_sections(snap_d, trace_key)
    if sec is None:
        return html.Div()
    code_blocks = [dcc.Markdown(load_code_excerpt(repo_root, r), className="small") for r in sec.code]
    idsuf = "".join(ch if ch.isalnum() else "_" for ch in uid)[:48]
    acc = dbc.Accordion(
        [
            dbc.AccordionItem(
                dcc.Markdown(sec.result_raw, className="phase-doc-body small"),
                title=get_app_label("research_accordion_result_title", "结果 → 原始数据"),
                item_id=f"{idsuf}_r",
            ),
            dbc.AccordionItem(
                dcc.Markdown(sec.calculation, className="phase-doc-body small"),
                title=get_app_label("research_accordion_calc_title", "计算过程"),
                item_id=f"{idsuf}_c",
            ),
            dbc.AccordionItem(
                html.Div(
                    [
                        html.H6(
                            get_app_label("research_header_raw", "原始数据"),
                            className="fw-bold text-muted small mb-1",
                        ),
                        dcc.Markdown(sec.params_raw, className="phase-doc-body small mb-3"),
                        html.H6(
                            get_app_label("research_header_learning", "学习过程"),
                            className="fw-bold text-muted small mb-1",
                        ),
                        dcc.Markdown(sec.learning, className="phase-doc-body small mb-3"),
                        html.H6(
                            get_app_label("research_header_source", "源码原文"),
                            className="fw-bold text-muted small mb-1",
                        ),
                        html.Div(code_blocks) if code_blocks else html.Div(get_status_message("no_source_index", "（无源码索引）"), className="text-muted small"),
                    ]
                ),
                title=get_app_label("research_accordion_source_title", "源码与模型参数"),
                item_id=f"{idsuf}_s",
            ),
        ],
        id=f"inline_trace_{idsuf}",
        flush=True,
        always_open=True,
        active_item=[f"{idsuf}_r", f"{idsuf}_c", f"{idsuf}_s"],
        className="research-trace-accordion mt-2",
    )
    return html.Div(acc, className="trace-inline-wrap")


def build_full_layout(project_intro_md: str = "", loading_dashboard_md: str = "", lang: str = "chn") -> Any:
    """Assemble the full application layout from modular UI components.

    Args:
        project_intro_md: 项目综述 Markdown 文本（从 ``content-{LANG}/project_intro.md`` 读入）。
        loading_dashboard_md: 加载态提示 Markdown 文本。
        lang: 当前语言 ``"chn"`` / ``"eng"``，写入 ``lang-store`` 的初值；顶栏按钮
            切换后由 clientside callback 通过 ``?lang=`` 刷新页面重新注入。
    """
    from dash_app.ui.topbar import _app_masthead
    from dash_app.ui.sidebar_left import _sidebar_params_settings_card
    from dash_app.ui.sidebar_right import sidebar_right_column
    from dash_app.ui.main_p0 import main_p0_panel
    from dash_app.ui.main_p1 import main_p1_panel
    from dash_app.ui.main_p2 import main_p2_panel
    from dash_app.ui.main_p3 import main_p3_panel
    from dash_app.ui.main_p4 import main_p4_panel
    from dash_app.ui.modals import modal_add_asset
    from research.schemas import DefensePolicyConfig

    _project_intro_md = project_intro_md or get_app_label(
        "project_intro_fallback",
        "（请将介绍写入 `dash_app/content/project_intro.md`。）",
    )
    _loading_md = loading_dashboard_md or get_app_label(
        "loading_md_fallback",
        "正在计算全链路结果，请稍候…",
    )

    col_scroll_style = {"overflowY": "auto", "height": "100vh"}

    return dbc.Container(
        [
            dcc.Store(id="theme-store", data="dark"),
            dcc.Store(id="defense-policy-config", data=DefensePolicyConfig().model_dump()),
            dcc.Store(id="last-snap", data=None),
            dcc.Store(id="pipeline-render-ctx", data={"kind": "idle"}),
            dcc.Store(id="symbols-store", data=[]),
            dcc.Store(id="sentiment-detail-store", data=None),
            dcc.Store(id="asset-universe-store", data=copy.deepcopy(_DEFAULT_UNIVERSE)),
            dcc.Store(id="p0-weight-store", data=None),
            dcc.Store(id="p0-weight-order", data=None),
            dcc.Store(id="p0-pie-selected", data=None),
            dcc.Store(id="p0-strike-store", data={"syms": [], "cats": []}),
            dcc.Store(id="figure-caption-bundle", data={}),
            dcc.Store(id="radio-ui-mode", data="invest"),
            dcc.Store(id="main-tab-store", data="p0"),
            dcc.Store(id="sidebar1-collapsed", data=False),
            dcc.Store(id="download-btn-state-store", data="idle"),
            dcc.Store(id="run-btn-state-store", data="idle"),
            dcc.Store(id="lang-store", data=(lang if lang in ("chn", "eng") else "chn")),
            dcc.Location(id="lang-url-refresh", refresh=True),
            _app_masthead(),
            dbc.Row(
                [
                    # Sidebar 1: Parameters
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    dbc.Button(
                                        get_app_label("sidebar_collapse_toggle_label", "<<"),
                                        id="btn-sidebar1-toggle",
                                        color="secondary",
                                        outline=True,
                                        size="sm",
                                        className="sidebar1-toggle-btn",
                                        n_clicks=0,
                                    ),
                                ],
                                className="sidebar1-toggle-strip",
                            ),
                            html.Div(
                                className="sidebar-scroll-inner sidebar1-scroll-inner",
                                children=[
                                    dcc.Tabs(
                                        id="sidebar-tabs",
                                        value="side-params",
                                        className="custom-tabs mb-2",
                                        parent_className="custom-tabs",
                                        children=[
                                            dcc.Tab(
                                                label=get_app_label("sidebar_tab_overview_label", "研究项目综述"),
                                                value="side-overview",
                                                className="custom-tab",
                                                children=[
                                                    html.Div(
                                                        id="sidebar-overview-cards-container",
                                                        style={"display": "flex", "flexDirection": "column"},
                                                        children=[
                                                            _overview_card(
                                                                "project",
                                                                get_topbar_label("overview_project_title", "项目综述"),
                                                                _project_intro_md,
                                                                is_open_default=True,
                                                            ),
                                                            _overview_card("p0", get_topbar_label("overview_p0_title", "P0 · 资产与研究前提"), me_phase0_intro_md(*_p0_resolved_window_strings(None)), md_id="p0-intro-me-md"),
                                                            _overview_card("p1", get_topbar_label("overview_p1_title", "P1 · 数据诊断"), ME_PHASE1_INTRO),
                                                            _overview_card("p2", get_topbar_label("overview_p2_title", "P2 · 信号对抗"), ME_PHASE2_INTRO),
                                                            _overview_card("p3", get_topbar_label("overview_p3_title", "P3 · 自动防御"), ME_PHASE3_INTRO),
                                                            _overview_card("p4", get_topbar_label("overview_p4_title", "P4 · 实验结论"), ME_PHASE4_INTRO),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            dcc.Tab(
                                                label=get_app_label("sidebar_tab_params_label", "防御策略与参数自定义"),
                                                value="side-params",
                                                className="custom-tab",
                                                children=[
                                                    _sidebar_params_settings_card(),
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                        xs=12, md=3, lg=2,
                        id="sidebar1-col",
                        className="mb-0 order-3 order-lg-1 sidebar1-col dash-three-col h-100",
                        style=col_scroll_style,
                    ),
                    # Sidebar 2: Defense Dashboard
                    sidebar_right_column(),
                    # Main area
                    dbc.Col(
                        html.Div(
                            dcc.Loading(
                                id="loading-main",
                                type="circle",
                                color="#5cc6ff",
                                delay_show=120,
                                delay_hide=200,
                                # NOTE: 不使用 custom_spinner，避免 Loading 用 spinner 替换
                                # children 导致主面板在加载时整块塌陷。`overlay_style` 让
                                # spinner 浮在 children 之上、保留底层布局尺寸。
                                # `show_initially=False` 是关键：初次进入页面时，
                                # dcc.Loading 不会默认渲染 spinner（默认为 True），否则
                                # 在 children 仍未被 callback 填充前就会呈现“半屏”效果。
                                show_initially=False,
                                overlay_style={
                                    "visibility": "visible",
                                    "opacity": 0.35,
                                    "backgroundColor": "rgba(0,0,0,0.18)",
                                },
                                parent_className="main-loading-parent",
                                parent_style={"minHeight": "100%", "height": "100%"},
                                children=[
                                    html.Div(id="diagnostic-summary", className="mb-2"),
                                    html.Div(id="header-status", className="mb-2"),
                                    html.Div(
                                        id="main-panels-root",
                                        className="main-panels-root custom-tabs mb-2",
                                        children=[
                                            main_p0_panel(),
                                            main_p1_panel(),
                                            main_p2_panel(),
                                            main_p3_panel(),
                                            main_p4_panel(),
                                        ],
                                    ),
                                ],
                            ),
                            className="main-scroll-clip",
                        ),
                        xs=12, md=4, lg=5,
                        className="order-1 order-lg-3 main-dashboard-col dash-three-col",
                        style=col_scroll_style,
                    ),
                ],
                id="dash-body-three-col-row",
                className="g-0 align-items-stretch dashboard-three-col-row app-body-row",
            ),
            modal_add_asset(),
        ],
        fluid=True,
        className="p-3 phase-doc-scope app-mode-invest app-shell",
        id="app-mode-shell",
        style={"overflow": "hidden", "height": "100vh"},
    )
