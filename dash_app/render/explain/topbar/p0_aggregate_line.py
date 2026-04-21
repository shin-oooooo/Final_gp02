"""顶栏 Phase 0 聚合条件行 — 与 resolve_defense_level 驱动项对齐。"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from dash_app.render.explain._loaders import load_defense_tag_text


def p0_aggregate_condition_line(
    *,
    defense_level: int,
    snap: Dict[str, Any],
    p1: Dict[str, Any],
    p2: Dict[str, Any],
    pol_tau_h1: float,
    pol_tau_l2: float,
    pol_tau_l1: float,
    pol_tau_s_low: float,
    s_min: float,
) -> Tuple[str, str]:
    """Phase 0 strip：一行文字，列出本次 Level 由哪些驱动项触发。"""
    from research.defense_state import any_adf_asset_failure

    _ = snap  # 保留签名兼容；当前仅使用 p1/p2 参数
    c = float(p2.get("credibility_score", p2.get("consistency_score", 0.5)) or 0.5)
    h = float(p1.get("h_struct", 1.0) or 1.0)
    adf_bad = any_adf_asset_failure(list(p1.get("diagnostics") or []))
    jsd = bool(p2.get("jsd_stress"))
    lb = bool(p2.get("logic_break_semantic_cosine_negative"))
    pf = bool(p2.get("prob_full_pipeline_failure"))
    s_def = float(s_min)

    parts: list[str] = []
    if int(defense_level) >= 2:
        if c <= float(pol_tau_l2):
            parts.append(f"可信度 c={c:.4f}≤τ_L2")
        if jsd:
            parts.append("JSD 应力触发")
        if lb:
            parts.append("滚动余弦<0")
        if not parts:
            parts.append("Level 2（聚合判定）")
        line = "；".join(parts)
        vm = {"p0_aggregate_line": line}
        return load_defense_tag_text("P0-Agg", None, vm, "if")
    if int(defense_level) == 1:
        if adf_bad:
            parts.append("存在标的 ADF 未过关")
        if h < float(pol_tau_h1):
            parts.append(f"H_struct={h:.3f}<τ_h1")
        if pf:
            parts.append("概率预测全流程失效")
        if float(pol_tau_l2) < c <= float(pol_tau_l1):
            parts.append(f"τ_L2<c≤τ_L1（c={c:.4f}）")
        if c > float(pol_tau_l1) and s_def < float(pol_tau_s_low):
            parts.append(f"min(S_t)={s_def:.3f}<τ_S_low")
        if not parts:
            parts.append("Level 1（聚合判定）")
        line = "；".join(parts)
        vm = {"p0_aggregate_line": line}
        return load_defense_tag_text("P0-Agg", None, vm, "elif_0")
    vm = {"p0_aggregate_line": "未触发 resolve_defense_level 的 Level 1/2 主条件"}
    return load_defense_tag_text("P0-Agg", None, vm, "else")
