"""研究模式溯源弹窗 — 指标 → 快照值 + 源码位置 + 文字说明。

对外 API（保持向后兼容，与原 ``dash_app.research_tracing`` 完全一致）：

* :class:`CodeRef`, :class:`TraceItem`, :class:`TraceModalSections`  — 数据模型
* :func:`list_traces`              — 按 key 列表拉取 TraceItem
* :func:`load_code_excerpt`        — 读取源码片段（带行号）
* :func:`snapshot_value_excerpt`   — 从快照摘取该 key 的原始值
* :func:`get_trace_modal_sections` — 组装完整弹窗的四个段落
"""

from __future__ import annotations

from dash_app.features.research_trace.code import (
    load_code_excerpt,
    snapshot_value_excerpt,
)
from dash_app.features.research_trace.modal import get_trace_modal_sections
from dash_app.features.research_trace.models import (
    CodeRef,
    TraceItem,
    TraceModalSections,
    list_traces,
)

__all__ = [
    "CodeRef",
    "TraceItem",
    "TraceModalSections",
    "list_traces",
    "load_code_excerpt",
    "snapshot_value_excerpt",
    "get_trace_modal_sections",
]
