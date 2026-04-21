"""情绪分 (S_t) 与情绪详情解析 — 纯函数。

**这里是 Feedback 要求 10**（"S_t 情绪分为恒定值, 各模型预测近直线"）**
**bug 最可能的源头**：旧版本在此处直接调用全局 ``get_sentiment_score()``
且没有日志，一旦获取失败会静默回退到 -0.1（就是那个"恒定值"）。

本模块把该段逻辑拆成 3 个纯函数 + 主入口：

* :func:`_coerce_sentiment_scalar` — sentiment 原值 → 有限 float 或 None
* :func:`_fetch_sentiment_score_safe` — 调 API；失败返回 (-0.1, err_tag)
* :func:`_fetch_sentiment_detail_safe` — 调 detail API；失败返回 None
* :func:`resolve_sentiment` — 组装 (s_val, sd)；每一步的回退都会 **日志可见**

这样你用 ``DEBUG_PIPELINE_EXEC=1`` 跑一次就能肉眼看到 S_t 到底是从
API 拿到的、还是 fallback 的、还是 detail 覆盖过的。
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from dash_app.pipeline_exec.contracts import pipeline_exec_debug_enabled

logger = logging.getLogger("dash_app.pipeline_exec.sentiment_resolver")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if pipeline_exec_debug_enabled():
        try:
            text = msg % args if args else msg
            print(f"[sentiment] {text}", flush=True)
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# 低层助手                                                                     #
# --------------------------------------------------------------------------- #


def _coerce_sentiment_scalar(raw: Any) -> Optional[float]:
    """任意输入 → 有限 float 或 None。"""
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


# 当 sentiment API 完全无法返回值时使用的中性占位（不再是 -0.1）。
# 选 0.0 的原因：避免「看似有意义的轻微负向」，让下游能区分真信号 vs 占位。
_SENTIMENT_NEUTRAL_FALLBACK = 0.0


def _fetch_sentiment_score_safe() -> Tuple[float, Optional[str]]:
    """惰性调 ``get_sentiment_score()``；失败回退为中性 0.0 并记日志。

    Returns:
        (s_val, err_tag)：err_tag 为 None 表示成功；非 None 时表示
        s_val 为占位值（外层应据此在 UI 显式提示）。
    """
    try:
        from dash_app.dash_ui_helpers import get_sentiment_score
    except Exception as exc:
        _trace("import get_sentiment_score FAILED: %s → fallback %.2f",
               exc, _SENTIMENT_NEUTRAL_FALLBACK)
        logger.warning("sentiment import failed: %s", exc)
        return (_SENTIMENT_NEUTRAL_FALLBACK, f"import_fail:{type(exc).__name__}")

    try:
        s = float(get_sentiment_score())
    except Exception as exc:
        _trace("get_sentiment_score() raised: %s → fallback %.2f",
               exc, _SENTIMENT_NEUTRAL_FALLBACK)
        logger.warning("get_sentiment_score() raised %s: %s",
                       type(exc).__name__, exc)
        return (_SENTIMENT_NEUTRAL_FALLBACK, f"api_fail:{type(exc).__name__}")

    if not math.isfinite(s):
        _trace("get_sentiment_score() returned non-finite → fallback %.2f",
               _SENTIMENT_NEUTRAL_FALLBACK)
        logger.warning("get_sentiment_score() returned non-finite")
        return (_SENTIMENT_NEUTRAL_FALLBACK, "non_finite")

    return (s, None)


def _fetch_sentiment_detail_safe(
    *,
    fallback: float,
    active_symbols: Optional[List[str]],
) -> Optional[Dict[str, Any]]:
    """惰性调 ``get_sentiment_detail(...)``；失败返回 None。"""
    try:
        from dash_app.dash_ui_helpers import get_sentiment_detail
    except Exception as exc:
        _trace("import get_sentiment_detail FAILED: %s", exc)
        return None

    try:
        sd = get_sentiment_detail(
            fallback=fallback,
            active_symbols=active_symbols if active_symbols else None,
        )
    except Exception as exc:
        _trace("get_sentiment_detail() raised: %s", exc)
        return None

    return sd if isinstance(sd, dict) else None


def _dedup_symbols_from_phase0(p0_in: Any) -> List[str]:
    """从 Phase0Input 里按顺序去重并合并三类标的。"""
    tech = list(getattr(p0_in, "tech_symbols", None) or [])
    hedge = list(getattr(p0_in, "hedge_symbols", None) or [])
    safe = list(getattr(p0_in, "safe_symbols", None) or [])
    return list(dict.fromkeys(tech + hedge + safe))


# --------------------------------------------------------------------------- #
# 主入口                                                                       #
# --------------------------------------------------------------------------- #


def resolve_sentiment(
    sentiment_raw: Any,
    sentiment_detail_raw: Any,
    p0_in: Any,
) -> Tuple[float, Optional[Dict[str, Any]]]:
    """解析最终的 ``(s_val, sentiment_detail)``。

    策略（按优先级）：
    1. 若前端给了合法 ``sentiment`` scalar，**优先用它**。
    2. 否则调 ``get_sentiment_score()`` API；失败回退 -0.1。
    3. 若前端给了合法 ``sentiment_detail`` dict，**沿用**。
    4. 否则调 ``get_sentiment_detail(fallback=s_val, symbols=...)``；
       若成功且里面有更新的 score，**覆盖** s_val（这一步是 S_t 真正的来源）。

    每一步都有日志。

    Args:
        sentiment_raw: 前端可能传入的 scalar（任意类型）。
        sentiment_detail_raw: 前端可能传入的 detail dict（或 None）。
        p0_in: Phase0Input 实例，用于从中拿到 active symbols 作为 API 输入。

    Returns:
        ``(s_val, sentiment_detail)``：s_val 保证有限 float；sentiment_detail
        可能是 dict 或 None。两者都是**新对象**，不修改传入的任何参数。
    """
    assert p0_in is not None, "p0_in must not be None"

    # Step 1: 尝试用 scalar
    s_val = _coerce_sentiment_scalar(sentiment_raw)
    _trace("step1 sentiment_raw=%s → s_val=%s", sentiment_raw, s_val)

    # Step 2: 若 scalar 失败，调 API
    api_err: Optional[str] = None
    if s_val is None:
        s_val, api_err = _fetch_sentiment_score_safe()
        _trace("step2 API → s_val=%s (err=%s)", s_val, api_err)

    # Step 3: 是否已提供 detail
    sd = sentiment_detail_raw if isinstance(sentiment_detail_raw, dict) else None
    _trace("step3 detail_provided=%s", sd is not None)

    # Step 4: 若没提供，拉 detail 并用其 score 覆盖 s_val
    if sd is None:
        syms = _dedup_symbols_from_phase0(p0_in)
        sd = _fetch_sentiment_detail_safe(fallback=s_val, active_symbols=syms)
        if isinstance(sd, dict):
            sc = _coerce_sentiment_scalar(sd.get("score"))
            if sc is not None:
                _trace("step4 detail.score=%.4f overrides s_val=%.4f", sc, s_val)
                s_val = sc
            else:
                _trace("step4 detail has no valid score → keep s_val=%s", s_val)
        else:
            _trace("step4 detail API failed → sd=None, keep s_val=%s", s_val)

    # Always-on diagnostic: surface what the pipeline will actually receive.
    try:
        if isinstance(sd, dict):
            _hl = sd.get("headlines") or []
            _pub_days = {str((_r or {}).get("published") or "")[:10] for _r in _hl if (_r or {}).get("published")}
            _pub_days = sorted(d for d in _pub_days if d)
            print(
                f"[sentiment:out] s_val={s_val:.4f} sd.source={sd.get('source')} "
                f"sd.score={sd.get('score')} sd.n_headlines={len(_hl)} "
                f"sd.unique_pub_days={len(_pub_days)} "
                f"sd.pub_range=({_pub_days[0] if _pub_days else None},"
                f"{_pub_days[-1] if _pub_days else None})",
                flush=True,
            )
        else:
            print(
                f"[sentiment:out] s_val={s_val:.4f} sd=None "
                f"(get_sentiment_detail fetch failed / not called)",
                flush=True,
            )
    except Exception:
        pass

    assert math.isfinite(s_val), f"s_val must be finite, got {s_val}"
    return s_val, sd
