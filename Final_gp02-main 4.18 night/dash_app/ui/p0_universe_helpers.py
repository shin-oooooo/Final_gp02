"""P0 (resource universe) helper functions.

Extracted from ``dash_app/dash_ui_helpers.py`` during the 2026-04-21 slim-down
round to keep the main helpers file under 500 LOC.

All names below are re-exported from ``dash_app.dash_ui_helpers`` to preserve
the legacy import surface::

    from dash_app.dash_ui_helpers import (
        _build_p0_asset_tree,
        _flatten_universe,
        _merge_alias_weight_keys,
        _normalize_weight_dict,
        _remove_symbols_from_universe,
        _struck_resolved_symbols,
        _symbol_parent_category_keys,
        _symbols_in_category,
        _phase0_from_universe_after_strikes,
        _phase0_from_universe_store,
    )
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Set, Tuple

import dash_bootstrap_components as dbc
from dash import html

from dash_app.constants import (
    _CAT_COLORS,
    _CAT_LABELS,
    _CATS,
    _DEFAULT_UNIVERSE,
    _EXTRA_COLORS,
)
from dash_app.services.copy import get_status_message
from research.schemas import Phase0Input


def _struck_resolved_symbols(univ: Dict[str, Any], strike_store: Dict[str, Any] | None) -> Set[str]:
    """Symbols excluded by strike (per-symbol or whole category keys)."""
    out: Set[str] = set()
    for x in (strike_store or {}).get("syms") or []:
        s = str(x).strip().upper()
        if s:
            out.add(s)
    for ck in (strike_store or {}).get("cats") or []:
        ck = str(ck).strip()
        if ck:
            out.update(str(s).upper() for s in _symbols_in_category(univ, ck))
    return out


def _phase0_from_universe_after_strikes(
    u: Dict[str, Any] | None, strike_store: Dict[str, Any] | None
) -> Phase0Input:
    """Phase0Input after removing struck symbols (划线暂不参与组合与诊断)。"""
    u2 = copy.deepcopy(u or _DEFAULT_UNIVERSE)
    to_remove = _struck_resolved_symbols(u2, strike_store)
    if to_remove:
        _remove_symbols_from_universe(u2, to_remove)
    return _phase0_from_universe_store(u2)


def _coerce_sym_list(v: Any) -> List[str]:
    """Normalize universe symbol lists from Store (list/str/empty dict must not wipe tech)."""
    if v is None:
        return []
    if isinstance(v, str):
        return [v.strip().upper()] if v.strip() else []
    if isinstance(v, list):
        return [str(x).strip().upper() for x in v if str(x).strip()]
    return []


def _phase0_from_universe_store(u: Dict[str, Any] | None) -> Phase0Input:
    """Map UI universe (including extra groups) to Phase0Input."""
    u = dict(u or _DEFAULT_UNIVERSE)
    tech = _coerce_sym_list(u.get("tech"))
    hedge = _coerce_sym_list(u.get("hedge"))
    safe = _coerce_sym_list(u.get("safe"))
    extra = u.get("extra") or {}
    if isinstance(extra, dict):
        for _gn, syms in extra.items():
            if isinstance(syms, list):
                for s in syms:
                    s = str(s).strip().upper()
                    if s and s not in tech:
                        tech.append(s)
    tech = list(dict.fromkeys(tech))
    if not tech:
        tech = list(dict.fromkeys(_coerce_sym_list(_DEFAULT_UNIVERSE.get("tech"))))
    return Phase0Input(
        tech_symbols=tech,
        hedge_symbols=hedge,
        safe_symbols=safe,
        benchmark=str(u.get("benchmark") or "SPY").strip().upper() or "SPY",
    )


def _universe_extra_color(i: int) -> str:
    return _EXTRA_COLORS[i % len(_EXTRA_COLORS)]


def _symbols_in_category(univ: Dict[str, Any], cat_key: str) -> List[str]:
    if cat_key in ("tech", "hedge", "safe"):
        v = univ.get(cat_key)
        if isinstance(v, list):
            return [str(x).upper() for x in v]
        if isinstance(v, str) and v:
            return [v.upper()]
        return []
    if cat_key == "benchmark":
        b = str(univ.get("benchmark") or "").strip().upper()
        return [b] if b else []
    if cat_key.startswith("extra:"):
        name = cat_key[6:]
        return [str(x).upper() for x in ((univ.get("extra") or {}).get(name) or [])]
    return []


def _symbol_parent_category_keys(univ: Dict[str, Any], sym: str) -> List[str]:
    """Universe 中包含 sym 的资产类键（tech/hedge/safe/benchmark/extra:…）。"""
    u = univ or dict(_DEFAULT_UNIVERSE)
    sym_u = str(sym).strip().upper()
    if not sym_u:
        return []
    out: List[str] = []
    for cat in ("tech", "hedge", "safe"):
        raw = u.get(cat)
        lst = raw if isinstance(raw, list) else ([raw] if isinstance(raw, str) and raw else [])
        if any(str(x).strip().upper() == sym_u for x in lst):
            out.append(cat)
    bench = str(u.get("benchmark") or "").strip().upper()
    if bench and sym_u == bench:
        out.append("benchmark")
    extra = u.get("extra") or {}
    if isinstance(extra, dict):
        for gname, syms_raw in extra.items():
            if not isinstance(syms_raw, list):
                continue
            if any(str(x).strip().upper() == sym_u for x in syms_raw):
                out.append(f"extra:{gname}")
    return out


def _cat_header_dimmed(cat: str, syms_in_cat: List[str], strike_syms: Set[str], strike_cats: Set[str]) -> bool:
    """类标题变暗 iff 该类下每一行都处于划线态（整类划线或单标的全员划线）。"""
    su = [str(s).upper() for s in syms_in_cat]
    if not su:
        return False
    cat_broad = cat in strike_cats
    return all((s in strike_syms or cat_broad) for s in su)


def _remove_symbols_from_universe(univ: Dict[str, Any], to_remove: Set[str]) -> None:
    for k in ("tech", "hedge", "safe"):
        if isinstance(univ.get(k), list):
            univ[k] = [x for x in univ[k] if str(x).upper() not in to_remove]
    ex = univ.get("extra") or {}
    if isinstance(ex, dict):
        for name, syms in list(ex.items()):
            if not isinstance(syms, list):
                continue
            ex[name] = [x for x in syms if str(x).upper() not in to_remove]
            if not ex[name]:
                del ex[name]
        univ["extra"] = ex
    if str(univ.get("benchmark") or "").upper() in to_remove:
        univ["benchmark"] = "SPY"


def _normalize_weight_dict(w: Dict[str, float], syms: List[str]) -> Dict[str, float]:
    if not syms:
        return {}
    out = {s: max(float(w.get(s, 0.0)), 0.0) for s in syms}
    t = sum(out.values())
    if t <= 1e-15:
        u = 1.0 / len(syms)
        return {s: u for s in syms}
    return {s: out[s] / t for s in syms}


def _merge_alias_weight_keys(w: Dict[str, float], order_full: List[str]) -> Dict[str, float]:
    """Align pipeline/data column names (TSM, AU0) with UI universe (TSMC, GLD)."""
    m = {str(k).upper(): float(v) for k, v in (w or {}).items()}
    of = set(order_full)
    if "TSM" in m and "TSMC" in of:
        m["TSMC"] = m.get("TSMC", 0.0) + m.pop("TSM", 0.0)
    if "AU0" in m and "GLD" in of:
        m["GLD"] = m.get("GLD", 0.0) + m.pop("AU0", 0.0)
    return {k: float(m.get(k, 0.0)) for k in order_full}


def _flatten_universe(universe: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for cat in _CATS:
        val = universe.get(cat)
        if isinstance(val, list):
            for s in val:
                if s and str(s).upper() not in out:
                    out.append(str(s).upper())
        elif isinstance(val, str) and val:
            if val.upper() not in out:
                out.append(val.upper())
    extra = universe.get("extra") or {}
    if isinstance(extra, dict):
        for _gn, syms in extra.items():
            if isinstance(syms, list):
                for s in syms:
                    if s and str(s).upper() not in out:
                        out.append(str(s).upper())
    return out


def _p0_diag_line(sym: str, diag_map: Dict[str, Dict[str, Any]]) -> Tuple[str, str]:
    """Return (one-line status, badge color) for 平稳 × 规律 四象限."""
    d = diag_map.get(sym)
    if not d:
        return "待诊断", "secondary"
    ok = bool(d.get("stationary_returns"))
    lpv = bool(d.get("low_predictive_value"))
    fail = bool(d.get("basic_logic_failure"))
    if fail:
        return "非平稳或逻辑失败 · 不可作为建模前提", "danger"
    if ok and not lpv:
        return "平稳 · 存在可建模结构（拒绝纯噪声）", "success"
    if ok and lpv:
        return "平稳 · 残差近白噪声（弱规律）", "warning"
    return "非平稳 · 需差分或进一步检验", "danger"


def _p0_slim_asset_row(
    sym: str,
    cat: str,
    weight: float,
    diag_map: Dict[str, Dict[str, Any]],
    *,
    struck: bool,
    color: str,
) -> html.Div:
    line, badge_c = _p0_diag_line(sym, diag_map)
    row_style: Dict[str, Any] = {"textDecoration": "line-through", "opacity": 0.55} if struck else {}
    return html.Div(
        [
            html.Div(className="p0-slim-bar", style={"background": color}),
            html.Div(
                [
                    html.Button(
                        html.I(className="fa fa-crosshairs"),
                        id={"type": "p0-sym-select", "sym": sym},
                        n_clicks=0,
                        type="button",
                        title="选为当前调整标的（与饼图联动）",
                        className="btn btn-sm btn-outline-secondary py-0 px-1 me-1 p0-sym-select-btn",
                    ),
                    html.Button(
                        id={"type": "p0-sym-row", "sym": sym},
                        n_clicks=0,
                        type="button",
                        className="p0-slim-row-hit btn btn-link text-start p-0 flex-grow-1 text-decoration-none",
                        style=row_style,
                        children=[
                            html.Span(sym, className="mono fw-bold me-2"),
                            dbc.Badge(line, color=badge_c, className="me-1 p0-diag-pill"),
                            html.Span(
                                f"权重 {weight:.1%}（右侧饼图调整）",
                                className="small text-muted",
                            ),
                        ],
                    ),
                ],
                className="p0-slim-body flex-grow-1",
            ),
        ],
        className="p0-slim-card d-flex mb-1",
    )


def _build_p0_asset_tree(
    universe: Dict[str, Any],
    order: List[str],
    weights: Dict[str, float],
    diag_map: Dict[str, Dict[str, Any]],
    strike_syms: set,
    strike_cats: set,
) -> html.Div:
    blocks: List[Any] = []
    for cat in _CATS:
        val = universe.get(cat)
        cat_syms = val if isinstance(val, list) else ([val] if isinstance(val, str) and val else [])
        syms = [s for s in cat_syms if s in order]
        if not syms:
            continue
        color = _CAT_COLORS.get(cat, "#78909c")
        cat_struck = cat in strike_cats
        cat_hdr_dim = _cat_header_dimmed(cat, syms, strike_syms, strike_cats)
        cat_hdr_style = {"textDecoration": "line-through", "opacity": 0.55} if cat_hdr_dim else {}
        blocks.append(
            html.Div(
                [
                    html.Button(
                        id={"type": "p0-cat-row", "cat": cat},
                        n_clicks=0,
                        type="button",
                        className="p0-tree-cat mb-1 p0-slim-row-hit btn btn-link text-start p-0 w-100 text-decoration-none",
                        style=cat_hdr_style,
                        children=[
                            html.I(className="fa fa-folder-tree me-2", style={"color": color}),
                            html.Span(_CAT_LABELS.get(cat, cat), className="fw-bold small"),
                            html.Span(f"（{len(syms)}）", className="small text-muted ms-1"),
                        ],
                    ),
                    html.Div(
                        [
                            _p0_slim_asset_row(
                                sym, cat, weights.get(sym, 0.0), diag_map,
                                struck=(sym in strike_syms or cat_struck),
                                color=color,
                            )
                            for sym in syms
                        ],
                        className="p0-tree-assets ms-2 ps-2 border-start",
                        style={"borderColor": color},
                    ),
                ],
                className="mb-2",
            )
        )
    extra = universe.get("extra") or {}
    if isinstance(extra, dict):
        for i, (gname, syms_raw) in enumerate(extra.items()):
            if not isinstance(syms_raw, list):
                continue
            syms = [str(s).upper() for s in syms_raw if s and str(s).upper() in order]
            if not syms:
                continue
            color = _universe_extra_color(i)
            gk = f"extra:{gname}"
            cat_struck = gk in strike_cats
            cat_hdr_dim = _cat_header_dimmed(gk, syms, strike_syms, strike_cats)
            cat_hdr_style = {"textDecoration": "line-through", "opacity": 0.55} if cat_hdr_dim else {}
            blocks.append(
                html.Div(
                    [
                        html.Button(
                            id={"type": "p0-cat-row", "cat": gk},
                            n_clicks=0,
                            type="button",
                            className="p0-tree-cat mb-1 p0-slim-row-hit btn btn-link text-start p-0 w-100 text-decoration-none",
                            style=cat_hdr_style,
                            children=[
                                html.I(className="fa fa-folder-tree me-2", style={"color": color}),
                                html.Span(gname, className="fw-bold small"),
                                html.Span(f"（{len(syms)}）", className="small text-muted ms-1"),
                            ],
                        ),
                        html.Div(
                            [
                                _p0_slim_asset_row(
                                    sym, gk, weights.get(sym, 0.0), diag_map,
                                    struck=(sym in strike_syms or cat_struck),
                                    color=color,
                                )
                                for sym in syms
                            ],
                            className="p0-tree-assets ms-2 ps-2 border-start",
                            style={"borderColor": color},
                        ),
                    ],
                    className="mb-2",
                )
            )
    if not blocks:
        return html.Div(get_status_message("no_asset_config", "暂无资产配置"), className="small text-muted")
    return html.Div(
        [
            html.P(
                "左侧：资产与统计指示灯（点击行可划线；「应用」按划线重算；红钮「删除资产」永久移除划线项）。"
                "组合权重默认为等权，请在右侧饼图调整。",
                className="small text-muted mb-2",
            ),
            html.Div(blocks),
        ],
        className="p0-asset-tree",
    )
