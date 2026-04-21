"""Fig4.1 数据抽取 — 从 ``snap_json`` 解析为 :class:`Fig41Bundle`。

所有函数都是**纯函数**：

* 入口做 ``assert`` 类型与必要字段检查；
* 关键分支与循环入口处用 ``logger.debug`` 或 ``print`` 输出核心变量；
* 不修改传入的任何对象；

调试最小可运行案例：

    >>> import json
    >>> from research.schemas import DefensePolicyConfig
    >>> from dash_app.fig41.extract import extract_fig41_bundle
    >>> snap = json.load(open("data.json", encoding="utf-8"))
    >>> bundle = extract_fig41_bundle(snap, DefensePolicyConfig())
    >>> bundle.has_post, bundle.focus_symbol, bundle.hits.verdict
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from dash_app.fig41.contracts import (
    Fig41Baselines,
    Fig41Bundle,
    Fig41DualVerdict,
    Fig41Hits,
    Fig41PostAlarm,
)

logger = logging.getLogger("dash_app.fig41.extract")

# 通过环境变量 DEBUG_FIG41=1 打开逐步输出（肉眼观测）
_TRACE = os.environ.get("DEBUG_FIG41", "0").strip() not in ("", "0", "false", "False")


def _trace(msg: str, *args: Any) -> None:
    """内部日志：DEBUG 级 + 可选 stdout（便于 Dash 终端直观观察）。"""
    logger.debug(msg, *args)
    if _TRACE:
        try:
            print(f"[fig41.extract] {msg % args}" if args else f"[fig41.extract] {msg}")
        except Exception:
            # 打印失败不能中断管线
            pass


# --------------------------------------------------------------------------- #
# 低层助手                                                                     #
# --------------------------------------------------------------------------- #


def _as_opt_float(v: Any) -> Optional[float]:
    """转为 float，None / 非数 / NaN 返回 None。"""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN check（避免依赖 math）
        return None
    return f


def _safe_dict(v: Any) -> Dict[str, Any]:
    """任何输入 → dict（非 dict 返回空 dict）。"""
    return v if isinstance(v, dict) else {}


def _safe_list(v: Any) -> List[Any]:
    """任何输入 → list（非 list 返回空 list）。"""
    return list(v) if isinstance(v, list) else []


# --------------------------------------------------------------------------- #
# 分步抽取（每个子函数只做一件事）                                              #
# --------------------------------------------------------------------------- #


def _extract_fig41_verify(
    snap_json: Dict[str, Any],
    verify_key: str = "fig41_verify",
) -> Dict[str, Any]:
    """从快照拿到 ``phase3.defense_validation.<verify_key>`` 子字典。

    ``verify_key`` 用于区分：
    * ``"fig41_verify"``     — 旧默认（更早 t0，Fig4.1 综合卡）
    * ``"fig41_verify_mm"`` — 模型—模型 / JSD（Fig 4.1a）
    * ``"fig41_verify_mv"`` — 模型—市场 / 余弦（Fig 4.1b）

    缺任何一层都返回空 dict，不抛异常；调用方据此决定走 fallback 分支。
    """
    assert isinstance(snap_json, dict), (
        f"snap_json must be dict, got {type(snap_json).__name__}"
    )
    assert isinstance(verify_key, str) and verify_key, "verify_key must be non-empty str"

    p3 = _safe_dict(snap_json.get("phase3"))
    dv = _safe_dict(p3.get("defense_validation"))
    v = _safe_dict(dv.get(verify_key))

    _trace("fig41_verify key=%s keys=%s", verify_key, sorted(v.keys()) if v else "(empty)")
    return v


def _extract_hits(v: Dict[str, Any]) -> Fig41Hits:
    """从 ``fig41_verify.hits`` 解析出三维命中 + verdict。

    Args:
        v: ``fig41_verify`` 子字典（可为空）。

    Returns:
        Fig41Hits：verdict/n_hit 缺失时分别回退为 ``"—"`` / ``None``。
    """
    assert isinstance(v, dict), f"v must be dict, got {type(v).__name__}"

    hits = _safe_dict(v.get("hits"))
    verdict = str(hits.get("verdict") or "—")
    n_hit_raw = hits.get("n_hit")
    try:
        n_hit: Optional[int] = int(n_hit_raw) if n_hit_raw is not None else None
    except (TypeError, ValueError):
        n_hit = None

    out = Fig41Hits(
        verdict=verdict,
        n_hit=n_hit,
        std_above_baseline=bool(hits.get("std_above_baseline")),
        crash_ratio_above_baseline=bool(hits.get("crash_ratio_above_baseline")),
        tail_ratio_above_baseline=bool(hits.get("tail_ratio_above_baseline")),
    )
    _trace("hits verdict=%s n_hit=%s std=%s crash=%s tail=%s",
           out.verdict, out.n_hit, out.std_above_baseline,
           out.crash_ratio_above_baseline, out.tail_ratio_above_baseline)
    return out


def _extract_post_alarm(v: Dict[str, Any]) -> Optional[Fig41PostAlarm]:
    """解析告警后逐标的指标。

    返回 ``None`` ⇒ 快照里缺少 ``post`` 子树，上游应走 fallback 分支。
    """
    assert isinstance(v, dict), f"v must be dict, got {type(v).__name__}"

    post = v.get("post")
    if not isinstance(post, dict):
        _trace("post missing → fallback panel")
        return None

    syms = [str(s) for s in _safe_list(post.get("symbols"))]
    per_crash = _safe_dict(post.get("per_symbol_crash"))
    tail_flags_raw = _safe_list(post.get("tail_flags_5xN"))
    tail_flags: List[List[int]] = []
    for row in tail_flags_raw[:5]:
        if isinstance(row, list):
            tail_flags.append([int(bool(x)) for x in row])

    # per-symbol 系列（用于 focus_override 搜索重绑定；旧快照缺失→空 dict）
    per_rh_raw = _safe_dict(post.get("per_symbol_Rh"))
    per_rh: Dict[str, float] = {}
    for k, v in per_rh_raw.items():
        f = _as_opt_float(v)
        if f is not None:
            per_rh[str(k)] = f
    per_daily_raw = _safe_dict(post.get("per_symbol_daily_returns"))
    per_daily: Dict[str, List[float]] = {}
    for k, v in per_daily_raw.items():
        if isinstance(v, list):
            per_daily[str(k)] = [float(x) for x in v if isinstance(x, (int, float))]

    out = Fig41PostAlarm(
        symbols=syms,
        per_symbol_crash=per_crash,
        tail_flags_5xN=tail_flags,
        crash_ratio=_as_opt_float(post.get("crash_ratio")),
        tail_ratio=_as_opt_float(post.get("tail_ratio")),
        cross_section_std_Rh=_as_opt_float(post.get("cross_section_std_Rh")),
        post_dates=[str(d) for d in _safe_list(post.get("post_dates"))],
        per_symbol_Rh=per_rh,
        per_symbol_daily_returns=per_daily,
        tail_left_thr=_as_opt_float(post.get("tail_left_thr")),
        tail_right_thr=_as_opt_float(post.get("tail_right_thr")),
    )
    _trace("post symbols=%d tail_rows=%d crash=%s tail=%s std=%s",
           len(out.symbols), len(out.tail_flags_5xN),
           out.crash_ratio, out.tail_ratio, out.cross_section_std_Rh)
    return out


def _verify_t0_date(v: Dict[str, Any]) -> Optional[str]:
    """从 fig41_verify.post.t0_date 取告警日 ISO；缺失返回 None。"""
    post = v.get("post") if isinstance(v, dict) else None
    if not isinstance(post, dict):
        return None
    raw = post.get("t0_date")
    return str(raw) if raw else None


def _extract_dual(snap_json: Dict[str, Any]) -> Fig41DualVerdict:
    """从 defense_validation 里抽取 mm / mv 两路 verdict + 告警日 + 更早者。"""
    p3 = _safe_dict(snap_json.get("phase3"))
    dv = _safe_dict(p3.get("defense_validation"))
    mm = _safe_dict(dv.get("fig41_verify_mm"))
    mv = _safe_dict(dv.get("fig41_verify_mv"))

    def _vd(b: Dict[str, Any]) -> str:
        h = _safe_dict(b.get("hits"))
        return str(h.get("verdict") or "—")

    mm_d = _verify_t0_date(mm)
    mv_d = _verify_t0_date(mv)

    # 兼容字段 earliest_t0_date：两路都通过 → 取较早（字典序更小 ISO）
    def _is_pass(verdict: str) -> bool:
        return verdict in ("成功", "较成功")

    valid = []
    mm_v = _vd(mm)
    mv_v = _vd(mv)
    if _is_pass(mm_v) and mm_d:
        valid.append(mm_d)
    if _is_pass(mv_v) and mv_d:
        valid.append(mv_d)
    earliest = min(valid) if valid else None

    # 新规则 final_t0_date：**模型—市场优先 > 模型—模型**；两路都失败 → None
    if _is_pass(mv_v) and mv_d:
        final = mv_d
    elif _is_pass(mm_v) and mm_d:
        final = mm_d
    else:
        final = None

    out = Fig41DualVerdict(
        mm_verdict=mm_v,
        mv_verdict=mv_v,
        mm_t0_date=mm_d,
        mv_t0_date=mv_d,
        earliest_t0_date=earliest,
        final_t0_date=final,
    )
    _trace("dual mm=%s@%s mv=%s@%s earliest=%s final=%s",
           out.mm_verdict, out.mm_t0_date, out.mv_verdict, out.mv_t0_date,
           out.earliest_t0_date, out.final_t0_date)
    return out


def _extract_baselines(v: Dict[str, Any], policy: Any) -> Fig41Baselines:
    """从 ``fig41_verify.baselines`` + policy 组合出三条基线。

    policy 只读 ``verify_tail_quantile_pct``；不修改 policy。
    """
    assert isinstance(v, dict), f"v must be dict, got {type(v).__name__}"

    base = _safe_dict(v.get("baselines"))
    p_pct = int(getattr(policy, "verify_tail_quantile_pct", 90) or 90)
    assert 50 <= p_pct <= 99, (
        f"verify_tail_quantile_pct out of range: {p_pct}"
    )
    tail_p = float(1.0 - p_pct / 100.0)  # 单侧理论占比基线

    # 逐标的大跌阈值（R^(h) 左尾分位；按需向前兼容）
    per_thr_raw = _safe_dict(base.get("crash_thresholds_Rh"))
    per_thr: Dict[str, float] = {}
    for k, val in per_thr_raw.items():
        f = _as_opt_float(val)
        if f is not None:
            per_thr[str(k)] = f

    out = Fig41Baselines(
        std_thr=_as_opt_float(base.get("baseline_std_thr")),
        crash_ratio_thr=_as_opt_float(base.get("baseline_crash_ratio_thr")),
        tail_ratio_thr=_as_opt_float(base.get("baseline_tail_ratio_thr")),
        tail_p_each_side=tail_p,
        per_symbol_crash_thr=per_thr,
    )
    _trace("baselines std=%s crash=%s tail=%s p_each_side=%.3f",
           out.std_thr, out.crash_ratio_thr, out.tail_ratio_thr, out.tail_p_each_side)
    return out


# --------------------------------------------------------------------------- #
# 公共入口                                                                     #
# --------------------------------------------------------------------------- #


def extract_fig41_bundle(
    snap_json: Dict[str, Any],
    policy: Any,
    *,
    verify_key: str = "fig41_verify",
) -> Fig41Bundle:
    """把 snapshot + policy 抽取为完整的 :class:`Fig41Bundle`。

    Args:
        snap_json: 管线输出的 JSON 快照（必须是 dict，可以为空）。
        policy: :class:`research.schemas.DefensePolicyConfig` 实例。
        verify_key: 指定 defense_validation 下的哪份 verify 字典作为 bundle 数据源；
            默认 ``"fig41_verify"``（综合卡，向后兼容）；``"fig41_verify_mm"`` /
            ``"fig41_verify_mv"`` 分别对应 Fig4.1a / Fig4.1b。

    Returns:
        Fig41Bundle：所有字段均已填好，必要时为默认值。
    """
    assert isinstance(snap_json, dict), (
        f"snap_json must be dict, got {type(snap_json).__name__}"
    )
    assert policy is not None, "policy must not be None"

    v = _extract_fig41_verify(snap_json, verify_key=verify_key)
    hits = _extract_hits(v)
    post = _extract_post_alarm(v)
    baselines = _extract_baselines(v, policy)
    dual = _extract_dual(snap_json)

    # 焦点标的大跌判定（R^(h) < 逐标阈值 → 红；否则 → 绿）
    focus_Rh = _as_opt_float(v.get("focus_Rh"))
    focus_thr = _as_opt_float(v.get("focus_crash_thr_Rh"))
    raw_is_crash = v.get("focus_is_crash")
    if isinstance(raw_is_crash, bool):
        focus_is_crash: Optional[bool] = raw_is_crash
    elif focus_Rh is not None and focus_thr is not None:
        focus_is_crash = bool(focus_Rh < focus_thr)
    else:
        focus_is_crash = None

    bundle = Fig41Bundle(
        focus_symbol=str(v.get("focus_symbol") or "—"),
        hits=hits,
        post=post,
        baselines=baselines,
        focus_daily_returns=[
            float(x) for x in _safe_list(v.get("focus_daily_returns"))
            if isinstance(x, (int, float))
        ],
        focus_post_dates=(post.post_dates if post else []),
        focus_tail_left_ratio=_as_opt_float(v.get("focus_tail_left_ratio")),
        focus_tail_right_ratio=_as_opt_float(v.get("focus_tail_right_ratio")),
        cross_section_std_by_k=[
            float(x) for x in _safe_list(v.get("cross_section_std_by_k"))
            if isinstance(x, (int, float))
        ],
        focus_Rh=focus_Rh,
        focus_crash_thr_Rh=focus_thr,
        focus_is_crash=focus_is_crash,
        dual=dual,
    )
    _trace("bundle ready focus=%s has_post=%s focus_crash=%s dual_mm=%s dual_mv=%s",
           bundle.focus_symbol, bundle.has_post, bundle.focus_is_crash,
           dual.mm_verdict, dual.mv_verdict)
    return bundle
