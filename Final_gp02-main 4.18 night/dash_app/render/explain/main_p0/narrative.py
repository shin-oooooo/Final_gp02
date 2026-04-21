"""主栏 P0 动态叙事：Phase 0 Tab 介绍 + 逻辑说明。"""

from __future__ import annotations

from typing import Any, Dict

from dash_app.render.explain.main_p0.bodies import ME_PHASE0_TAB_INTRO_BODY


def me_phase0_intro_md(train_start: str, train_end: str, test_start: str, test_end: str) -> str:
    """Phase 0 tab Introduction: 前提与资产表 + 解析后时间窗；项目综述正文在侧栏。"""
    return (
        ME_PHASE0_TAB_INTRO_BODY
        + "\n\n**3. 时间窗口划分**\n\n"
        + f"- **训练集**：{train_start} 至 {train_end}\n"
        + f"- **测试集**：{test_start} 至 {test_end}"
        + "\n\n测试集终点由**两个因素共同决定**：① 新闻抓取（Crawl4AI / RSS）可覆盖的最新日期；② 运行当日日历日（`today_iso()`）。"
        + "管线在 `research/windowing.py` 中对两者取交集并与 `data.json` 交易日索引对齐，得到最终 `resolved_windows.test_end`。"
        + "若新闻尚未覆盖当日，测试窗自动向前收缩至最新新闻日期。\n"
    ).strip()


def about_phase0_logic(p0: Dict[str, Any], env: Dict[str, Any]) -> str:
    """UI.md About_Phase0_Logic：相关性过高与测试窗过短的提示。"""
    parts: list[str] = []
    o = env.get("orthogonality_check") or {}
    if bool(o.get("warning")) and "削弱" in str(o.get("message", "")):
        parts.append(
            "**警告**：训练期内科技组与避险组相关性偏高，对冲正交性不足，"
            "Phase 3 基于分散化的防御叙事可能被削弱；建议调整 Universe 或对照解读。"
        )
    n_test = len(p0.get("test_index") or [])
    if n_test > 0 and n_test < 15:
        parts.append(
            f"**建议**：当前测试集仅约 {n_test} 个交易日，可能不足以稳定观察 4 月初断裂期的模型—语义背离；"
            "若数据允许，可延长测试窗至包含完整波动段。"
        )
    if not parts:
        return "当前 Phase 0 配置下，组间相关预警未触发，测试窗长度可接受。"
    return " ".join(parts)
