"""Fig 4.2 结论卡（独立）— 按 5 情形分支从共用源 ``p4_conclusion_analysis.md`` 提取文案。

**对外接口**（对调用端保持黑盒稳定）：
* :func:`classify_fig42_case` — 根据 ``defense_level`` + ``test_equity_*`` +
  ``test_mdd_pct_*`` + ``test_terminal_cumret_*`` 返回 ``"A"/"B"/"C"/"D"/"E"/"N"``。
* :func:`build_fig42_conclusion_card` — 独立 ``dbc.Card``，风格与
  :func:`dash_app.fig41.render.build_fig41_conclusion_card` 对齐。

**文案来源（R3 变更）**：共用源 ``content-{LANG}/p4_conclusion_analysis.md``，
按 ``## Fig4.2 · 情形 X`` 命名空间索引（与 Fig 4.1 的 ``## Fig4.1 · 情形 X``
严格区分）。``Fig4.2-Res.md §9`` 已被掏空，仅保留指向本共用源的引用说明，
以避免"两处定义"冲突。
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import dash_bootstrap_components as dbc
from dash import dcc, html

from dash_app.services.copy import get_language, get_md_text, get_status_message

# 蓝红重合（Level 0 下 CVaR ≡ Max-Sharpe）逐点阈值
_OVERLAP_EPS = 1e-9

# 共用源按 H2 命名空间索引：CHN → ``## Fig4.2 · 情形 X``；ENG → ``## Fig4.2 · Case X``。
# 一段情形截至下一个 ``## ``（含 ``### `` 子节）。
def _fig42_case_headers(lang: Optional[str] = None) -> Dict[str, str]:
    """语言感知的 H2 标题表：情形 A-E → 对应 header 字符串。"""
    lang_s = (lang or get_language() or "chn").lower()
    case_word = "情形" if lang_s == "chn" else "Case"
    return {c: f"## Fig4.2 · {case_word} {c}" for c in "ABCDE"}


# --------------------------------------------------------------------------- #
# 情形分类（纯函数）                                                            #
# --------------------------------------------------------------------------- #


def classify_fig42_case(snap_json: Dict[str, Any], dv: Dict[str, Any]) -> str:
    """返回 ``"A"/"B"/"C"/"D"/"E"/"N"``（N = 数据不足，不走 §9 任何分支）。

    判定规则（与 ``Fig4.2-Res.md §9.1`` 完全对齐）：

    * A: ``defense_level == 0`` 且 ``test_equity_cvar ≡ test_equity_max_sharpe``（逐点）。
    * B: ``defense_level == 0`` 且 两条曲线出现可察觉偏离。
    * C: ``defense_level >= 1`` 且 ``|MDD_cvar|`` 最小 且 ``cumret_cvar`` 最高。
    * D: ``defense_level >= 1`` 且 ``|MDD_cvar|`` 最小 且 ``cumret_cvar`` 非最高。
    * E: ``defense_level >= 1`` 且 ``|MDD_cvar|`` 非最小（不论 cumret）。
    * N: 任一分类所需字段缺失（未运行管线或快照残缺）。
    """
    try:
        level = int((snap_json or {}).get("defense_level") or 0)
    except (TypeError, ValueError):
        level = 0

    eq_ms = (dv or {}).get("test_equity_max_sharpe")
    eq_cv = (dv or {}).get("test_equity_cvar")

    if level == 0:
        # Level 0：判断红线与蓝线是否逐点重合
        if not isinstance(eq_ms, list) or not isinstance(eq_cv, list) or not eq_ms:
            return "N"
        if len(eq_ms) != len(eq_cv):
            return "B"
        try:
            diffs = [abs(float(a) - float(b)) for a, b in zip(eq_ms, eq_cv)]
        except (TypeError, ValueError):
            return "B"
        return "A" if all(d < _OVERLAP_EPS for d in diffs) else "B"

    # level >= 1
    mdd_vals = [
        (dv or {}).get("test_mdd_pct_max_sharpe"),
        (dv or {}).get("test_mdd_pct_custom_weights"),
        (dv or {}).get("test_mdd_pct_cvar"),
    ]
    cum_vals = [
        (dv or {}).get("test_terminal_cumret_max_sharpe"),
        (dv or {}).get("test_terminal_cumret_custom_weights"),
        (dv or {}).get("test_terminal_cumret_cvar"),
    ]
    if any(v is None for v in mdd_vals) or any(v is None for v in cum_vals):
        return "N"
    try:
        abs_mdds = [abs(float(v)) for v in mdd_vals]
        cums = [float(v) for v in cum_vals]
    except (TypeError, ValueError):
        return "N"
    if not all(math.isfinite(x) for x in (*abs_mdds, *cums)):
        return "N"

    cvar_mdd_min = abs_mdds[2] <= min(abs_mdds)
    cvar_cumret_max = cums[2] >= max(cums)
    if cvar_mdd_min and cvar_cumret_max:
        return "C"
    if cvar_mdd_min and not cvar_cumret_max:
        return "D"
    return "E"


# --------------------------------------------------------------------------- #
# md 加载与 §9.1 / §9.2 切片                                                   #
# --------------------------------------------------------------------------- #


def _read_conclusion_md() -> str:
    """读取共用源 ``content-{LANG}/p4_conclusion_analysis.md``；语言 fallback 由
    ``get_md_text`` 内部处理（CHN 为最终回退）。"""
    _ = get_language()  # noqa: F841 — 仅为触发语言缓存，实际读取由 get_md_text 完成
    return get_md_text("p4_conclusion_analysis.md", "")


def _extract_h2_block(text: str, header: str) -> str:
    """从 ``header`` 起截到下一个 ``## `` 之前；不包含下一个 H2。保留 ``### `` 子节。"""
    idx = text.find(header)
    if idx == -1:
        return ""
    rest = text[idx:]
    next_idx = rest.find("\n## ", 1)
    return rest if next_idx == -1 else rest[:next_idx]


