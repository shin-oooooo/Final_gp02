"""Main panel layout for Phase 4.

**布局**（R2）：
* **Fig 4.1a / Fig 4.1b 左右并排**（``dbc.Row`` 内两个 ``dbc.Col(md=6)``），便于
  用户对比模型—模型应力预警与模型应力—市场载荷方向预警。
* 每列内部自上而下（"每个卡片和图表各占一行"）：
    1. **预警日 banner**（``p4-fig41-alarm-banner`` / ``p4-fig41b-alarm-banner``）——
       idle 状态下由 ``fig41/render._build_alarm_date_banner`` 返回空 Div，整块不留占位。
    2. **标的搜索栏**（``p4-verify-search`` / ``p4-verify-search-b``）——两框相互独立，
       分别驱动 4.1a / 4.1b 的 focus_override。
    3. **Hero / 阈值卡**（``p4-verify-hero`` / ``p4-fig41b-verify-hero``）——
       标的切换时实时刷新；idle 态同样返回空 Div。
    4. **图表 Chart 1**（``p4-fig41-jsd`` / ``p4-fig41b-jsd``）。
    5. **分析 / Part 2-5**（``p4-fig41-analysis-md`` / ``p4-fig41b-analysis-md``）。
* **独立结论卡**（``p4-fig41-conclusion``）。
* **Fig 4.1 讲解卡**（``p4-fig41-explain-card``）。
* **Fig 4.2 实验栈**（``p4-experiments-stack``）+ **Fig 4.2 独立结论卡**（``p4-fig42-conclusion``，
  情形 A–E，源自 ``content-{LANG}/Res/Fig4.2-Res.md §9.1``）+ **Fig 4.2 讲解卡**
  （``p4-fig42-explain-card``）。
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from dash_app.render.explain._loaders import load_fig4_template
from dash_app.services.copy import get_app_label, get_figure_title, get_md_text
from dash_app.ui.layout import (
    _analysis_card,
    _figure_wrap,
    _placeholder_fig,
    explain_title_from_figures,
)


# Phase 4 面板末尾附录卡片。文档按顺序落在 Res-templates/ 下；
# 缺失时 `get_md_text` 会返回 default 字符串，卡片展开后仍有提示不至于空白。
# 所有卡片默认**收起**——这 4 份都是长文，默认打开会干扰上方诊断视图。
_P4_APPENDIX_DOCS = (
    (
        "方法论与局限说明",
        "Res-templates/methodology_constraints.md",
        "（缺 `methodology_constraints.md`）",
    ),
    (
        "模型参数学习：方法论与简要过程",
        "Res-templates/models_params_learning.md",
        "（缺 `models_params_learning.md`）",
    ),
    (
        "模型约束、能力与局限（Models — constraints, strengths, weaknesses）",
        "Res-templates/models_constraints.md",
        "（缺 `models_constraints.md`）",
    ),
    (
        "参考文献 / References & Resources",
        "Res-templates/Reference.md",
        "（缺 `Reference.md`）",
    ),
)


def _p4_appendix_cards() -> html.Div:
    """Phase 4 面板末尾的 4 张可展开附录卡片（与其它讲解卡同样样式 / 同一回调）。"""
    return html.Div(
        [
            _analysis_card(title, get_md_text(path, default), is_open=False)
            for (title, path, default) in _P4_APPENDIX_DOCS
        ],
        id="p4-appendix-docs",
        className="mt-3",
    )

# Chart 1 尺寸：高度保持 260，宽度随列自适应（不再硬限 720px —— 分栏后一列容得下）。
_CHART1_STYLE = {"height": "260px"}


def _build_search_block(dropdown_id: str) -> html.Div:
    """一张标的搜索框（Fig4.1a 与 Fig4.1b 各用一份；options 由 ``p2_symbol.py`` 同步）。"""
    return html.Div(
        [
            dbc.Label(
                get_app_label("p2_symbol_search_label", "标的（可搜索）"),
                className="small text-muted mb-1",
            ),
            dcc.Dropdown(
                id=dropdown_id,
                clearable=False,
                searchable=True,
                placeholder=get_app_label("p2_symbol_search_placeholder", "搜索代码…"),
                className="text-center",
            ),
        ],
        className="mb-2",
    )


def _fig41_card(
    *,
    header_title: str,
    inner_label: str,
    alarm_id: str,
    search_id: str,
    hero_id: str,
    chart_id: str,
    analysis_id: str,
) -> dbc.Card:
    """一张 Fig4.1 卡；4.1a / 4.1b 同一函数生成，仅 id 不同。

    纵向堆叠：**预警日 banner → 搜索框 → Hero 阈值卡 → 图表 → 分析正文**。
    所有与快照相关的 id 由 ``dashboard_pipeline._render_dashboard_face`` 填写；
    idle 态下 banner / hero 返回空 Div，页面不留"—"占位。
    """
    _ = header_title  # R3: 去除黑色卡头（上层 figure-unit 的彩色标题已足够，避免重复）
    return dbc.Card(
        dbc.CardBody(
            _figure_wrap(
                0,
                [
                    # 1. 预警日 banner（放到搜索栏之上）
                    html.Div(id=alarm_id, className="mb-2"),
                    # 2. 标的搜索栏
                    _build_search_block(search_id),
                    # 3. Hero / 阈值卡
                    html.Div(id=hero_id, className="mb-2"),
                    # 4. 图表
                    dcc.Graph(
                        id=chart_id,
                        figure=_placeholder_fig("日收益"),
                        config={"displayModeBar": False},
                        style=_CHART1_STYLE,
                    ),
                    # 5. 分析 / Part 2-5 / fallback markdown
                    html.Div(id=analysis_id, className="mt-2 mb-0"),
                ],
                fig_label=inner_label,
            ),
            className="p-2",
        ),
        className="mb-2 border-secondary shadow-sm h-100",
    )


def main_p4_panel() -> html.Div:
    """Phase 4 主栏：Fig 4.1a + Fig 4.1b（左右并排）+ 独立结论 + Fig 4.1 讲解卡 + Fig 4.2 实验栈 + Fig 4.2 讲解卡。"""
    cap41a_hdr = get_figure_title(
        "fig_4_1_jsd",
        "Figure 4.1a · 模型—模型应力预警有效性检验",
    )
    cap41a_inner = get_figure_title(
        "fig_4_1_jsd_inner",
        "Figure 4.1.1 · 当前标的告警后 5 日简单日收益",
    )
    cap41b_hdr = get_figure_title(
        "fig_4_1_cos",
        "Figure 4.1b · 模型应力—市场载荷方向预警有效性检验",
    )
    cap41b_inner = get_figure_title(
        "fig_4_1_cos_inner",
        "Figure 4.1.2 · 当前标的告警后 5 日简单日收益",
    )
    card_41a = _fig41_card(
        header_title=cap41a_hdr,
        inner_label=cap41a_inner,
        alarm_id="p4-fig41-alarm-banner",
        search_id="p4-verify-search",
        hero_id="p4-verify-hero",
        chart_id="p4-fig41-jsd",
        analysis_id="p4-fig41-analysis-md",
    )
    card_41b = _fig41_card(
        header_title=cap41b_hdr,
        inner_label=cap41b_inner,
        alarm_id="p4-fig41b-alarm-banner",
        search_id="p4-verify-search-b",
        hero_id="p4-fig41b-verify-hero",
        chart_id="p4-fig41b-jsd",
        analysis_id="p4-fig41b-analysis-md",
    )
    return html.Div(
        id="main-panel-p4",
        className="main-tab-panel",
        style={"display": "none"},
        children=[
            # Fig 4.1a / 4.1b 并排对比
            dbc.Row(
                [
                    dbc.Col(card_41a, xs=12, md=6, className="mb-2"),
                    dbc.Col(card_41b, xs=12, md=6, className="mb-2"),
                ],
                className="g-2 align-items-stretch",
            ),
            # 独立结论卡
            html.Div(id="p4-fig41-conclusion", className="mb-2"),
            # Fig 4.1 讲解卡（与 P1/P2/P3 同一 _analysis_card 样式；内容由 _caption_refresh_on_mode 覆盖）
            html.Div(
                id="p4-fig41-explain-card",
                className="mb-2",
                children=_analysis_card(
                    explain_title_from_figures(
                        "fig_4_1_explain", "invest", "Figure 4.1 讲解"
                    ),
                    load_fig4_template("1", "invest"),
                    is_open=False,
                    md_slot_id="p4-fig41-explain-md",
                ),
            ),
            # Fig 4.2 实验栈
            html.Div(id="p4-experiments-stack", className="mt-2"),
            # Fig 4.2 独立结论卡（情形 A–E，源自 content-{LANG}/Res/Fig4.2-Res.md §9.1）
            html.Div(id="p4-fig42-conclusion", className="mt-2"),
            # Fig 4.2 讲解卡（与其它讲解卡同一样式）
            html.Div(
                id="p4-fig42-explain-card",
                className="mt-2",
                children=_analysis_card(
                    explain_title_from_figures(
                        "fig_4_2_explain", "invest", "Figure 4.2 讲解"
                    ),
                    load_fig4_template("2", "invest"),
                    is_open=False,
                    md_slot_id="p4-fig42-explain-md",
                ),
            ),
            # 附录：4 张默认收起的长文档卡片（与其它讲解卡同一 _analysis_card 样式）
            _p4_appendix_cards(),
        ],
    )
