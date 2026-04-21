"""Main panel layout for Phase 3 (adaptive optimization, dual-track MC)."""

from __future__ import annotations

from dash import dcc, html

from dash_app.render.explain import (
    p3_section_31_adaptive,
    p3_section_32_dual_mc,
)
from dash_app.ui.layout import (
    _analysis_card,
    _figure_wrap,
    _placeholder_fig,
    explain_title_from_figures,
)
from dash_app.services.copy import get_app_label, get_figure_title, get_md_text


def main_p3_panel() -> html.Div:
    """Return the full main-panel-p3 layout。

    结构（每张图都是 *图表 + 讲解卡* 成组；与 Fig2.x / Fig3.3 同一范式）：

    * objective-banner → 目标优化状态横幅。
    * Fig3.1 → ``fig-p3-best-table`` + ``p3-fig31-explain-card``（宽度 12）。
    * Fig3.2 → ``fig-p3-weights``（保留原样，暂无讲解卡）。
    * Fig3.3 → ``fig-p3-mc`` + ``p3-fig33-explain-card``。

    讲解卡容器（``*-explain-card``）的内容由
    ``callbacks/research_panels.py::_caption_refresh_on_mode`` 在模式 / 语言
    切换时覆盖，标题统一从 ``figures_titles.md`` 的 ``fig_X_Y_explain`` /
    ``fig_X_Y_explain_res`` 读取，正文从 ``content-{LANG}/Inv/Fig3.x-Inv.md``
    或 ``content-{LANG}/Res-templates/Fig3.x-Res.md`` 加载。
    """
    return html.Div(
        id="main-panel-p3",
        className="main-tab-panel",
        style={"display": "none"},
        children=[
            html.Div(id="objective-banner", className="mt-2"),
            html.P(
                get_app_label(
                    "p3_st_reuse_note",
                    "测试窗 S_t 与侧栏 FigX.1 同源；影子择模结果已移至 Phase 2 顶部展示。",
                ),
                className="small text-muted mb-2",
            ),
            _figure_wrap(
                0,
                [
                    dcc.Graph(
                        id="fig-p3-best-table",
                        figure=_placeholder_fig(),
                        config={"displayModeBar": False},
                        style={"height": "220px"},
                        className="mb-2",
                    ),
                    # Mode-aware container: updated by `_caption_refresh_on_mode` callback。
                    # 标题走 figures_titles.md ``fig_3_1_explain`` / ``..._res``；
                    # 正文来自 ``content-{LANG}/Inv/Fig3.1-Inv.md`` 或
                    # ``content-{LANG}/Res-templates/Fig3.1-Res.md``。
                    html.Div(
                        id="p3-fig31-explain-card",
                        children=_analysis_card(
                            explain_title_from_figures(
                                "fig_3_1_explain", "invest", "Figure 3.1 讲解"
                            ),
                            p3_section_31_adaptive("invest"),
                            md_slot_id="p3-fig31-explain-md",
                        ),
                    ),
                ],
                fig_label=get_figure_title(
                    "fig_3_1", "Figure 3.1 · 各标的最佳模型收益期望与波动预测"
                ),
            ),
            _figure_wrap(
                1,
                [
                    dcc.Graph(
                        id="fig-p3-weights",
                        figure=_placeholder_fig(),
                    ),
                ],
                fig_label=get_figure_title(
                    "fig_3_2", "Figure 3.2 · 优化权重与自定义权重对比"
                ),
            ),
            _figure_wrap(
                2,
                [
                    dcc.Graph(
                        id="fig-p3-mc",
                        figure=_placeholder_fig(),
                    ),
                    # Mode-aware container: updated by `_caption_refresh_on_mode` callback。
                    # 标题统一从 figures_titles.md 的 ``fig_3_3_explain`` / ``..._res`` 读取，
                    # 正文从 ``content-{LANG}/Inv/Fig3.3-Inv.md`` / ``Res-templates/Fig3.3-Res.md`` 加载。
                    html.Div(
                        id="p3-fig33-explain-card",
                        children=_analysis_card(
                            explain_title_from_figures(
                                "fig_3_3_explain", "invest", "Figure 3.3 讲解"
                            ),
                            p3_section_32_dual_mc("invest"),
                            md_slot_id="p3-fig33-explain-md",
                        ),
                    ),
                    # 投资模式专属：双轨蒙特卡洛模拟细节卡（内容来自 Fig3.3-Inv_2.md）。
                    # 研究模式下由 ``_caption_refresh_on_mode`` 覆盖为空 Div。
                    html.Div(
                        id="p3-fig33-explain-card-2",
                        children=_analysis_card(
                            "双轨蒙特卡洛模拟",
                            get_md_text("Inv/Fig3.3-Inv_2.md", ""),
                            md_slot_id="p3-fig33-explain-md-2",
                        ),
                    ),
                ],
                fig_label=get_figure_title(
                    "fig_3_3", "Figure 3.3 · 双轨蒙特卡洛模拟"
                ),
            ),
            html.Div(id="card-p3"),
        ],
    )
