from __future__ import annotations

from typing import Any

import dash_bootstrap_components as dbc
from dash import dcc, html

from dash_app.services.copy import get_md_text, get_project_intro, get_topbar_label, get_kronos_hint, get_status_message


def _hint_md_text() -> str:
    """顶栏「使用提示」：文案来源为 ``content-{LANG}/topbar/hint_for_webapp.md``。

    历史上路径曾在 root 与 ``topbar/`` 子目录之间反复，实际文件位于 ``topbar/``；
    这里显式指向子目录，避免读到空串让折叠面板「展开后无内容」。
    """
    return get_md_text(
        "topbar/hint_for_webapp.md",
        "",
    ).strip()


def kronos_weights_ready() -> bool:
    """与 Phase2 / kronos_predictor 一致：模型与分词器目录内须含 .safetensors。"""
    try:
        from kronos_predictor import kronos_parameters_available

        return bool(kronos_parameters_available())
    except Exception:
        return False


def _kronos_topbar_hint_children() -> Any:
    if kronos_weights_ready():
        return html.Span(
            get_kronos_hint("weights_ready", "Kronos 权重就绪：全链路（含影子验证 MSE 与样本外一步预测）使用模型推理。"),
            className="text-muted small",
        )
    return html.Span(
        get_kronos_hint("weights_missing", "未检测到 Kronos 权重（或缺少 .safetensors）：Phase2/影子验证对 Kronos 使用统计回退；建议先点击「拉取」或通过 Git LFS 落盘后再「保存并运行」。"),
        className="text-warning small",
    )


def _btn_run_title_kronos() -> str:
    if kronos_weights_ready():
        return ""
    return get_kronos_hint(
        "btn_run_title_missing",
        get_topbar_label(
            "kronos_pull_fallback_warning",
            "未检测到完整 Kronos 权重：保存并运行后 Phase2 对 Kronos 将使用收益统计回退（非 Transformer）。建议先拉取权重。",
        ),
    )


