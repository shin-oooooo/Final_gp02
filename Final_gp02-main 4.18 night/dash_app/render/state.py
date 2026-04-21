"""DashboardState 抽取 — 从 snap_json + policy 一次性提取所有派生值。

纯函数，入口断言；所有 ``build_*`` 只读这个 state（严禁回头 ``snap_json.get(...)``）。
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from dash_app.render.contracts import DashboardState

logger = logging.getLogger("dash_app.render.state")
_TRACE = os.environ.get("DEBUG_RENDER", "0").strip() not in ("", "0", "false", "False")


def _trace(msg: str, *args: Any) -> None:
    logger.debug(msg, *args)
    if _TRACE:
        try:
            print(f"[render.state] {msg % args}" if args else f"[render.state] {msg}")
        except Exception:
            pass


def _safe_dict(v: Any) -> Dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _safe_list(v: Any) -> List[Any]:
    return list(v) if isinstance(v, list) else []


def jsd_dynamic_threshold(
    p2: Dict[str, Any],
    k_jsd: float,
    *,
    baseline_eps: float = 1e-9,
) -> float:
    """水平参照 τ = k_jsd × max(jsd_baseline_mean, ε)，与 ``phase2._jsd_stress_rolling_breach`` 一致。

    管线侧使用这条公式判断 JSD 应力触发；UI 侧用同一条公式画阈值线并注入讲解变量。
    该函数不涉及 UI 渲染，但只被 render 层使用，故定居于此。
    """
    jm = float(p2.get("jsd_baseline_mean") or 0.0)
    eps = float(baseline_eps) if baseline_eps is not None and float(baseline_eps) > 0 else 1e-9
    base = max(jm, eps)
    return float(k_jsd) * base


def _resolve_windows(
    meta: Dict[str, Any],
    tr_idx: List[str],
    te_idx: List[str],
) -> tuple[str, str, str, str]:
    """归并训练窗 / 测试窗起止日期。"""
    from research.schemas import Phase0Input

    default = Phase0Input()
    rw = _safe_dict(meta.get("resolved_windows"))
    train_start = str(rw.get("train_start") or (tr_idx[0] if tr_idx else default.train_start))
    train_end = str(rw.get("train_end") or (tr_idx[-1] if tr_idx else default.train_end))
    test_start = str(rw.get("test_start") or (te_idx[0] if te_idx else default.test_start))
    test_end = str(rw.get("test_end") or (te_idx[-1] if te_idx else default.test_end))
    return train_start, train_end, test_start, test_end


def extract_dashboard_state(
    snap_json: Dict[str, Any],
    policy: Any,
    *,
    symbols: List[str],
    api_err: Optional[str],
    s_val: float,
    theme: Optional[str],
    p2_sym_state: Optional[str],
    ui_mode: Optional[str],
    p4_focus_a: Optional[str] = None,
    p4_focus_b: Optional[str] = None,
) -> DashboardState:
    """从快照 + 参数构造 :class:`DashboardState`（不可变，一次到位）。"""
    assert isinstance(snap_json, dict), (
        f"snap_json must be dict, got {type(snap_json).__name__}"
    )
    assert policy is not None, "policy must not be None"
    assert isinstance(symbols, list), f"symbols must be list, got {type(symbols).__name__}"

    from dash_app.ui.layout import _default_data_json_path, _templates

    tpl = _templates(theme or "dark")
    json_path = _default_data_json_path()

    p0 = _safe_dict(snap_json.get("phase0"))
    p1 = _safe_dict(snap_json.get("phase1"))
    p2 = _safe_dict(snap_json.get("phase2"))
    p3 = _safe_dict(snap_json.get("phase3"))
    meta = _safe_dict(p0.get("meta"))
    env = _safe_dict(p0.get("environment_report"))

    defense_level = int(snap_json.get("defense_level", 0))
    objective_name = str(p3.get("objective_name") or "")

    train_start, train_end, test_start, test_end = _resolve_windows(
        meta, _safe_list(p0.get("train_index")), _safe_list(p0.get("test_index"))
    )

    benchmark = str(meta.get("benchmark", "SPY"))
    tech_m = _safe_list(meta.get("tech_symbols"))
    hedge_m = _safe_list(meta.get("hedge_symbols"))
    safe_m = _safe_list(meta.get("safe_symbols"))

    h_struct = float(p1.get("h_struct", 1.0))
    tau_h1 = float(getattr(policy, "tau_h1", 0.5) or 0.5)
    tau_l1 = float(getattr(policy, "tau_l1", 0.70) or 0.70)
    tau_l2 = float(getattr(policy, "tau_l2", 0.45) or 0.45)
    tau_s_low = float(policy.tau_s_low)
    tau_vol_melt = float(getattr(policy, "tau_vol_melt", 0.32) or 0.32)
    tau_return_ac1 = float(getattr(policy, "tau_return_ac1", -0.08) or -0.08)
    sem_cos = int(getattr(policy, "semantic_cosine_window", 5) or 5)

    jsd_tri = float(p2.get("jsd_triangle_mean", 0.0))
    jsd_thr = float(
        jsd_dynamic_threshold(
            p2,
            float(getattr(policy, "k_jsd", 2.0) or 2.0),
            baseline_eps=float(getattr(policy, "jsd_baseline_eps", 1e-9) or 1e-9),
        )
    )
    jsd_pairs_mean = float(p2.get("jsd_pairs_mean", 0.0))
    consistency = float(p2.get("credibility_score", p2.get("consistency_score", 0.5)))
    s_min_sb = float(meta.get("defense_sentiment_min_st", s_val) or s_val)

    state = DashboardState(
        snap_json=snap_json,
        policy=policy,
        p0=p0, p1=p1, p2=p2, p3=p3,
        meta=meta, env=env,
        defense_level=defense_level,
        symbols=list(symbols),
        api_err=api_err,
        s_val=float(s_val),
        ui_mode=ui_mode,
        tpl=tpl,
        p2_sym_state=p2_sym_state,
        p4_focus_a=p4_focus_a,
        p4_focus_b=p4_focus_b,
        json_path=json_path,
        objective_name=objective_name,
        train_start=train_start, train_end=train_end,
        test_start=test_start, test_end=test_end,
        benchmark=benchmark,
        tech_m=[str(x) for x in tech_m],
        hedge_m=[str(x) for x in hedge_m],
        safe_m=[str(x) for x in safe_m],
        h_struct=h_struct,
        tau_h1=tau_h1, tau_l1=tau_l1, tau_l2=tau_l2,
        tau_s_low=tau_s_low,
        tau_vol_melt=tau_vol_melt,
        tau_return_ac1=tau_return_ac1,
        semantic_cos_window=sem_cos,
        jsd_tri=jsd_tri, jsd_thr=jsd_thr,
        jsd_pairs_mean=jsd_pairs_mean,
        consistency=consistency,
        s_min_sb=s_min_sb,
        best_per_sym=dict(_safe_dict(p2.get("best_model_per_symbol"))),
        model_mu=_safe_dict(p2.get("model_mu")),
        model_sigma=_safe_dict(p2.get("model_sigma")),
        model_mu_test_ts=_safe_dict(p2.get("model_mu_test_ts")),
        model_sigma_test_ts=_safe_dict(p2.get("model_sigma_test_ts")),
        test_forecast_dates=_safe_list(p2.get("test_forecast_dates")),
        weights=_safe_dict(p3.get("weights")),
        diagnostics=[_safe_dict(d) for d in _safe_list(p1.get("diagnostics"))],
    )
    _trace(
        "state built: level=%d symbols=%d h=%.3f c=%.3f jsd_tri=%.4f api_err=%s",
        state.defense_level, len(state.symbols),
        state.h_struct, state.consistency, state.jsd_tri, state.api_err,
    )
    return state
