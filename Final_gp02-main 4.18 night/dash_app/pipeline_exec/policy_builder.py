"""滑块原值 → `DefensePolicyConfig`（纯函数，带裁剪 + 断言 + 日志）。

原 ``_execute_pipeline_for_dashboard`` 前半段 45 行散落的 clamp 逻辑在这里
拆成 5 个单职责小函数 + 1 个组装函数。每个 clamp 子函数都可以独立单测：

    >>> _clamp_int_default(None, 1, 60, dflt=10)
    10
    >>> _clamp_int_default("abc", 1, 60, dflt=10)
    10
    >>> _clamp_int_default(999, 1, 60, dflt=10)
    60

调试最小用例：

    >>> from dash_app.pipeline_exec import build_policy_from_sliders, SliderInputs
    >>> pol = build_policy_from_sliders(SliderInputs(
    ...     tau_l2=0.45, tau_l1=0.7, tau_h1=0.5, tau_vol=None, tau_ac1=None,
    ...     k_jsd=2.0, jsd_baseline_eps_log=-9.0, cred_jsd_base=6.0,
    ...     cred_jsd_pen=0.12, cred_pen_cap=0.35, cred_min=-0.5, cred_max=1.0,
    ...     lam=0.5, semantic_cos_window=5, oos_steps=10, shadow_alpha_mse=0.5,
    ...     shadow_holdout_days=40,
    ...     verify_train_tail_days=60, verify_crash_q=90, verify_std_q=90,
    ...     verify_tail_q=90,
    ... ))
    >>> pol.tau_l2
    0.45
"""

from __future__ import annotations

import logging
import math
from typing import Any, Optional

from dash_app.pipeline_exec.contracts import SliderInputs, pipeline_exec_debug_enabled

logger = logging.getLogger("dash_app.pipeline_exec.policy_builder")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if pipeline_exec_debug_enabled():
        try:
            text = msg % args if args else msg
            print(f"[policy_builder] {text}", flush=True)
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# 低层 clamp 助手（纯函数 + 断言）                                              #
# --------------------------------------------------------------------------- #


def _clamp_int_default(x: Any, lo: int, hi: int, *, dflt: int) -> int:
    """任意输入 → [lo, hi] 范围内的 int；失败回退到 dflt。"""
    assert lo <= hi, f"lo>hi: {lo} > {hi}"
    assert lo <= dflt <= hi, f"default {dflt} outside [{lo}, {hi}]"

    try:
        v = int(x)
    except (TypeError, ValueError):
        v = dflt
    return max(lo, min(hi, v))


def _clamp_float_default(x: Any, lo: float, hi: float, *, dflt: float) -> float:
    """任意输入 → [lo, hi] 范围内的 float；失败或非有限回退到 dflt。"""
    assert lo <= hi, f"lo>hi: {lo} > {hi}"
    assert lo <= dflt <= hi, f"default {dflt} outside [{lo}, {hi}]"

    try:
        v = float(x)
    except (TypeError, ValueError):
        v = dflt
    if not math.isfinite(v):
        v = dflt
    return max(lo, min(hi, v))


def _resolve_credibility_range(raw_min: Any, raw_max: Any) -> tuple[float, float]:
    """解决可信度上下界：若 min ≥ max，回退到默认值 (-0.5, 1.0)。"""
    try:
        cmin = float(raw_min) if raw_min is not None else -0.5
    except (TypeError, ValueError):
        cmin = -0.5
    try:
        cmax = float(raw_max) if raw_max is not None else 1.0
    except (TypeError, ValueError):
        cmax = 1.0

    if cmin >= cmax:
        _trace("credibility range invalid (min=%s >= max=%s), using defaults", cmin, cmax)
        cmin, cmax = -0.5, 1.0
    return cmin, cmax


def _resolve_jsd_baseline_eps(raw_log: Any) -> float:
    """log10(ε) 滑块值 → 实际 ε（限制在 [1e-15, 1e-2]）。"""
    try:
        lg = float(raw_log)
    except (TypeError, ValueError):
        lg = -9.0
    if not math.isfinite(lg):
        lg = -9.0
    lg = max(-12.0, min(-3.0, lg))
    eps = min(0.01, max(1e-15, 10 ** lg))
    return float(eps)


def _resolve_or_default_float(x: Any, dflt: float) -> float:
    """Truthy-or-default：`None` / 0 / NaN 回退到 dflt（保留原函数 `or` 语义）。"""
    if x is None:
        return dflt
    try:
        v = float(x)
    except (TypeError, ValueError):
        return dflt
    if not math.isfinite(v) or v == 0:
        return dflt
    return v


