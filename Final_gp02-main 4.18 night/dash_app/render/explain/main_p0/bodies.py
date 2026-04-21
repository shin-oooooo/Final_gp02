"""主栏 P0 静态 MD 常量 + 模式切换 getter。

**两组接口**：

* **常量**（启动时加载，提供初始渲染与向后兼容）：``ME_PHASE0_TAB_INTRO_BODY`` /
  ``P0_HEATMAP_BODY_MD`` / ``P0_BETA_CHEATSHEET_MD`` / ``P0_BETA_NONSTEADY_MD`` /
  ``P0_BETA_BY_CLASS_MD``。
* **getter**（运行时按 ``ui_mode`` 切换，读取 ``{basename}-{Inv|Res}.md`` 优先）：
  见 :func:`p0_heatmap_body` / :func:`p0_beta_cheatsheet` / :func:`p0_beta_nonsteady` /
  :func:`p0_beta_by_class`。

用法约定：
    # 新增 Res / Inv 差异化版本
    content/p0_heatmap_body-Res.md      # 研究模式专属
    content/p0_heatmap_body-Inv.md      # 投资模式专属
    content/p0_heatmap_body.md          # 共享兜底（两种模式都会退回到它）
"""

from __future__ import annotations

from dash_app.services.copy import get_md_text, get_md_text_by_mode


# ── 启动时加载的常量（初始渲染使用；后续若用户切模式会被 getter 覆盖）────────
ME_PHASE0_TAB_INTRO_BODY = get_md_text("sidebar_left/phase0_tab_intro.md", "")

P0_HEATMAP_BODY_MD = get_md_text("p0_heatmap_body.md", "")
P0_BETA_CHEATSHEET_MD = get_md_text("p0_beta_cheatsheet.md", "")
P0_BETA_NONSTEADY_MD = get_md_text("p0_beta_nonsteady.md", "")
P0_BETA_BY_CLASS_MD = get_md_text("p0_beta_by_class.md", "")


# ── 模式切换 getter（render/main_p0.py 按 state.ui_mode 调用）─────────────
def p0_heatmap_body(ui_mode: str) -> str:
    """P0 热力图卡片正文：按 ``ui_mode`` 返回对应 Markdown（Inv/Res 优先，否则 base）。"""
    return get_md_text_by_mode("p0_heatmap_body", ui_mode, P0_HEATMAP_BODY_MD)


def p0_beta_cheatsheet(ui_mode: str) -> str:
    """P0 Beta 含义速查。"""
    return get_md_text_by_mode("p0_beta_cheatsheet", ui_mode, P0_BETA_CHEATSHEET_MD)


def p0_beta_nonsteady(ui_mode: str) -> str:
    """P0 Beta 非稳态区间说明。"""
    return get_md_text_by_mode("p0_beta_nonsteady", ui_mode, P0_BETA_NONSTEADY_MD)


def p0_beta_by_class(ui_mode: str) -> str:
    """P0 各资产类分析。"""
    return get_md_text_by_mode("p0_beta_by_class", ui_mode, P0_BETA_BY_CLASS_MD)
