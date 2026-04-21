"""FigX.2 · 结构熵 — 讲解卡 + defense-tag 条件行。"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from dash_app.render.explain._formatters import (
    ENTROPY_WINDOW_DEFAULT,
    compute_figx2_physics_vars,
    merge_base_vm,
)
from dash_app.render.explain._loaders import (
    load_defense_tag_text,
    load_figx_template,
    _substitute_md,
)


def build_figx2_explain_body(
    ui_mode: Optional[str],
    snap_json: Dict[str, Any],
    pol: Any,
    p2: Dict[str, Any],
    meta: Dict[str, Any],
    symbols: List[str],
    json_path: str,
) -> str:
    """FigX.2 讲解卡：结构熵与 Level 判定。"""
    tpl = load_figx_template("2", ui_mode)
    vm = merge_base_vm(ui_mode, snap_json, pol, p2, meta, symbols)
    p1 = snap_json.get("phase1") or {}
    vm["tau_h_gamma"] = f"{float(getattr(pol, 'tau_h_gamma', 0.4) or 0.4):.4f}"
    vm["gamma_multiplier"] = f"{float(p1.get('gamma_multiplier') or 1.0):.4f}"
    vm["entropy_window"] = str(ENTROPY_WINDOW_DEFAULT)
    h_s = float((p1.get("h_struct") or p1.get("H_struct") or 0.0) or 0.0)
    vm["h_struct"] = f"{h_s:.8f}"
    vm["h_struct_short"] = f"{h_s:.4f}"
    vm.update(compute_figx2_physics_vars(json_path, snap_json, symbols))
    try:
        na_s = str(vm.get("p1_n_assets") or "").strip()
        na = int(na_s) if na_s.isdigit() else 0
        if na >= 2 and h_s > 0 and math.isfinite(h_s):
            vm["p1_h_raw_from_h"] = f"{float(h_s * math.log(na)):.10f}"
        else:
            vm["p1_h_raw_from_h"] = "—"
    except Exception:
        vm["p1_h_raw_from_h"] = "—"
    return _substitute_md(tpl, vm)


def figx2_condition_line(
    *,
    h_struct: float,
    tau_h1: float,
) -> Tuple[str, str]:
    """FigX.2 defense-tag：H_struct < τ_H1 → Level 1 警示。"""
    vm = {
        "h_struct_short": f"{float(h_struct):.4f}",
        "h_struct": f"{float(h_struct):.8f}",
        "tau_h1": f"{float(tau_h1):.4f}",
    }
    if float(h_struct) < float(tau_h1):
        vm["figx2_trigger_line"] = f"H_struct={float(h_struct):.3f}<τ_h1={float(tau_h1):.3f}"
        return load_defense_tag_text("2", None, vm, "if")
    return load_defense_tag_text("2", None, vm, "else")
