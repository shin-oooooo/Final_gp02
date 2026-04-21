"""FigX.5 · 模型—模型 JSD 应力 — 讲解卡 + defense-tag 条件行。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from dash_app.render.explain._formatters import merge_base_vm, tail_csv
from dash_app.render.explain._loaders import (
    load_defense_tag_text,
    load_figx_template,
    _substitute_md,
)
from dash_app.render.explain.figure_captions import _jsd_threshold_value
from dash_app.render.explain.sidebar_right._shared import (
    defense_validation,
    iso_test_date,
    iso_to_yymmdd,
)


def _rolling_mean_at(seq: List[float], row: int, window: int) -> Optional[float]:
    """返回 ``row`` 处长度为 ``window`` 的滚动均值；窗口不满或全 NaN 返回 None。"""
    w = max(1, int(window))
    if row is None or row < w - 1 or row >= len(seq):
        return None
    arr = np.array(seq[row - w + 1 : row + 1], dtype=float)
    if not np.any(np.isfinite(arr)):
        return None
    return float(np.nanmean(arr))


def build_figx5_explain_body(
    ui_mode: Optional[str],
    snap_json: Dict[str, Any],
    pol: Any,
    p2: Dict[str, Any],
    meta: Dict[str, Any],
    symbols: List[str],
    json_path: str,
) -> str:
    """FigX.5 讲解卡：三角 JSD 均值 / 训练基线 / 动态阈值。"""
    _ = json_path
    tpl = load_figx_template("5", ui_mode)
    vm = merge_base_vm(ui_mode, snap_json, pol, p2, meta, symbols)
    vm["jsd_kronos_arima_mean"] = f"{float(p2.get('jsd_kronos_arima_mean') or 0.0):.8f}"
    vm["jsd_kronos_gbm_mean"] = f"{float(p2.get('jsd_kronos_gbm_mean') or 0.0):.8f}"
    vm["jsd_gbm_arima_mean"] = f"{float(p2.get('jsd_gbm_arima_mean') or 0.0):.8f}"
    vm["jsd_triangle_mean"] = f"{float(p2.get('jsd_triangle_mean') or 0.0):.8f}"
    vm["jsd_triangle_max"] = f"{float(p2.get('jsd_triangle_max') or 0.0):.8f}"
    vm["jsd_baseline_mean"] = f"{float(p2.get('jsd_baseline_mean') or 0.0):.8f}"
    vm["cos_w"] = str(int(getattr(pol, "semantic_cosine_window", 5) or 5))
    vm["k_jsd"] = f"{float(getattr(pol, 'k_jsd', 2.0) or 2.0):.4f}"
    vm["jsd_baseline_eps"] = f"{float(getattr(pol, 'jsd_baseline_eps', 1e-9) or 1e-9):.4e}"
    vm["jsd_stress_dyn_thr"] = f"{float(vm.get('jsd_thr', 0.0) or 0.0):.8f}"
    daily = list(p2.get("test_daily_triangle_jsd_mean") or [])
    vm["test_daily_tri_tail_csv"] = tail_csv(daily, 10)
    vm["test_daily_tri_len"] = str(len(daily))
    return _substitute_md(tpl, vm)


def figx5_condition_line(
    *,
    snap: Dict[str, Any],
    p2: Dict[str, Any],
    pol: Any,
    jsd_stress: bool,
) -> Tuple[str, str]:
    """FigX.5 defense-tag：滚动三角 JSD 首次超过动态阈值时触发。

    向 Defense-Tag 模板注入：
      - ``{jsd_alarm_date}``：首次告警日（``YY.MM.DD``，未对齐时为 ``—``）
      - ``{jsd_mean_at_breach}``：首次告警日的滚动三角 JSD 均值（W=semantic_cosine_window）
      - ``{jsd_stress_dyn_thr}``：动态阈值 τ = k × max(jsd_baseline_mean, ε)
      - ``{jsd_alarm_line}``：单行回退串（兼容旧模板）
    """
    dv = defense_validation(snap)
    row = dv.get("research_alarm_day_rolling_jsd_stress")
    iso = iso_test_date(p2, row)
    yymd = iso_to_yymmdd(iso)
    daily_tri = list(p2.get("test_daily_triangle_jsd_mean") or [])
    w = int(getattr(pol, "semantic_cosine_window", 5) or 5)
    breach_val: Optional[float] = None
    try:
        if row is not None:
            breach_val = _rolling_mean_at(daily_tri, int(row), w)
    except (TypeError, ValueError):
        breach_val = None
    breach_val_str = f"{breach_val:.4f}" if breach_val is not None else "—"
    try:
        thr_val, _ = _jsd_threshold_value(p2, pol)
    except Exception:
        thr_val = float(p2.get("jsd_stress_dyn_thr") or 0.0)
    thr_str = f"{float(thr_val or 0.0):.4f}"

    if bool(jsd_stress):
        if iso:
            alarm_line = (
                f"于{yymd}，滚动三角JSD均值={breach_val_str}第一次超过τ={thr_str}"
                f"→{yymd}为首次预警日，防御等级切换至 Level 2"
            )
        else:
            alarm_line = (
                f"滚动三角JSD均值={breach_val_str}第一次超过τ={thr_str}（日序号未对齐）"
                f"→防御等级切换至 Level 2"
            )
    else:
        alarm_line = f"滚动三角JSD在测试集内未超过τ={thr_str}"

    vm = {
        "jsd_stress": "是" if bool(jsd_stress) else "否",
        "jsd_alarm_date": yymd,
        "jsd_mean_at_breach": breach_val_str,
        "jsd_stress_dyn_thr": thr_str,
        "jsd_alarm_line": alarm_line,
    }
    return load_defense_tag_text("5", None, vm, "if" if bool(jsd_stress) else "else")
