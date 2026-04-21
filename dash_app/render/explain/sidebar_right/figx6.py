"""FigX.6 · 语义–数值滚动余弦 — 讲解卡 + defense-tag 条件行。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from dash_app.render.explain._formatters import merge_base_vm
from dash_app.render.explain._loaders import (
    load_defense_tag_text,
    load_figx_template,
    _substitute_md,
)
from dash_app.render.explain.sidebar_right._shared import (
    defense_validation,
    iso_test_date,
    iso_to_yymmdd,
)


def _rolling_cosine_at_breach(
    p2: Dict[str, Any],
    meta: Dict[str, Any],
    window: int,
    row: Optional[int],
) -> Optional[float]:
    """复算首次告警行处的滚动余弦值；与 ``research/phase2.py`` 内的逻辑一致。"""
    if row is None:
        return None
    dates = list(p2.get("test_forecast_dates") or [])
    best_mu = list(p2.get("test_daily_best_model_mu_mean") or [])
    if not dates or len(best_mu) != len(dates):
        return None
    try:
        ii = int(row)
    except (TypeError, ValueError):
        return None
    w = max(2, int(window))
    if ii < w - 1 or ii >= len(dates):
        return None

    st = (meta or {}).get("test_sentiment_st") or {}
    st_dates = st.get("dates") or []
    st_vals = st.get("values") or []
    if not st_dates or len(st_dates) != len(st_vals):
        return None
    try:
        cal_idx = [pd.Timestamp(x) for x in dates]
        st_series = pd.Series(
            [float(v) for v in st_vals],
            index=[pd.Timestamp(x) for x in st_dates],
        )
        st_arr = st_series.reindex(cal_idx).ffill().bfill().to_numpy(dtype=float)
    except Exception:
        return None
    num_arr = pd.Series([float(v) for v in best_mu]).ffill().bfill().to_numpy(dtype=float)
    if st_arr.size != len(dates) or num_arr.size != len(dates):
        return None
    sa = st_arr[ii - w + 1 : ii + 1]
    sb = num_arr[ii - w + 1 : ii + 1]
    if not (np.all(np.isfinite(sa)) and np.all(np.isfinite(sb))):
        return None
    na = float(np.linalg.norm(sa))
    nb = float(np.linalg.norm(sb))
    if na < 1e-15 or nb < 1e-15:
        return None
    return float(np.dot(sa, sb) / (na * nb))


def build_figx6_explain_body(
    ui_mode: Optional[str],
    snap_json: Dict[str, Any],
    pol: Any,
    p2: Dict[str, Any],
    meta: Dict[str, Any],
    symbols: List[str],
    json_path: str,
) -> str:
    """FigX.6 讲解卡：测试窗 S_t 与数值预测的滚动余弦相似度。"""
    _ = json_path
    tpl = load_figx_template("6", ui_mode)
    vm = merge_base_vm(ui_mode, snap_json, pol, p2, meta, symbols)
    vm["cos_w"] = str(int(getattr(pol, "semantic_cosine_window", 5) or 5))
    vm["cosine"] = f"{float(p2.get('cosine_semantic_numeric') or 0.0):.8f}"
    vm["lb_cos"] = "是" if bool(p2.get("logic_break_semantic_cosine_negative")) else "否"
    vm["sem_cos_computed"] = "是" if bool(p2.get("semantic_numeric_cosine_computed")) else "否"
    vm["train_return_ac1"] = f"{float(p2.get('train_return_ac1') or 0.0):.8f}"
    vm["tau_ac1"] = f"{float(getattr(pol, 'tau_return_ac1', -0.08) or -0.08):.4f}"
    vm["logic_break_ac1"] = "是" if bool(p2.get("logic_break_from_ac1")) else "否"
    vm["logic_break_total"] = "是" if bool(p2.get("logic_break")) else "否"
    st = meta.get("test_sentiment_st") or {}
    dates = st.get("dates") or []
    vals = st.get("values") or []
    if dates and vals and len(dates) == len(vals):
        n = min(5, len(vals))
        vm["st_path_tail_md"] = "\n".join(
            f"- `{dates[-k]}` → **{float(vals[-k]):.6f}**" for k in range(n, 0, -1)
        )
    else:
        vm["st_path_tail_md"] = "—"
    return _substitute_md(tpl, vm)


def figx6_condition_line(
    *,
    snap: Dict[str, Any],
    p2: Dict[str, Any],
    pol: Any,
    meta: Dict[str, Any],
    logic_break_cos: bool,
) -> Tuple[str, str]:
    """FigX.6 defense-tag：滚动余弦首次 < 0 时触发（语义–数值背离 → L2）。

    向 Defense-Tag 模板注入：
      - ``{cos_alarm_date}``：首次告警日（``YY.MM.DD``，未对齐时为 ``—``）
      - ``{cos_at_breach}``：首次告警日处的滚动余弦值
      - ``{cos_alarm_line}``：单行回退串（兼容旧模板）
    """
    dv = defense_validation(snap)
    row = dv.get("research_alarm_day_semantic_cosine_negative")
    iso = iso_test_date(p2, row)
    yymd = iso_to_yymmdd(iso)
    w = int(getattr(pol, "semantic_cosine_window", 5) or 5)
    cos_val: Optional[float] = None
    try:
        if row is not None:
            cos_val = _rolling_cosine_at_breach(p2, meta, w, int(row))
    except (TypeError, ValueError):
        cos_val = None
    if cos_val is None and bool(logic_break_cos):
        try:
            cos_val = float(p2.get("cosine_semantic_numeric") or 0.0)
        except (TypeError, ValueError):
            cos_val = None
    cos_val_str = f"{cos_val:.4f}" if cos_val is not None else "—"

    if bool(logic_break_cos):
        if iso:
            alarm_line = (
                f"于{yymd}，语义–数值滚动余弦={cos_val_str}第一次出现负值"
                f"→{yymd}为首次预警日，防御等级切换至 Level 2"
            )
        else:
            alarm_line = (
                f"语义–数值滚动余弦={cos_val_str}第一次出现负值（日序号未对齐）"
                f"→防御等级切换至 Level 2"
            )
    else:
        alarm_line = "语义–数值滚动余弦在测试集内始终 ≥ 0"

    try:
        last_cos = float(p2.get("cosine_semantic_numeric") or 0.0)
        last_cos_str = f"{last_cos:.4f}"
    except (TypeError, ValueError):
        last_cos_str = "—"
    vm = {
        "lb_cos": "是" if bool(logic_break_cos) else "否",
        "cos_alarm_date": yymd,
        "cos_at_breach": cos_val_str,
        "cos_alarm_line": alarm_line,
        "cosine": last_cos_str,
        "cos_w": str(int(getattr(pol, "semantic_cosine_window", 5) or 5)),
    }
    return load_defense_tag_text("6", None, vm, "if" if bool(logic_break_cos) else "else")
