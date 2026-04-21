"""主栏 P2 静态 MD 常量 + 模式切换 getter。

Figure2.1 / Figure2.2 讲解卡正文统一改读 ``content-{LANG}/Inv/Fig2.x-Inv.md`` 与
``content-{LANG}/Res-templates/Fig2.x-Res.md``，与侧栏 FigX 走同一套约定。
"""

from __future__ import annotations

from dash_app.render.explain._loaders import load_main_template
from dash_app.services.copy import get_md_text


ME_PHASE2_INTRO = get_md_text("sidebar_left/phase2_intro.md", "")

# 启动时加载 Inv 版本作为初始渲染；模式切换由对应 getter 负责。
P2_PIXEL_SHADOW_INTRO_MD = load_main_template(2, 1, "invest")
P2_FIG21_INTRO_MD = load_main_template(2, 2, "invest")


def p2_pixel_shadow_intro(ui_mode: str) -> str:
    """Figure2.1 讲解：影子择模与像素矩阵。"""
    return load_main_template(2, 1, ui_mode)


def p2_fig21_intro(ui_mode: str) -> str:
    """Figure2.2 讲解：时间×收益密度（函数名沿用历史，实际对应 Fig2.2）。"""
    return load_main_template(2, 2, ui_mode)
