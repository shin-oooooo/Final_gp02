"""主栏 P3 静态 MD 常量 + 模式切换 getter。

Figure3.x 讲解卡正文统一改读 ``content-{LANG}/Inv/Fig3.x-Inv.md`` 与
``content-{LANG}/Res-templates/Fig3.x-Res.md``，与侧栏 FigX 走同一套约定。
``p3_adaptive_optimizer.md`` / ``p3_dual_mc.md`` 这两份历史 root-level 文件
已不再被运行时读取（如需后续完全清理，可单独走文件清理 PR）。
"""

from __future__ import annotations

from typing import List

from dash_app.render.explain._loaders import load_main_template
from dash_app.services.copy import get_md_text


ME_PHASE3_INTRO = get_md_text("phase3_intro.md", "")

# 启动时加载 Inv 版本作为初始渲染；模式切换由对应 getter 负责。
P3_SECTION_31_ADAPTIVE_MD = load_main_template(3, 1, "invest")
P3_SECTION_32_DUAL_MC_MD = load_main_template(3, 3, "invest")


def p3_section_31_adaptive(ui_mode: str) -> str:
    """AdaptiveOptimizer 与三阶段防御（Figure3.1 介绍卡）。"""
    return load_main_template(3, 1, ui_mode)


def p3_section_32_dual_mc(ui_mode: str) -> str:
    """Figure3.3 讲解：双轨蒙特卡洛（单卡正文）。"""
    return load_main_template(3, 3, ui_mode)


def p3_section_31_table_md(ui_mode: str) -> str:
    """Figure3.1 讲解：各标的最佳模型 μ̂/σ̂ 表（旧入口，与 31_adaptive 同源）。"""
    return load_main_template(3, 1, ui_mode)


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
