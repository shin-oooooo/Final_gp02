"""FigX.3 · 资产异常诊断 — 讲解卡 + defense-tag 条件行 + 诊断摘要格式化。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from dash_app.render.explain._formatters import merge_base_vm
from dash_app.render.explain._loaders import (
    load_defense_tag_text,
    load_figx_template,
    _substitute_md,
)


def format_adf_diagnostic_detail(d: Dict[str, Any]) -> str:
    """侧栏资产卡第二行小字：与波动/AC1 卡同为简短数值摘要。"""
    if bool(d.get("basic_logic_failure")):
        return f"ADF 未收敛（阶数 {int(d.get('diff_order') or 0)}）"
    p_raw = d.get("adf_p_returns")
    if p_raw is None:
        p_raw = d.get("adf_p")
    p = float(p_raw if p_raw is not None else 1.0)
    return f"未平稳（p={p:.4f}）"


def build_figx3_explain_body(
    ui_mode: Optional[str],
    snap_json: Dict[str, Any],
    pol: Any,
    p2: Dict[str, Any],
    meta: Dict[str, Any],
    symbols: List[str],
    json_path: str,
) -> str:
    """FigX.3 讲解卡：高波动 / 低自相关 / 未过关 ADF 资产三类异常。"""
    from research.defense_state import diagnostic_failed_adf

    _ = json_path
    tpl = load_figx_template("3", ui_mode)
    vm = merge_base_vm(ui_mode, snap_json, pol, p2, meta, symbols)
    p1 = snap_json.get("phase1") or {}
    h_s = float((p1.get("h_struct") or p1.get("H_struct") or 0.0) or 0.0)
    vm["h_struct"] = f"{h_s:.8f}"
    vm["h_struct_short"] = f"{h_s:.4f}"
    vm["tau_h1"] = f"{float(getattr(pol, 'tau_h1', 0.5) or 0.5):.4f}"
    tau_vol = float(getattr(pol, 'tau_vol_melt', 0.32) or 0.32)
    tau_ac1 = float(getattr(pol, 'tau_return_ac1', -0.08) or -0.08)
    vm["tau_vol_melt"] = f"{tau_vol:.2%}"
    vm["tau_return_ac1"] = f"{tau_ac1:.4f}"
    diags = list(p1.get("diagnostics") or [])
    adf_lines: List[str] = []
    for d in diags:
        if diagnostic_failed_adf(d):
            adf_lines.append(f"- **{d.get('symbol', '?')}**：{format_adf_diagnostic_detail(d)}")
    vm["adf_fail_assets_md"] = "\n".join(adf_lines) if adf_lines else "*无未通过 ADF 的标的*"
    vol_items = []
    ac1_items = []
    for d in diags:
        va = float(d.get("vol_ann") or 0.0)
        a1 = float(d.get("ac1") or 0.0)
        if va > tau_vol:
            vol_items.append(f"- **{d.get('symbol', '?')}**：年化波动 {va:.2%}")
        if a1 < tau_ac1:
            ac1_items.append(f"- **{d.get('symbol', '?')}**：AC1 = {a1:.4f}")
    vm["vol_assets_md"] = "\n".join(vol_items) if vol_items else "*无高波动资产*"
    vm["ac1_assets_md"] = "\n".join(ac1_items) if ac1_items else "*无低自相关资产*"
    return _substitute_md(tpl, vm)


def figx3_condition_line(
    *,
    adf_fail_assets: List[Dict[str, Any]],
    vol_assets: List[Dict[str, Any]],
    ac1_assets: List[Dict[str, Any]],
    tau_vol_melt: float,
    tau_return_ac1: float,
) -> Tuple[str, str]:
    """FigX.3 defense-tag：ADF 未过关 / 高波动 / 低 AC1 任一触发 warn。"""
    vm = {
        "tau_vol_melt": f"{float(tau_vol_melt):.2%}",
        "tau_return_ac1": f"{float(tau_return_ac1):.4f}",
        "vol_assets_csv": ", ".join(a["symbol"] for a in vol_assets) if vol_assets else "无",
        "ac1_assets_csv": ", ".join(a["symbol"] for a in ac1_assets) if ac1_assets else "无",
        "vol_count": str(len(vol_assets)),
        "ac1_count": str(len(ac1_assets)),
    }
    has_anomaly = bool(adf_fail_assets) or bool(vol_assets) or bool(ac1_assets)
    if not has_anomaly:
        return load_defense_tag_text("3", None, vm, "else")

    parts: List[str] = []
    for a in adf_fail_assets:
        parts.append(f"{a['symbol']} ADF 检验未通过（{a['value']}）")
    for a in vol_assets:
        parts.append(f"{a['symbol']} 年化波动 {a['value']} 高于阈值 {vm['tau_vol_melt']}")
    for a in ac1_assets:
        parts.append(f"{a['symbol']} 一阶自相关系数 {a['value']} 低于阈值 {vm['tau_return_ac1']}")
    body = "；".join(parts) + " → 防御等级切换至 Level 1"
    return body, "warn"
