"""FigX.4 · 可信度评分 + 三态灯 — 讲解卡 + defense-tag 条件行。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dash_app.render.explain._formatters import (
    fmt_dict_md_row,
    fmt_traffic_md,
    merge_base_vm,
)
from dash_app.render.explain._loaders import (
    load_defense_tag_text,
    load_figx_template,
    _substitute_md,
)


def build_figx4_explain_body(
    ui_mode: Optional[str],
    snap_json: Dict[str, Any],
    pol: Any,
    p2: Dict[str, Any],
    meta: Dict[str, Any],
    symbols: List[str],
    json_path: str,
) -> str:
    """FigX.4 讲解卡：可信度评分与 NLL / DM / 覆盖率 三态灯。"""
    _ = json_path
    tpl = load_figx_template("4", ui_mode)
    vm = merge_base_vm(ui_mode, snap_json, pol, p2, meta, symbols)
    vm["credibility_base_jsd"] = f"{float(p2.get('credibility_base_jsd') or 0.0):.8f}"
    vm["credibility_coverage_penalty"] = f"{float(p2.get('credibility_coverage_penalty') or 0.0):.8f}"
    vm["density_test_failed"] = "是" if bool(p2.get("density_test_failed")) else "否"
    pcn = p2.get("prob_coverage_naive")
    vm["prob_coverage_naive"] = f"{float(pcn):.6f}" if pcn is not None else "—"
    vm["cred_alpha"] = f"{float(getattr(pol, 'credibility_baseline_jsd_scale', 6.0) or 6.0):.4f}"
    vm["cred_beta_pen"] = f"{float(getattr(pol, 'credibility_penalty_jsd_scale', 0.12) or 0.12):.4f}"
    vm["cred_pen_cap"] = f"{float(getattr(pol, 'credibility_penalty_cap', 0.35) or 0.35):.4f}"
    vm["cred_min"] = f"{float(getattr(pol, 'credibility_score_min', -0.5) or -0.5):.4f}"
    vm["cred_max"] = f"{float(getattr(pol, 'credibility_score_max', 1.0) or 1.0):.4f}"
    vm["jsd_triangle_mean"] = f"{float(p2.get('jsd_triangle_mean') or 0.0):.8f}"
    vm["prob_nll_md"] = fmt_dict_md_row("平均 NLL", p2.get("prob_nll_mean"))
    vm["prob_dm_p_md"] = fmt_dict_md_row("DM p 值（对 Naive）", p2.get("prob_dm_pvalue_vs_naive"))
    vm["prob_cov_md"] = fmt_dict_md_row("名义 95% 实证覆盖率", p2.get("prob_coverage_95"))
    vm["traffic_lights_md"] = fmt_traffic_md(p2.get("model_traffic_light"))
    vm["prob_full_fail"] = "是" if bool(p2.get("prob_full_pipeline_failure")) else "否"
    return _substitute_md(tpl, vm)


def figx4_condition_line(*, c: float, tau_l2: float, tau_l1: float) -> Tuple[str, str]:
    """FigX.4 defense-tag：c ≤ τ_L2 → L2；τ_L2 < c ≤ τ_L1 → L1；else 基准。"""
    c = float(c)
    tl2 = float(tau_l2)
    tl1 = float(tau_l1)
    vm = {
        "credibility": f"{c:.8f}",
        "tau_l2": f"{tl2:.4f}",
        "tau_l1": f"{tl1:.4f}",
    }
    if c <= tl2:
        return load_defense_tag_text("4", None, vm, "if")
    if tl2 < c <= tl1:
        return load_defense_tag_text("4", None, vm, "elif_0")
    return load_defense_tag_text("4", None, vm, "else")
