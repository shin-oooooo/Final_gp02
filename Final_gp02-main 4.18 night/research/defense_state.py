"""Single source of truth for DefenseLevel (state_bit)."""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Dict, Iterable, Optional

from research.schemas import DefensePolicyConfig


def diagnostic_failed_adf(d: Any) -> bool:
    """训练窗对数收益 ADF 管线未给出「平稳且逻辑闭环」：未过关。"""
    if isinstance(d, dict):
        sr = bool(d.get("stationary_returns"))
        blf = bool(d.get("basic_logic_failure"))
    else:
        sr = bool(getattr(d, "stationary_returns", False))
        blf = bool(getattr(d, "basic_logic_failure", False))
    return not (sr and not blf)


def any_adf_asset_failure(diagnostics: Optional[Iterable[Any]]) -> bool:
    if not diagnostics:
        return False
    return any(diagnostic_failed_adf(d) for d in diagnostics)


class DefenseLevel(IntEnum):
    STANDARD = 0
    CAUTION = 1
    MELTDOWN = 2


def resolve_defense_level(
    *,
    consistency: float,
    sentiment: float,
    h_struct: float,
    adf_asset_failure: bool,
    jsd_stress: bool,
    policy: DefensePolicyConfig,
    prob_full_pipeline_failure: bool = False,
    semantic_numeric_divergence: bool = False,
) -> DefenseLevel:
    """
    Level 2（熔断）触发条件（满足任一即触发）：
      ① 一致性 ≤ τ_L2；
      ② 语义–数值滚动余弦 < 0（`semantic_numeric_divergence`）；
      ③ JSD 动态应力（`jsd_stress`）。

    Level 1（警戒）触发条件（满足任一即触发，不满足 Level 2）：
      存在标的 ADF 未过关 / 结构熵低 / 概率全失效 / 一致性区间 / 情绪过低。

    `sentiment`：管线传入 **min(S_t)**（测试窗情绪序列最小值；无序列时为标量回退）。
    """
    t = policy
    if consistency <= t.tau_l2 or semantic_numeric_divergence or jsd_stress:
        return DefenseLevel.MELTDOWN
    if (
        adf_asset_failure
        or h_struct < t.tau_h1
        or prob_full_pipeline_failure
        or (t.tau_l2 < consistency <= t.tau_l1)
        or (consistency > t.tau_l1 and sentiment < t.tau_s_low)
    ):
        return DefenseLevel.CAUTION
    if consistency > t.tau_l1 and t.tau_s_low <= sentiment <= t.tau_s_high:
        return DefenseLevel.STANDARD
    return DefenseLevel.CAUTION


def defense_level_to_dict(level: DefenseLevel) -> Dict[str, Any]:
    return {"level": int(level), "label": {0: "Level 0 Standard", 1: "Level 1 Caution", 2: "Level 2 Melt-down"}.get(int(level), "Unknown")}
