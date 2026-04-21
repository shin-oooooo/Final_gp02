"""Fig4.2 讲解正文 — 防御策略有效性检验（三权重测试窗对照）。"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from dash_app.render.explain._loaders import load_fig4_template, _substitute_md


def build_fig42_body(
    ui_mode: Optional[str],
    snap_json: Dict[str, Any],
    dv: Dict[str, Any],
) -> str:
    """Fig4.2 讲解正文（三权重累计回报 + MDD + MC 反事实）。"""
    _ = snap_json  # 保留签名兼容；当前仅使用 dv
    tpl = load_fig4_template("2", ui_mode)
    vm: Dict[str, Any] = {}
    tm = dv.get("test_terminal_cumret_max_sharpe")
    tc = dv.get("test_terminal_cumret_custom_weights")
    tv = dv.get("test_terminal_cumret_cvar")
    vm["term_ms"] = f"{float(tm):.4f}" if tm is not None else "—"
    vm["term_cw"] = f"{float(tc):.4f}" if tc is not None else "—"
    vm["term_cv"] = f"{float(tv):.4f}" if tv is not None else "—"

    def _fmt_mdd(x: Any) -> str:
        if x is None:
            return "—"
        try:
            xf = float(x)
            return f"{xf:.2f}" if math.isfinite(xf) else "—"
        except Exception:
            return "—"

    vm["term_mdd_ms"] = _fmt_mdd(dv.get("test_mdd_pct_max_sharpe"))
    vm["term_mdd_cw"] = _fmt_mdd(dv.get("test_mdd_pct_custom_weights"))
    vm["term_mdd_cv"] = _fmt_mdd(dv.get("test_mdd_pct_cvar"))

    mc_parts: List[str] = []
    if not dv.get("comparison_active"):
        mc_parts = [
            "**蒙特卡洛反事实**：当前为 **Level 0**，与「始终 Max-Sharpe」一致，无额外尾部对照。",
            "在 **Level 1/2** 时，此处追加**相同随机种子**下实际权重 vs Level0 权重的含跳 5% 分位与 MDD 对照。",
        ]
    else:
        ap5 = dv.get("actual_stress_p5_terminal")
        bp5 = dv.get("baseline_stress_p5_terminal")
        lift = dv.get("stress_p5_terminal_lift_pct")
        amdd = dv.get("actual_mdd_p95_pct")
        bmdd = dv.get("baseline_mdd_p95_pct")
        mddi = dv.get("mdd_p95_improvement_pctpts")
        tr_a = dv.get("test_cumulative_return_actual")
        tr_b = dv.get("test_cumulative_return_baseline")
        dd_a = dv.get("test_max_drawdown_pct_actual")
        dd_b = dv.get("test_max_drawdown_pct_baseline")
        mc_parts = [
            "**防御有效性验证（MC）**（反事实：始终 max-Sharpe；与主图相同跳跃与情景注入）",
            "",
            f"- **含跳终端财富 5% 分位**：实际 {_fmt_mdd(ap5)} vs 反事实 Level 0 {_fmt_mdd(bp5)}",
        ]
        if lift is not None:
            try:
                lf = float(lift)
                if math.isfinite(lf):
                    mc_parts.append(
                        f"- **5% 分位相对变化**（(实际−反事实)/|反事实|×100%）：**{lf:+.2f}%** "
                        "（正值表示压力情景下终端财富左尾更高）"
                    )
            except (TypeError, ValueError):
                pass
        mc_parts.append(
            f"- **含跳路径最大回撤的 95% 分位（%）**：实际 {_fmt_mdd(amdd)} vs 反事实 {_fmt_mdd(bmdd)}"
        )
        if mddi is not None:
            try:
                mi = float(mddi)
                if math.isfinite(mi):
                    mc_parts.append(
                        f"- **MDD 的 95% 分位差（反事实−实际，百分点）**：**{mi:+.2f}** "
                        "（正值表示防御降低了尾部回撤上界）"
                    )
            except (TypeError, ValueError):
                pass
        if tr_a is not None or tr_b is not None:
            def _fmt_ret(x: Any) -> str:
                if x is None:
                    return "—"
                try:
                    xf = float(x)
                    return f"{xf:.4f}" if math.isfinite(xf) else "—"
                except Exception:
                    return "—"
            mc_parts.extend(
                [
                    "",
                    "**测试窗已实现（实际防御权重 vs 反事实 Level0）**",
                    f"- 累计收益：实际 {_fmt_ret(tr_a)} vs 反事实 {_fmt_ret(tr_b)}",
                    f"- 最大回撤 %：实际 {_fmt_ret(dd_a)} vs 反事实 {_fmt_ret(dd_b)}",
                ]
            )
    vm["mc_content"] = "\n".join(mc_parts)

    # Meets expectation: actual >= baseline for p5 terminal, actual <= baseline for MDD
    mc_pass = "否"
    mc_mdd_pass = "否"
    if dv.get("comparison_active"):
        ap5 = dv.get("actual_stress_p5_terminal")
        bp5 = dv.get("baseline_stress_p5_terminal")
        if ap5 is not None and bp5 is not None:
            try:
                if float(ap5) >= float(bp5):
                    mc_pass = "是"
            except (TypeError, ValueError):
                pass
        amdd = dv.get("actual_mdd_p95_pct")
        bmdd = dv.get("baseline_mdd_p95_pct")
        if amdd is not None and bmdd is not None:
            try:
                if float(amdd) <= float(bmdd):
                    mc_mdd_pass = "是"
            except (TypeError, ValueError):
                pass
    vm["mc_pass"] = mc_pass
    vm["mc_mdd_pass"] = mc_mdd_pass
    vm["defense_pass"] = "是" if mc_pass == "是" and mc_mdd_pass == "是" else "否"
    return _substitute_md(tpl, vm)
