"""Research trace — 数据契约 + 静态 TraceItem 注册表。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class CodeRef:
    """源码引用：相对 repo root 的路径 + 行号区间（1-indexed, 闭区间）。"""

    path: str
    start: int
    end: int


@dataclass(frozen=True)
class TraceItem:
    """一个研究 trace 条目：key + 显示标题 + 原理说明 + 相关源码段。"""

    key: str
    title: str
    why_md: str
    code: Tuple[CodeRef, ...] = ()


@dataclass(frozen=True)
class TraceModalSections:
    """研究溯源弹窗的结构化四段：

    * ``result_raw``   结果值 + 原始数据链路
    * ``calculation``  计算过程（叙事）
    * ``params_raw``   涉及的策略参数（与 ``defense_policy`` 对齐）
    * ``learning``     训练/学习环节（若有）
    * ``code``         源码位置
    """

    result_raw: str
    calculation: str
    params_raw: str
    learning: str
    code: Tuple[CodeRef, ...]


_TRACE: Dict[str, TraceItem] = {
    "p2_credibility": TraceItem(
        key="p2_credibility",
        title="可信度评分（credibility_score）",
        why_md=(
            "来自 Phase 2：基准项 `1/(1+α·JSD_triangle)`，若密度覆盖率相对 Naive 更差则追加惩罚，"
            "最后 clip 到侧栏上下界。"
        ),
        code=(
            CodeRef("research/phase2.py", 654, 717),
        ),
    ),
    "p2_shadow_mse": TraceItem(
        key="p2_shadow_mse",
        title="影子验证 MSE / best_model_per_symbol",
        why_md="训练窗末尾留出 `shadow_holdout_days`（侧栏可调）个交易日做伪样本外，用于择模与像素矩阵；不读取测试窗标签。",
        code=(
            CodeRef("research/phase2.py", 175, 249),
            CodeRef("research/phase2.py", 670, 712),
        ),
    ),
    "p2_prob_tests": TraceItem(
        key="p2_prob_tests",
        title="样本外概率检验（NLL / DM / 覆盖率）",
        why_md="对各模型 OOS 预测按高斯 NLL 评分，并对 Naive 做 DM(HAC) 检验，同时计算名义 95% 区间覆盖率。",
        code=(
            CodeRef("research/phase2.py", 252, 376),
            CodeRef("research/phase2.py", 626, 651),
        ),
    ),
    "st_series": TraceItem(
        key="st_series",
        title="测试窗情绪路径 S_t（分段累积）",
        why_md="当 sentiment_detail 可用时，按测试窗交易日对齐并构造 S_t 序列；用于 Phase 2 的语义-数值余弦与 Phase 3 的展示。",
        code=(
            CodeRef("research/pipeline.py", 142, 190),
        ),
    ),
    "windows": TraceItem(
        key="windows",
        title="训练/测试时间窗解析（resolved_windows）",
        why_md="运行时根据 data.json 交易日索引与（可选）新闻跨度动态解析训练/测试窗，并写入 phase0.meta.resolved_windows。",
        code=(
            CodeRef("research/pipeline.py", 142, 167),
        ),
    ),
}


def list_traces(keys: List[str]) -> List[TraceItem]:
    """根据 key 列表返回 TraceItem；未知 key 被静默跳过。"""
    return [t for k in keys if (t := _TRACE.get(k)) is not None]


def get_trace(key: str) -> TraceItem | None:
    """单个 key 查表；不存在返回 None。供 :mod:`modal` 内部使用。"""
    return _TRACE.get(key)
