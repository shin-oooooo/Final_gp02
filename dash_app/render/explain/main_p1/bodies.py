"""主栏 P1 静态 MD 常量 + 模式切换 getter。

Figure1.1 讲解卡正文统一改读 ``content-{LANG}/Inv/Fig1.1-Inv.md`` 与
``content-{LANG}/Res-templates/Fig1.1-Res.md``，与侧栏 FigX 走同一套约定。
保留 ``P1_STAT_METHOD_MD`` 常量以兼容历史导入；它现在加载 invest 模式的初始正文。
"""

from __future__ import annotations

from dash_app.render.explain._loaders import load_main_template
from dash_app.services.copy import get_md_text


ME_PHASE1_INTRO = get_md_text("sidebar_left/phase1_intro.md", "")

# 启动时加载 Inv 版本作为初始渲染；模式切换由 :func:`p1_stat_method` 负责。
P1_STAT_METHOD_MD = load_main_template(1, 1, "invest")


def p1_stat_method(ui_mode: str) -> str:
    """Figure1.1 讲解：ADF / Ljung-Box / P 值含义。"""
    return load_main_template(1, 1, ui_mode)
