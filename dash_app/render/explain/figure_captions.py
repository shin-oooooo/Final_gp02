"""FigX.* 讲解卡片通用变量注入 + bundle 组装。

**外部 API**（与原 ``figure_caption_service.build_figure_caption_bundle`` 完全兼容）：
    build_figure_caption_bundle(ui_mode, snap_json, pol, p2, meta, *, jsd_thr_precomputed=None)

内部职责：
* 从 ``assets/figure_captions.json`` 装 FigX 讲解模板（按 invest / research 分支）
* 组装注入变量（:func:`_fmt_vars`）
* 替换模板占位符（:func:`_apply_template`）
* 输出 ``{key: {"title": str, "body": str}}`` 字典

``_fmt_vars`` 被 ``render/explain/_formatters.merge_base_vm`` 作为基础复用，
因此保留为模块级公开（下划线仅表示"内部模块"约定）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


_CAPTION_CACHE: Optional[Dict[str, Any]] = None
# Lazy: avoid circular dependency with render.state at import time
_jsd_dynamic_threshold_fn: Any = None


def _caption_json_path() -> Path:
    return Path(__file__).resolve().parents[2] / "assets" / "figure_captions.json"


def load_caption_templates() -> Dict[str, Any]:
    """Load ``assets/figure_captions.json``（缓存到进程内）。"""
    global _CAPTION_CACHE
    if _CAPTION_CACHE is not None:
        return _CAPTION_CACHE
    p = _caption_json_path()
    if not p.is_file():
        _CAPTION_CACHE = {"invest": {}, "research": {}}
        return _CAPTION_CACHE
    with p.open(encoding="utf-8") as f:
        _CAPTION_CACHE = json.load(f)
    return _CAPTION_CACHE


def _jsd_threshold_value(p2: Dict[str, Any], pol: Any) -> Tuple[float, float]:
    """Runtime JSD 动态阈值 + 用于展示的 ε。惰性加载 :func:`jsd_dynamic_threshold`。"""
    global _jsd_dynamic_threshold_fn
    if _jsd_dynamic_threshold_fn is None:
        from dash_app.render.state import jsd_dynamic_threshold as _fn

        _jsd_dynamic_threshold_fn = _fn
    try:
        _eps = float(getattr(pol, "jsd_baseline_eps", 1e-9) or 1e-9)
        jsd_thr = float(
            _jsd_dynamic_threshold_fn(
                p2,
                float(getattr(pol, "k_jsd", 2.0) or 2.0),
                baseline_eps=_eps,
            )
        )
        return jsd_thr, _eps
    except Exception:
        try:
            _eps = float(getattr(pol, "jsd_baseline_eps", 1e-9) or 1e-9)
        except Exception:
            _eps = 1e-9
        return 0.0, _eps


def _fmt_vars(
    ui_mode: str,
    snap_json: Dict[str, Any],
    pol: Any,
    p2: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    jsd_thr_precomputed: Optional[float] = None,
) -> Dict[str, Any]:
    """组装 FigX 讲解模板的通用变量字典。"""
    from research.defense_state import diagnostic_failed_adf

    p0 = snap_json.get("phase0") or {}
    p1 = snap_json.get("phase1") or {}
    rw = (p0.get("meta") or {}).get("resolved_windows") or {}
    te_idx = p0.get("test_index") or []
    _train_s = str(rw.get("train_start") or "—")
    _train_e = str(rw.get("train_end") or "—")
    test_start = str(rw.get("test_start") or (te_idx[0] if te_idx else "—"))
    test_end = str(rw.get("test_end") or (te_idx[-1] if te_idx else "—"))
    h_struct = float((p1.get("h_struct") or p1.get("H_struct") or 0.0) or 0.0)
    h_struct_short = f"{h_struct:.4f}"
    tau_h1 = float(getattr(pol, "tau_h1", 0.5) or 0.5)
    tau_h_gamma = float(getattr(pol, "tau_h_gamma", 0.4) or 0.4)
    gamma_multiplier = float((p1.get("gamma_multiplier") if isinstance(p1, dict) else None) or 1.0)
    tau_l2 = float(getattr(pol, "tau_l2", 0.45) or 0.45)
    tau_l1 = float(getattr(pol, "tau_l1", 0.70) or 0.70)
    jsd_tri = float(p2.get("jsd_triangle_mean") or 0.0)
    if jsd_thr_precomputed is not None:
        try:
            _eps = float(getattr(pol, "jsd_baseline_eps", 1e-9) or 1e-9)
        except Exception:
            _eps = 1e-9
        jsd_thr = float(jsd_thr_precomputed)
    else:
        jsd_thr, _eps = _jsd_threshold_value(p2, pol)
    consistency = float(p2.get("credibility_score", p2.get("consistency_score")) or 0.0)
    credibility = consistency
    defense_level = int(snap_json.get("defense_level", 0))
    cos_w = int(getattr(pol, "semantic_cosine_window", 5) or 5)
    cosine = float(p2.get("cosine_semantic_numeric") or 0.0)
    lb_cos = "是" if bool(p2.get("logic_break_semantic_cosine_negative")) else "否"
    jsd_stress = "是" if bool(p2.get("jsd_stress")) else "否"
    _diags = list(p1.get("diagnostics") or [])
    adf_fail_count = sum(1 for d in _diags if diagnostic_failed_adf(d))
    sentiment = -0.1
    try:
        s2 = snap_json.get("sentiment_anchor")
        if s2 is not None:
            sentiment = float(s2)
    except (TypeError, ValueError):
        sentiment = -0.1
    return {
        "ui_mode": ui_mode,
        "test_start": test_start,
        "test_end": test_end,
        "train_start": _train_s,
        "train_end": _train_e,
        "h_struct": h_struct,
        "h_struct_short": h_struct_short,
        "tau_h1": tau_h1,
        "tau_h_gamma": f"{tau_h_gamma:.4f}",
        "gamma_multiplier": f"{gamma_multiplier:.4f}",
        "tau_l2": tau_l2,
        "tau_l1": tau_l1,
        "jsd_tri": jsd_tri,
        "jsd_thr": jsd_thr,
        "jsd_baseline_eps": f"{float(_eps):.4e}",
        "credibility": credibility,
        "consistency": consistency,
        "defense_level": defense_level,
        "cos_w": cos_w,
        "cosine": cosine,
        "lb_cos": lb_cos,
        "jsd_stress": jsd_stress,
        "adf_fail_count": adf_fail_count,
        "sentiment": sentiment,
    }


def _apply_template(template: str, vars_map: Dict[str, Any]) -> str:
    """``{key}`` → ``vars_map[key]``。"""
    out = template
    for k, v in vars_map.items():
        key = "{" + k + "}"
        if key in out:
            out = out.replace(key, str(v))
    return out


def build_figure_caption_bundle(
    ui_mode: Optional[str],
    snap_json: Dict[str, Any],
    pol: Any,
    p2: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    jsd_thr_precomputed: Optional[float] = None,
) -> Dict[str, Any]:
    """按当前 ui_mode 装 FigX 讲解模板 → 注入变量 → 返回 ``{key: {title, body}}`` 字典。

    **外部接口完全不变**：与 ``figure_caption_service.build_figure_caption_bundle`` 行为一致。
    """
    mode = (ui_mode or "invest").lower()
    if mode not in ("invest", "research"):
        mode = "invest"
    tpl_root = load_caption_templates()
    branch = tpl_root.get(mode) or tpl_root.get("invest") or {}
    vm = _fmt_vars(
        mode,
        snap_json,
        pol,
        p2,
        meta,
        jsd_thr_precomputed=jsd_thr_precomputed,
    )
    out: Dict[str, Any] = {}
    for key, spec in branch.items():
        if not isinstance(spec, dict):
            continue
        title = str(spec.get("title") or key)
        body_t = str(spec.get("body_template") or "")
        out[key] = {"title": title, "body": _apply_template(body_t, vm)}
    return out
