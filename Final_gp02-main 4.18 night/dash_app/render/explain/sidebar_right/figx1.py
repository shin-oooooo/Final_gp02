"""FigX.1 · S_t 情绪路径 — 讲解卡 + defense-tag 条件行。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dash_app.render.explain._formatters import merge_base_vm
from dash_app.render.explain._loaders import (
    load_defense_tag_text,
    load_figx_template,
    _substitute_md,
)


def build_figx1_explain_body(
    ui_mode: Optional[str],
    snap_json: Dict[str, Any],
    pol: Any,
    p2: Dict[str, Any],
    meta: Dict[str, Any],
    symbols: List[str],
    json_path: str,
) -> str:
    """FigX.1 讲解卡：测试窗 S_t（指数核 MVP · 当日 VADER + 历史记忆 + penalty/boost）。"""
    _ = json_path
    tpl = load_figx_template("1", ui_mode)
    vm = merge_base_vm(ui_mode, snap_json, pol, p2, meta, symbols)
    st = meta.get("test_sentiment_st") or {}
    dates = st.get("dates") or []
    vals = st.get("values") or []
    vm["tau_s_low"] = f"{float(getattr(pol, 'tau_s_low', -0.20) or -0.20):.3f}"
    if dates and vals and len(dates) == len(vals):
        vm["st_min"] = f"{float(min(vals)):.6f}"
        vm["st_max"] = f"{float(max(vals)):.6f}"
        vm["st_last"] = f"{float(vals[-1]):.6f}"
        vm["st_news_days"] = str(len(dates))
    else:
        vm["st_min"] = "—"
        vm["st_max"] = "—"
        vm["st_last"] = "—"
        vm["st_news_days"] = "—"
    vm["st_segments"] = "—"

    kernel = meta.get("sentiment_st_kernel") or {}
    vm["sentiment_halflife_days"] = (
        f"{float(kernel.get('halflife_days', getattr(pol, 'sentiment_halflife_days', 2.0) or 2.0)):.2f}"
    )
    vm["sentiment_penalty"] = f"{float(kernel.get('penalty') or 0.0):+.4f}"
    vm["sentiment_severity_boost"] = f"{float(kernel.get('severity_boost') or 0.0):+.4f}"
    vm["sentiment_vader_avg"] = f"{float(kernel.get('vader_avg') or 0.0):+.4f}"
    vm["sentiment_n_headlines"] = str(int(kernel.get("n_headlines") or 0))
    vm["sentiment_kernel_method"] = str(kernel.get("method") or "kernel_smoothed_exponential_mvp")

    return _substitute_md(tpl, vm)


def figx1_condition_line(
    *,
    s_min: float,
    tau_s_low: float,
    c: float,
    tau_l1: float,
) -> Tuple[str, str]:
    """FigX.1 defense-tag：当 c>τ_L1 且 min(S_t)<τ_S_low 时触发 Level 1 警示。"""
    vm = {
        "st_min": f"{float(s_min):.3f}",
        "tau_s_low": f"{float(tau_s_low):.3f}",
        "credibility": f"{float(c):.4f}",
        "tau_l1": f"{float(tau_l1):.3f}",
    }
    cond = float(c) > float(tau_l1) and float(s_min) < float(tau_s_low)
    return load_defense_tag_text("1", None, vm, "if" if cond else "else")
