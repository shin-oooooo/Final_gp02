"""Fig4.1 讲解正文（fallback 路径；主路径走 ``dash_app.fig41.render``）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from dash_app.render.explain._formatters import merge_base_vm
from dash_app.render.explain._loaders import load_fig4_template, _substitute_md


def build_fig41_explain_body(
    ui_mode: Optional[str],
    snap_json: Dict[str, Any],
    pol: Any,
    p2: Dict[str, Any],
    meta: Dict[str, Any],
    symbols: List[str],
) -> str:
    """Fig4.1 fallback 讲解（当快照缺少 post-alarm 数据时展示）。"""
    tpl = load_fig4_template("1", ui_mode)
    vm = merge_base_vm(ui_mode, snap_json, pol, p2, meta, symbols)
    vm["jsd_triangle_mean"] = f"{float(p2.get('jsd_triangle_mean') or 0.0):.8f}"
    vm["jsd_stress_dyn_thr"] = f"{float(meta.get('jsd_stress_dyn_thr', 0.0) or 0.0):.8f}"
    vm["jsd_stress"] = "是" if bool(p2.get("jsd_stress")) else "否"
    vm["jsd_stress_no"] = "否" if bool(p2.get("jsd_stress")) else "是"
    vm["jsd_baseline_mean"] = f"{float(p2.get('jsd_baseline_mean') or 0.0):.8f}"
    vm["k_jsd"] = f"{float(getattr(pol, 'k_jsd', 2.0) or 2.0):.4f}"
    vm["jsd_baseline_eps"] = f"{float(getattr(pol, 'jsd_baseline_eps', 1e-9) or 1e-9):.4e}"
    vm["cos_w"] = str(int(getattr(pol, "semantic_cosine_window", 5) or 5))
    vm["cosine"] = f"{float(p2.get('cosine_semantic_numeric') or 0.0):.8f}"
    vm["lb_cos"] = "是" if bool(p2.get("logic_break_semantic_cosine_negative")) else "否"
    vm["cosine_ge_zero"] = "是" if not bool(p2.get("logic_break_semantic_cosine_negative")) else "否"
    vm["logic_break_total"] = "是" if bool(p2.get("logic_break")) else "否"

    # 预警失效日验证
    p3 = snap_json.get("phase3") or {}
    dv = p3.get("defense_validation") or {}
    leads = []
    lead_names = {
        "research_lead_ref_vs_h_struct": "结构熵",
        "research_lead_ref_vs_jsd_stress": "JSD 应力",
        "research_lead_ref_vs_credibility": "可信度",
        "research_lead_ref_vs_semantic_cosine": "语义余弦",
    }
    for k, name in lead_names.items():
        v = dv.get(k)
        if v is not None:
            try:
                iv = int(v)
                leads.append(f"{name} 提前 {iv} 个交易日")
            except (TypeError, ValueError):
                pass
    vm["early_warning_signals"] = "、".join(leads) if leads else "无"
    vm["early_warning_leads_md"] = "\n".join(f"- {x}" for x in leads) if leads else "- 无有效提前量"
    has_lead = any(
        dv.get(k) is not None and 1 <= int(dv.get(k)) <= 5
        for k in lead_names
    )
    vm["early_warning_valid"] = "是" if has_lead else "否"
    vm["research_failure_ref_label"] = str(dv.get("research_failure_ref_label") or "价格不稳参照日")
    return _substitute_md(tpl, vm)
