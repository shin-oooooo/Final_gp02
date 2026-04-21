"""主栏 P2 静态 MD 常量 + 模式切换 getter。"""

from __future__ import annotations

from dash_app.services.copy import get_md_text, get_md_text_by_mode


ME_PHASE2_INTRO = get_md_text("sidebar_left/phase2_intro.md", "")
P2_PIXEL_SHADOW_INTRO_MD = get_md_text("p2_pixel_shadow_intro.md", "")
P2_FIG21_INTRO_MD = get_md_text("p2_fig21_intro.md", "")


def p2_pixel_shadow_intro(ui_mode: str) -> str:
    """Figure2.1 讲解：影子择模与像素矩阵。"""
    return get_md_text_by_mode("p2_pixel_shadow_intro", ui_mode, P2_PIXEL_SHADOW_INTRO_MD)


def p2_fig21_intro(ui_mode: str) -> str:
    """Figure2.2 讲解：时间×收益密度。"""
    return get_md_text_by_mode("p2_fig21_intro", ui_mode, P2_FIG21_INTRO_MD)