def _app_masthead() -> html.Div:
    """顶栏：左（标题 + 投资/研究 + 保存运行/Kronos 纵向 + 说明）、中（防御等级）、主栏格（仅 5 Tab，与下方主栏同列对齐）。"""
    _kr_ok = kronos_weights_ready()
    _kr_lbl = get_kronos_hint("kronos_pull_ready", "已检测到Kronos参数，无需拉取") if _kr_ok else get_kronos_hint("kronos_pull_missing", "未检测到Kronos参数，点击拉取")
    return html.Div(
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.H4(get_project_intro().get("title", "AIE1902 防御研究"), className="mb-1 app-topbar-title"),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        dbc.Button(
                                                            get_topbar_label("btn_invest", "投资"),
                                                            id="btn-ui-mode-invest",
                                                            n_clicks=0,
                                                            size="sm",
                                                            className="ui-mode-seg-btn active",
                                                        ),
                                                        dbc.Button(
                                                            get_topbar_label("btn_research", "研究"),
                                                            id="btn-ui-mode-research",
                                                            n_clicks=0,
                                                            size="sm",
                                                            className="ui-mode-seg-btn",
                                                        ),
                                                    ],
                                                    className="ui-mode-segment",
                                                ),
                                                html.Div(
                                                    [
                                                        dbc.Button(
                                                            get_topbar_label("btn_lang_chn", "中"),
                                                            id="btn-lang-chn",
                                                            n_clicks=0,
                                                            size="sm",
                                                            className="ui-mode-seg-btn",
                                                            title=get_topbar_label("btn_lang_chn_title", "切换到中文文案"),
                                                        ),
                                                        dbc.Button(
                                                            get_topbar_label("btn_lang_eng", "EN"),
                                                            id="btn-lang-eng",
                                                            n_clicks=0,
                                                            size="sm",
                                                            className="ui-mode-seg-btn",
                                                            title=get_topbar_label("btn_lang_eng_title", "Switch to English copy"),
                                                        ),
                                                    ],
                                                    className="ui-mode-segment",
                                                ),
                                            ],
                                            className="app-topbar-mode-stack",
                                        ),
                                        html.Div(
                                            [
                                                dbc.Button(
                                                    [html.I(className="fa fa-play me-1"), get_topbar_label("btn_run", "保存运行")],
                                                    id="btn-run",
                                                    color="primary",
                                                    size="sm",
                                                    className="text-nowrap app-btn-run-compact",
                                                    n_clicks=0,
                                                    title=_btn_run_title_kronos()
                                                    or get_topbar_label("btn_run_title_default", "保存配置并执行全链路（原「保存并运行」）"),
                                                ),
                                                dbc.Button(
                                                    _kr_lbl,
                                                    id="btn-kronos-pull",
                                                    color="secondary",
                                                    outline=True,
                                                    size="sm",
                                                    className="w-100 mt-1 app-kronos-btn",
                                                    n_clicks=0,
                                                    disabled=bool(_kr_ok),
                                                ),
                                                dbc.Button(
                                                    [html.I(className="fa fa-download me-1"), get_topbar_label("btn_download_data_json", "下载 data.json")],
                                                    id="btn-download-data-json",
                                                    color="secondary",
                                                    outline=True,
                                                    size="sm",
                                                    className="w-100 mt-1",
                                                    n_clicks=0,
                                                ),
                                                dcc.Download(id="download-data-json"),
                                                html.P(
                                                    id="kr-topbar-hint",
                                                    className="small mb-0 mt-1",
                                                    children=_kronos_topbar_hint_children(),
                                                ),
                                            ],
                                            className="app-topbar-actions app-topbar-actions--stacked",
                                        ),
                                    ],
                                    className="app-topbar-left-toolbar",
                                ),
                            ],
                            className="app-topbar-cell app-topbar-left",
                        ),
                    ],
                    className="app-topbar-cell app-topbar-left",
                ),
                html.Div(
                    [
                        # ── 运行使用提示 ──
                        html.Div(
                            dbc.Button(
                                [
                                    html.I(
                                        className="fa fa-circle-question me-1",
                                        style={"fontSize": "1.15rem"},
                                    ),
                                    html.Span(
                                        get_topbar_label(
                                            "btn_toggle_hints_label",
                                            "Webapp运行与使用提示",
                                        ),
                                        className="small fw-bold",
                                    ),
                                ],
                                id="btn-toggle-topbar-hint",
                                color="link",
                                size="sm",
                                className="p-0 d-flex align-items-center gap-1",
                                n_clicks=0,
                            ),
                            className="text-end",
                        ),
                        dbc.Collapse(
                            dcc.Markdown(
                                _hint_md_text(),
                                className="small text-muted mb-0 phase-doc-body",
                            ),
                            id="topbar-hint-collapse",
                            # R4：**运行前默认展开**——这是新用户第一眼看到的
                            # 操作说明，不应藏起来；用户按 btn-toggle-topbar-hint
                            # 仍可随时收起。
                            is_open=True,
                            className="mb-1",
                        ),
                        # ── 当前防御状态卡片：整张卡可点击 → 横向展开 defense-reasons。
                        # 由 ``_toggle_topbar_reasons`` 回调切换
                        # ``topbar-defense-reasons-collapse.style`` 的 display；
                        # 初始收起（display:none）。
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            get_topbar_label(
                                                "defense_status_prefix", "当前防御状态："
                                            ),
                                            className="small text-muted me-1",
                                        ),
                                        html.Div(
                                            id="sb2-defense-level-badge",
                                            className="mb-0 flex-shrink-0",
                                            children=[
                                                html.Div(
                                                    html.Div(
                                                        f"{get_topbar_label('defense_status_prefix', '当前防御状态：')}{get_status_message('level0_preview', 'Level 0（基准）')}",
                                                        className="reason-body fw-bold",
                                                    ),
                                                    className="defense-reason-tag success mb-0 py-2 small",
                                                ),
                                            ],
                                        ),
                                        html.I(
                                            className="fa fa-chevron-right ms-2 topbar-defense-chevron",
                                            id="topbar-defense-status-chevron",
                                        ),
                                    ],
                                    id="topbar-defense-status-card",
                                    className="topbar-defense-status-card d-flex align-items-center",
                                    role="button",
                                    title=get_topbar_label(
                                        "btn_toggle_defense_reasons",
                                        "展开查看与当前等级相符的防御条件",
                                    ),
                                    n_clicks=0,
                                ),
                                # 与 badge 同一行横向平铺 reason；内容由
                                # ``render/topbar.py::_build_reasons_inline`` 覆盖，
                                # 严格只保留与当前等级严重度相符的 tag。
                                # id 沿用历史名 ``topbar-defense-reasons-collapse``
                                # 以免破坏既有的管线 Output 接线；实际已不是 Collapse，
                                # 而是普通 Div，默认 display:none，由回调切换。
                                html.Div(
                                    id="topbar-defense-reasons-collapse",
                                    className="topbar-defense-reasons-inline ms-2",
                                    style={"display": "none"},
                                ),
                            ],
                            className="topbar-defense-row d-flex align-items-center flex-wrap gap-2",
                        ),
                    ],
                    className="app-topbar-cell app-topbar-center",
                ),
                html.Div(
                    [
                        # ── 防御策略介绍：移回右格最顶（主 tab 之上）──
                        html.Div(
                            id="topbar-defense-intro-slot",
                            className="mb-2 app-topbar-defense-intro-slot",
                        ),
                        html.Div(
                            [
                                dbc.Button(
                                    get_topbar_label("tab_p0", "资产与研究前提"),
                                    id="btn-main-tab-p0",
                                    n_clicks=0,
                                    size="sm",
                                    className="main-tab-seg-btn active",
                                    title=get_topbar_label("tab_p0_title", "资产自定义面板与研究前提"),
                                ),
                                dbc.Button(
                                    get_topbar_label("tab_p1", "数据诊断"),
                                    id="btn-main-tab-p1",
                                    n_clicks=0,
                                    size="sm",
                                    className="main-tab-seg-btn",
                                    title=get_topbar_label("tab_p1_title", "数据诊断与失效前兆识别"),
                                ),
                                dbc.Button(
                                    get_topbar_label("tab_p2", "信号对抗"),
                                    id="btn-main-tab-p2",
                                    n_clicks=0,
                                    size="sm",
                                    className="main-tab-seg-btn",
                                    title=get_topbar_label("tab_p2_title", "多范式信号对抗与模型失效识别"),
                                ),
                                dbc.Button(
                                    get_topbar_label("tab_p3", "自动防御"),
                                    id="btn-main-tab-p3",
                                    n_clicks=0,
                                    size="sm",
                                    className="main-tab-seg-btn",
                                    title=get_topbar_label("tab_p3_title", "自动防御响应"),
                                ),
                                dbc.Button(
                                    get_topbar_label("tab_p4", "实验结论"),
                                    id="btn-main-tab-p4",
                                    n_clicks=0,
                                    size="sm",
                                    className="main-tab-seg-btn",
                                    title=get_topbar_label("tab_p4_title", "实验结论展示"),
                                ),
                            ],
                            className="main-tab-segment",
                        ),
                    ],
                    className="app-topbar-cell app-topbar-main",
                ),
            ],
            className="app-topbar-inner",
        ),
        className="app-topbar app-topbar--v3",
    )
