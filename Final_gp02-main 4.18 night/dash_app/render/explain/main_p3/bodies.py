"""主栏 P3 静态 MD 常量 + 模式切换 getter。"""

from __future__ import annotations

from typing import List

from dash_app.services.copy import get_md_text, get_md_text_by_mode


ME_PHASE3_INTRO = get_md_text("phase3_intro.md", "")
P3_SECTION_31_ADAPTIVE_MD = get_md_text("p3_adaptive_optimizer.md", "")
P3_SECTION_32_DUAL_MC_MD = get_md_text("p3_dual_mc.md", "")


def p3_section_31_adaptive(ui_mode: str) -> str:
    """AdaptiveOptimizer 与三阶段防御（Figure3.2 左侧介绍卡）。"""
    return get_md_text_by_mode("p3_adaptive_optimizer", ui_mode, P3_SECTION_31_ADAPTIVE_MD)


def p3_section_32_dual_mc(ui_mode: str) -> str:
    """Figure3.3 讲解：双轨蒙特卡洛（兼容旧入口；返回首张卡片正文）。"""
    return get_md_text_by_mode("p3_dual_mc", ui_mode, P3_SECTION_32_DUAL_MC_MD)


def p3_section_31_table_md(ui_mode: str) -> str:
    """Figure3.1 讲解：各标的最佳模型 μ̂/σ̂ 表（按模式取 Inv/ 或 Res/ 子目录）。"""
    mode = (ui_mode or "invest").strip().lower()
    if mode == "research":
        return get_md_text("Res-templates/Fig3.1-Res.md", "")
    return get_md_text("Inv/Fig3.1-Inv.md", "")


def p3_section_32_dual_mc_md_list(ui_mode: str) -> List[str]:
    """Figure3.3 讲解卡 MD 列表：投资模式 2 张、研究模式 1 张。

    Returns:
        List of markdown bodies. The caller wraps each into an analysis card.
    """
    mode = (ui_mode or "invest").strip().lower()
    if mode == "research":
        body = get_md_text("Res-templates/Fig3.3-Res.md", "")
        return [body] if body else []
    body1 = get_md_text("Inv/Fig3.3-Inv.md", "")
    body2 = get_md_text("Inv/Fig3.3-Inv_2.md", "")
    return [b for b in (body1, body2) if b]
