"""管线执行编排 — API → 本地 → 无 detail 重试 三级降级。

原 ``_execute_pipeline_for_dashboard`` 后半段的 try/except 嵌套在这里
拆成 3 个单职责函数：

* :func:`_ensure_data_json_exists`   — 缺文件时静默触发下载
* :func:`_run_via_api_or_local`      — API → 本地 fallback
* :func:`_extract_symbols_from_snap` — 从快照 phase0.meta / phase3.weights 拿 symbols

主入口 :func:`execute_pipeline_for_dashboard` 做**编排**（不含业务逻辑）。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from dash_app.pipeline_exec.contracts import PipelineResult, SliderInputs, pipeline_exec_debug_enabled
from dash_app.pipeline_exec.policy_builder import build_policy_from_sliders
from dash_app.pipeline_exec.sentiment_resolver import resolve_sentiment

logger = logging.getLogger("dash_app.pipeline_exec.executor")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if pipeline_exec_debug_enabled():
        try:
            text = msg % args if args else msg
            print(f"[executor] {text}", flush=True)
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# 子任务（每个只做一件事）                                                      #
# --------------------------------------------------------------------------- #


def _ensure_data_json_exists(json_path: str) -> None:
    """数据文件缺失时，调用后端刷新接口生成；失败**静默忽略**。"""
    assert isinstance(json_path, str) and json_path, "json_path must be non-empty str"

    if os.path.exists(json_path):
        _trace("data.json exists: %s", json_path)
        return

    _trace("data.json MISSING, attempting refresh...")
    try:
        from research.data_refresher import _do_refresh

        _do_refresh(json_path)
        _trace("refresh succeeded, new size=%s",
               os.path.getsize(json_path) if os.path.exists(json_path) else "(still missing)")
    except Exception as exc:
        _trace("refresh FAILED: %s (silent)", exc)


def _run_via_api_or_local(
    policy: Any,
    s_val: float,
    phase0_payload: Dict[str, Any],
    sd: Optional[Dict[str, Any]],
    p0_in: Any,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """API → 本地 → 无 detail 重试（三级降级）。

    Returns:
        ``(snap_json, api_err)``；snap_json 一定非空。
    """
    from dash_app.dash_ui_helpers import (
        _safe_analyze_via_api,
        _snapshot_json_ok,
        snapshot_to_jsonable,
    )
    from research.pipeline import run_pipeline

    # Level 1: API
    snap_json, api_err = _safe_analyze_via_api(policy, s_val, phase0_payload, sd)
    if snap_json is not None and _snapshot_json_ok(snap_json):
        _trace("level1 API OK (api_err=%s)", api_err)
        return snap_json, api_err
    _trace("level1 API failed or invalid (api_err=%s) → try local", api_err)

    # Level 2: 本地 with detail
    def _local(detail: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        snap = run_pipeline(
            policy=policy, phase0_in=p0_in,
            sentiment_score=s_val, sentiment_detail=detail,
        )
        return snapshot_to_jsonable(snap)

    try:
        snap = _local(sd)
        _trace("level2 local (with detail) OK")
        return snap, api_err
    except Exception as exc1:
        _trace("level2 local (with detail) FAILED: %s", exc1)
        # Level 3: 本地 without detail — 仅当原本有 detail 时才重试
        if sd is not None:
            try:
                snap = _local(None)
                _trace("level3 local (no detail) OK")
                return snap, api_err
            except Exception as exc2:
                _trace("level3 local (no detail) FAILED: %s", exc2)
                raise exc1 from None
        raise


def _extract_symbols_from_snap(snap_json: Dict[str, Any]) -> List[str]:
    """从快照抽取 symbols 列表（优先 phase0.meta.symbols_resolved）。"""
    assert isinstance(snap_json, dict), "snap_json must be dict"

    p0 = snap_json.get("phase0") or {}
    p3 = snap_json.get("phase3") or {}
    meta = p0.get("meta") or {}
    weights = p3.get("weights") or {}
    syms = meta.get("symbols_resolved") or list(weights.keys())
    return [str(s) for s in syms]


# --------------------------------------------------------------------------- #
# 主入口                                                                       #
# --------------------------------------------------------------------------- #


def execute_pipeline_for_dashboard(
    inputs: SliderInputs,
    sentiment_raw: Any,
    asset_universe: Any,
    strike_store: Any,
    sentiment_detail_raw: Any,
) -> PipelineResult:
    """Dashboard 侧管线执行总入口。

    职责编排（**每一步都在日志里可见**）：

    1. :func:`build_policy_from_sliders` — SliderInputs → DefensePolicyConfig
    2. 从 asset_universe + strike_store 构造 Phase0Input
    3. :func:`resolve_sentiment` — 得到 (s_val, sd)
    4. :func:`_ensure_data_json_exists`
    5. :func:`_run_via_api_or_local` — 三级降级
    6. :func:`_extract_symbols_from_snap`

    Args:
        inputs: 滑块原始值打包。
        sentiment_raw: 情绪 scalar 原值（可 None）。
        asset_universe: 资产域 store。
        strike_store: 划线 store。
        sentiment_detail_raw: 情绪详情原值（可 None）。

    Returns:
        :class:`PipelineResult` — 不可变，可通过 ``.to_tuple()`` 拿旧 5 元组兼容。
    """
    assert isinstance(inputs, SliderInputs), (
        f"inputs must be SliderInputs, got {type(inputs).__name__}"
    )

    # Step 1: policy
    policy = build_policy_from_sliders(inputs)

    # Step 2: Phase0Input（惰性 import 避循环）
    from dash_app.dash_ui_helpers import (
        _default_data_json_path,
        _phase0_from_universe_after_strikes,
    )

    p0_in = _phase0_from_universe_after_strikes(asset_universe, strike_store)
    phase0_payload = p0_in.model_dump()
    _trace("phase0 resolved: %d tech, %d hedge, %d safe",
           len(p0_in.tech_symbols or []),
           len(p0_in.hedge_symbols or []),
           len(p0_in.safe_symbols or []))

    # Step 3: sentiment
    s_val, sd = resolve_sentiment(sentiment_raw, sentiment_detail_raw, p0_in)
    _trace("sentiment resolved: s_val=%.4f detail_provided=%s", s_val, sd is not None)

    # Step 4: data.json
    _ensure_data_json_exists(_default_data_json_path())

    # Step 5: pipeline（三级降级）
    snap_json, api_err = _run_via_api_or_local(policy, s_val, phase0_payload, sd, p0_in)

    # Step 6: symbols
    symbols = _extract_symbols_from_snap(snap_json)
    _trace("pipeline done: %d symbols, api_err=%s", len(symbols), api_err)

    return PipelineResult(
        policy=policy,
        snap_json=snap_json,
        symbols=symbols,
        api_err=api_err,
        sentiment_score=s_val,
    )
