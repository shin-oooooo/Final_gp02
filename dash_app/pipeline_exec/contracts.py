"""Pipeline-execution 数据契约（冻结 dataclass；纯数据无行为）。

关键：`SliderInputs` 里所有字段都是 ``Any`` — 它们是**未经裁剪的前端原值**，
可能是 None、数值、字符串或者 NaN。只有通过 :mod:`policy_builder` 才会被
裁剪为合法范围内的 float/int。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def pipeline_exec_debug_enabled() -> bool:
    """是否在管线执行路径上打印调试输出。

    **必须在调用时读取** ``DEBUG_PIPELINE_EXEC``：若在模块顶层缓存布尔值，
    Dash/Flask debug 重载子进程或导入顺序会导致「已设环境变量却无 print」。
    """
    v = (os.environ.get("DEBUG_PIPELINE_EXEC") or "0").strip().lower()
    return v not in ("", "0", "false")


@dataclass(frozen=True)
class SliderInputs:
    """左侧参数栏所有滑块/输入的**原始**值（可 None / NaN / str）。

    23 个字段完全对应原 ``_execute_pipeline_for_dashboard`` 函数的 23 个
    以 slider 为源的参数。拆成单一结构体后：

    * 方便单元测试（传入 dict 就能构造）；
    * 方便日志化（一行 dump 全部参数）；
    * 不再需要 23 个位置参数层层传递。
    """

    tau_l2: Any
    tau_l1: Any
    tau_h1: Any
    tau_vol: Any
    tau_ac1: Any
    k_jsd: Any
    jsd_baseline_eps_log: Any
    cred_jsd_base: Any
    cred_jsd_pen: Any
    cred_pen_cap: Any
    cred_min: Any
    cred_max: Any
    lam: Any
    semantic_cos_window: Any
    oos_steps: Any
    shadow_alpha_mse: Any
    shadow_holdout_days: Any
    # data_max_age / auto_refresh 字段随 R1.10 已退役（UI 控件不存在）。字段保
    # 留为默认 None 的键入口，如未来要恢复 auto-refresh 控件只需恢复赋值即可。
    verify_train_tail_days: Any
    verify_crash_q: Any
    verify_std_q: Any
    verify_tail_q: Any


@dataclass(frozen=True)
class PipelineResult:
    """管线执行最终返回结果（替代原来的 5 元组）。"""

    policy: Any                              # DefensePolicyConfig (避免循环 import)
    snap_json: Dict[str, Any]
    symbols: List[str]
    api_err: Optional[str]
    sentiment_score: float

    def to_tuple(self):
        """兼容旧 5 元组返回（dashboard_pipeline.py 调用方期望顺序）。"""
        return (
            self.policy,
            self.snap_json,
            self.symbols,
            self.api_err,
            self.sentiment_score,
        )