# --------------------------------------------------------------------------- #
# 主入口                                                                       #
# --------------------------------------------------------------------------- #


def build_policy_from_sliders(inputs: SliderInputs) -> Any:
    """把 :class:`SliderInputs` 全部裁剪好 → 构造 `DefensePolicyConfig`。

    **纯函数**：不修改 inputs；每次返回新的 policy 实例。

    Args:
        inputs: 从前端采集的 23 个滑块原值（可能含 None / NaN / str）。

    Returns:
        合法的 :class:`research.schemas.DefensePolicyConfig` 实例。
    """
    from research.schemas import DefensePolicyConfig  # 惰性 import 避循环

    assert isinstance(inputs, SliderInputs), (
        f"inputs must be SliderInputs, got {type(inputs).__name__}"
    )

    # --- 分组 clamp ---
    oos = _clamp_int_default(inputs.oos_steps, 1, 60, dflt=10)
    shd = _clamp_int_default(inputs.shadow_holdout_days, 5, 120, dflt=40)
    v_train = _clamp_int_default(inputs.verify_train_tail_days, 20, 260, dflt=60)
    v_crash = _clamp_int_default(inputs.verify_crash_q, 50, 99, dflt=90)
    v_std = _clamp_int_default(inputs.verify_std_q, 50, 99, dflt=90)
    v_tail = _clamp_int_default(inputs.verify_tail_q, 50, 99, dflt=90)
    sem_cos = _clamp_int_default(inputs.semantic_cos_window, 1, 10, dflt=5)

    alpha_sel = _clamp_float_default(inputs.shadow_alpha_mse, 0.0, 1.0, dflt=0.5)

    cmin, cmax = _resolve_credibility_range(inputs.cred_min, inputs.cred_max)
    eps = _resolve_jsd_baseline_eps(inputs.jsd_baseline_eps_log)

    _trace(
        "clamps: oos=%d shd=%d v_train=%d v_crash=%d v_std=%d v_tail=%d "
        "sem_cos=%d alpha=%.3f cmin=%s cmax=%s eps=%.2e",
        oos, shd, v_train, v_crash, v_std, v_tail,
        sem_cos, alpha_sel, cmin, cmax, eps,
    )

    # 防御性 clamp：Pydantic 对 credibility 三项有 gt/ge=0 约束，NaN 会抛 ValidationError
    cred_base = _clamp_float_default(inputs.cred_jsd_base, 0.01, 100.0, dflt=6.0)
    cred_pen = _clamp_float_default(inputs.cred_jsd_pen, 0.0, 10.0, dflt=0.12)
    cred_cap = _clamp_float_default(inputs.cred_pen_cap, 0.0, 10.0, dflt=0.35)
    tau_vol = _clamp_float_default(inputs.tau_vol, 0.0, 5.0, dflt=0.32)
    tau_ac1 = _clamp_float_default(inputs.tau_ac1, -1.0, 1.0, dflt=-0.08)

    policy = DefensePolicyConfig(
        tau_l2=_resolve_or_default_float(inputs.tau_l2, 0.45),
        tau_l1=_resolve_or_default_float(inputs.tau_l1, 0.70),
        tau_h1=_resolve_or_default_float(inputs.tau_h1, 0.50),
        tau_vol_melt=tau_vol,
        tau_return_ac1=tau_ac1,
        semantic_cosine_window=sem_cos,
        verify_train_tail_days=v_train,
        verify_crash_quantile_pct=v_crash,
        verify_std_quantile_pct=v_std,
        verify_tail_quantile_pct=v_tail,
        k_jsd=_resolve_or_default_float(inputs.k_jsd, 2.0),
        jsd_baseline_eps=eps,
        credibility_baseline_jsd_scale=cred_base,
        credibility_penalty_jsd_scale=cred_pen,
        credibility_penalty_cap=cred_cap,
        credibility_score_min=cmin,
        credibility_score_max=cmax,
        lambda_semantic=_resolve_or_default_float(inputs.lam, 0.5),
        alpha_model_select=alpha_sel,
        shadow_holdout_days=shd,
        oos_fit_steps=oos,
        # `data_refresh_max_age_hours` / `data_auto_refresh` 随 R1.10 退役：UI
        # 不再暴露这两个字段，全部走 Pydantic schema 的默认值（18h / False）。
    )
    _trace("policy built: tau_l2=%.3f tau_l1=%.3f k_jsd=%.2f alpha=%.3f",
           policy.tau_l2, policy.tau_l1, policy.k_jsd, policy.alpha_model_select)
    return policy
