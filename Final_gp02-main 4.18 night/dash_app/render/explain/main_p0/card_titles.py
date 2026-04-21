"""主栏 P0 两个卡片的动态标题。"""

from __future__ import annotations

from typing import Any, Dict


def p0_heatmap_card_title(env: Dict[str, Any]) -> str:
    """热力图卡片标题。极端：正交性预警时替换为削弱版文案。"""
    o = env.get("orthogonality_check") or {}
    if bool(o.get("warning")) and "削弱" in str(o.get("message", "")):
        return "结论：组间正交性不足——对冲叙事在常态下需对照解读。"
    return "结论：对冲在常态下是有效的——实验的逻辑起点成立。"


def p0_beta_card_title(defense_level: int) -> str:
    """Beta 区首条结论标题。Level ≥ 2 时替换为更严峻的表述。"""
    if defense_level >= 2:
        return "结论：尾部风险显性化——结构性断裂与防御目标已切换。"
    return "结论：市场正在经历结构性断裂，而非普通波动。"
