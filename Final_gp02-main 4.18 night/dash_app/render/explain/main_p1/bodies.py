"""主栏 P1 静态 MD 常量 + 模式切换 getter。"""

from __future__ import annotations

from dash_app.services.copy import get_md_text, get_md_text_by_mode


ME_PHASE1_INTRO = get_md_text("sidebar_left/phase1_intro.md", "")
P1_STAT_METHOD_MD = get_md_text("p1_stat_method.md", "")


def p1_stat_method(ui_mode: str) -> str:
    """Figure1.1 讲解：ADF / Ljung-Box / P 值含义。"""
    return get_md_text_by_mode("p1_stat_method", ui_mode, P1_STAT_METHOD_MD)