def _extract_case_prose(md: str, case: str) -> str:
    """根据情形 letter（A/B/C/D/E）只截取对应 ``## Fig4.2 · 情形 X`` 段（ENG 为 ``Case X``）。

    与 Fig 4.1 结论卡不同，Fig 4.2 **不**再拼接"论点"段；所有应展示的前提在各情形
    内部已经说清楚，避免在窄卡里重复叙述。情形 E 的段落在共用源里已包含
    ``### E-1 / ### E-2`` 归因子节与"方法局限性"子节，无需额外拼接。

    当前语言由 :func:`get_language` 决定；ENG 模式下 header 自动切换为 "Case X"。
    """
    headers = _fig42_case_headers()
    header = headers.get(case, "")
    return _extract_h2_block(md, header) if header else ""


# --------------------------------------------------------------------------- #
# 占位符替换（与 build_fig42_body 的 vm 共源）                                  #
# --------------------------------------------------------------------------- #


def _fmt_num(x: Any) -> str:
    if x is None:
        return "—"
    try:
        xf = float(x)
        return f"{xf:.4f}" if math.isfinite(xf) else "—"
    except (TypeError, ValueError):
        return "—"


def _fmt_mdd(x: Any) -> str:
    if x is None:
        return "—"
    try:
        xf = float(x)
        return f"{xf:.2f}" if math.isfinite(xf) else "—"
    except (TypeError, ValueError):
        return "—"


