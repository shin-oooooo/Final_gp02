"""Dashboard pipeline execution — 高内聚管线执行模块。

替代 ``dash_ui_helpers._execute_pipeline_for_dashboard`` 中 130 行的五合一函数。
按职责拆分：

* :mod:`~.contracts`           — 数据契约（`SliderInputs` / `PipelineResult`）
* :mod:`~.policy_builder`      — 滑块原值 → 裁剪 → `DefensePolicyConfig`
* :mod:`~.sentiment_resolver`  — 解析情绪分（S_t）+ 详情
* :mod:`~.executor`            — API → 本地 → 无 detail 重试（三级降级）

对外 API 只暴露 :func:`execute_pipeline_for_dashboard`，外加类型定义。
"""

from __future__ import annotations

from dash_app.pipeline_exec.contracts import PipelineResult, SliderInputs
from dash_app.pipeline_exec.executor import execute_pipeline_for_dashboard
from dash_app.pipeline_exec.policy_builder import build_policy_from_sliders
from dash_app.pipeline_exec.sentiment_resolver import resolve_sentiment

__all__ = [
    "PipelineResult",
    "SliderInputs",
    "build_policy_from_sliders",
    "execute_pipeline_for_dashboard",
    "resolve_sentiment",
]
