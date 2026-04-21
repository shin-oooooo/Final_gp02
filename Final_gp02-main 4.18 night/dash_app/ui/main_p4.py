"""Main panel layout for Phase 4.

**三张卡**（彼此独立）：
* **Fig 4.1a · 模型—模型应力预警有效性检验** — 搜索框 + 顶行预警日 banner
  + hero + Chart 1 + Part 2-5。
* **Fig 4.1b · 模型应力—市场载荷方向预警有效性检验** — 与 4.1a 对称，复用搜索。
* **独立结论卡**（``p4-fig41-conclusion``）— 仅展示情形 A / B，文案来自
  ``content-CHN/p4_conclusion_analysis.md``。

**槽位 id 列表**：
``p4-verify-search``（共用搜索，位于 4.1a 卡内）、
``p4-verify-hero`` / ``p4-fig41-jsd`` / ``p4-fig41-analysis-md``（4.1a）、
``p4-fig41b-verify-hero`` / ``p4-fig41b-jsd`` / ``p4-fig41b-analysis-md``（4.1b）、
``p4-fig41-conclusion``（独立结论）、
``p4-experiments-stack``（Fig 4.2）。
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import dcc, html

from dash_app.services.copy import get_app_label, get_figure_title
from dash_app.ui.layout import _figure_wrap, _placeholder_fig

# Chart 1 压窄：最大宽 720px，居中
_CHART1_STYLE = {
    "height": "260px",
    "maxWidth": "720px",
    "margin": "0 auto",
}


def _fig41_card(
    *,
    header_title: str,
    inner_label: str,
    hero_id: str,
    chart_id: str,
    analysis_id: str,
    search_block: object = None,
) -> dbc.Card:
    """一张 Fig4.1a / Fig4.1b 卡。结构完全对称，仅 id 与 search 块不同。"""
    # Part 1 Row：左 = 搜索框（若 search_block 非 None）；右 = 大跌提示 hero
    row_children: list = []
    if search_block is not None:
        row_children.append(dbc.Col(search_block, xs=12, md=4))
        hero_col_md = 8
    else:
        hero_col_md = 12
    row_children.append(dbc.Col(html.Div(id=hero_id), xs=12, md=hero_col_md))

    return dbc.Card(
        [
            dbc.CardHeader(header_title, className="py-2 small fw-bold"),
            dbc.CardBody(
                _figure_wrap(
                    0,
                    [
                        dbc.Row(
                            row_children,
                            className="g-2 align-items-stretch mb-2",
                        ),
                        dcc.Graph(
                            id=chart_id,
                            figure=_placeholder_fig("日收益"),
                            config={"displayModeBar": False},
                            style=_CHART1_STYLE,
                        ),
                        html.Div(
                            id=analysis_id,
                            className="mt-2 mb-0",
                        ),
                    ],
                    fig_label=inner_label,
                ),
                className="p-2",
            ),
        ],
        className="mb-2 border-secondary shadow-sm",
    )


def _build_search_block() -> html.Div:
    """共用的标的搜索框（搬自 P2：``dcc.Dropdown(searchable=True)``）。

    容器加个 label 提示；dropdown 的 options 由 ``callbacks/p2_symbol.py``
    在 ``symbols-store`` 变更时同步写入，value 沿用 p2 的选择机制。
    """
    return html.Div(
        [
            dbc.Label(
                get_app_label("p2_symbol_search_label", "标的（可搜索）"),
                className="small text-muted mb-1",
            ),
            dcc.Dropdown(
                id="p4-verify-search",
                clearable=False,
                searchable=True,
                placeholder=get_app_label("p2_symbol_search_placeholder", "搜索代码…"),
                className="text-center",
            ),
        ],
        className="py-2",
    )


def main_p4_panel() -> html.Div:
    """Phase 4 主栏：Fig 4.1a + Fig 4.1b + 独立结论 + Fig 4.2 实验栈。"""
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
    return html.Div(
        id="main-panel-p4",
        className="main-tab-panel",
        style={"display": "none"},
        children=[
            # Fig 4.1a（含共用搜索框）
            _fig41_card(
                header_title=cap41a_hdr,
                inner_label=cap41a_inner,
                hero_id="p4-verify-hero",
                chart_id="p4-fig41-jsd",
                analysis_id="p4-fig41-analysis-md",
                search_block=_build_search_block(),
            ),
            # Fig 4.1b（对称；不重复搜索）
            _fig41_card(
                header_title=cap41b_hdr,
                inner_label=cap41b_inner,
                hero_id="p4-fig41b-verify-hero",
                chart_id="p4-fig41b-jsd",
                analysis_id="p4-fig41b-analysis-md",
                search_block=None,
            ),
            # 独立结论卡
            html.Div(id="p4-fig41-conclusion", className="mb-2"),
            # Fig 4.2 实验栈
            html.Div(id="p4-experiments-stack", className="mt-2"),
        ],
    )