def _mc_flags(dv: Dict[str, Any]) -> Dict[str, str]:
    """与 build_fig42_body 相同的 mc_pass / mc_mdd_pass / defense_pass 计算。"""
    mc_pass = "否"
    mc_mdd_pass = "否"
    if dv.get("comparison_active"):
        try:
            ap5 = dv.get("actual_stress_p5_terminal")
            bp5 = dv.get("baseline_stress_p5_terminal")
            if ap5 is not None and bp5 is not None and float(ap5) >= float(bp5):
                mc_pass = "是"
        except (TypeError, ValueError):
            pass
        try:
            amdd = dv.get("actual_mdd_p95_pct")
            bmdd = dv.get("baseline_mdd_p95_pct")
            if amdd is not None and bmdd is not None and float(amdd) <= float(bmdd):
                mc_mdd_pass = "是"
        except (TypeError, ValueError):
            pass
    return {
        "mc_pass": mc_pass,
        "mc_mdd_pass": mc_mdd_pass,
        "defense_pass": "是" if (mc_pass == "是" and mc_mdd_pass == "是") else "否",
    }


def _build_vm(dv: Dict[str, Any]) -> Dict[str, str]:
    vm: Dict[str, str] = {
        "term_ms": _fmt_num(dv.get("test_terminal_cumret_max_sharpe")),
        "term_cw": _fmt_num(dv.get("test_terminal_cumret_custom_weights")),
        "term_cv": _fmt_num(dv.get("test_terminal_cumret_cvar")),
        "term_mdd_ms": _fmt_mdd(dv.get("test_mdd_pct_max_sharpe")),
        "term_mdd_cw": _fmt_mdd(dv.get("test_mdd_pct_custom_weights")),
        "term_mdd_cv": _fmt_mdd(dv.get("test_mdd_pct_cvar")),
        # 结论卡不重复展开 mc_content（主讲解卡里已有）；保留占位提示
        "mc_content": "（MC 反事实详情见 Fig 4.2 讲解卡）",
    }
    vm.update(_mc_flags(dv))
    return vm


def _substitute(text: str, vm: Dict[str, str]) -> str:
    out = text
    for k in sorted(vm.keys(), key=len, reverse=True):
        key = "{" + k + "}"
        if key in out:
            out = out.replace(key, str(vm[k]))
    return out


# --------------------------------------------------------------------------- #
# 公共入口                                                                      #
# --------------------------------------------------------------------------- #


def build_fig42_conclusion_card(
    snap_json: Dict[str, Any],
    dv: Dict[str, Any],
    ui_mode: Optional[str] = None,
) -> Any:
    """Fig 4.2 结论卡 — 与 Fig4.1 结论卡风格一致的独立 ``dbc.Card``。

    Args:
        snap_json: 管线快照（``phase3.defense_level`` 等）。
        dv: ``phase3.defense_validation``；可以是空 dict。
        ui_mode: ``"invest"`` / ``"research"``；当前仅影响语言 fallback（中/英）。

    Returns:
        dbc.Card — 头部显示 "Figure 4.2 · 结论分析"，正文为对应情形的 markdown 文本。
    """
    _ = ui_mode  # 预留
    title = get_status_message("fig42_conclusion_title", "Figure 4.2 · 结论分析")

    dv = dv if isinstance(dv, dict) else {}
    snap = snap_json if isinstance(snap_json, dict) else {}
    case = classify_fig42_case(snap, dv)

    md = _read_conclusion_md()
    if case == "N" or not md:
        body_md = get_status_message(
            "fig42_conclusion_no_data",
            "（数据不足或未运行管线；请点击 **保存运行** 后结论将自动按情形刷新。）",
        )
    else:
        body_md = _extract_case_prose(md, case)
        if not body_md:
            body_md = (
                f"（情形 {case}：未能在 `content-{{LANG}}/p4_conclusion_analysis.md` 定位到对应 H2，"
                "请检查 md 是否包含 `## Fig4.2 · 情形 X` 起首的标题。）"
            )
        body_md = _substitute(body_md, _build_vm(dv))

    return dbc.Card(
        [
            dbc.CardHeader(title, className="py-2 small fw-bold"),
            dbc.CardBody(
                dcc.Markdown(body_md, className="small phase-doc-body mb-0"),
                className="p-3",
            ),
        ],
        className="mb-2 border-secondary shadow-sm",
    )
