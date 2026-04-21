"""P0 asset panel and pie chart callbacks."""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Set

from dash import ALL, Input, Output, State, ctx, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from dash_app.figures import fig_p0_portfolio_pie
from dash_app.services.copy import get_status_message

# Import shared helpers and constants from the main app module.
from dash_app.constants import _DEFAULT_UNIVERSE
from dash_app.ui.layout import _templates
from dash_app.dash_ui_helpers import (
    _build_p0_asset_tree,
    _flatten_universe,
    _merge_alias_weight_keys,
    _normalize_weight_dict,
    _remove_symbols_from_universe,
    _struck_resolved_symbols,
    _symbol_parent_category_keys,
    _symbols_in_category,
)


def register_p0_assets_callbacks(app):
    @app.callback(
        Output("fig-p0-pie", "figure"),
        Output("p0-pie-slider", "disabled"),
        Output("p0-pie-target-label", "children"),
        Input("p0-weight-store", "data"),
        Input("p0-pie-selected", "data"),
        Input("last-snap", "data"),
        Input("asset-universe-store", "data"),
        # theme-store 在 R1.10 后常驻 "dark"；从 Input 降级为 State 以免引入无意义
        # 触发点（dcc.Store 常量值永远不变，订阅它只会让 callback-graph 变脏）。
        State("theme-store", "data"),
        prevent_initial_call=False,
    )
    def _update_pie(weights, selected, snap, universe, theme):
        tpl = _templates(theme or "dark")
        u = universe or dict(_DEFAULT_UNIVERSE)
        order_full = _flatten_universe(u)
        w: Dict[str, float] = {}
        if isinstance(weights, dict) and len(weights) > 0:
            w = _merge_alias_weight_keys(dict(weights), order_full)
        if not w and snap:
            w = _merge_alias_weight_keys((snap.get("phase3") or {}).get("weights") or {}, order_full)
        if not w and not snap:
            if order_full:
                w = _normalize_weight_dict({s: 1.0 / len(order_full) for s in order_full}, order_full)
        meta = ((snap or {}).get("phase0") or {}).get("meta") or {}
        if snap:
            tech_m = meta.get("tech_symbols") or []
            hedge_m = meta.get("hedge_symbols") or []
            safe_m = meta.get("safe_symbols") or []
            bench = str(meta.get("benchmark") or "SPY")
        else:
            tech_m = [str(x).upper() for x in (u.get("tech") or []) if x]
            hedge_m = [str(x).upper() for x in (u.get("hedge") or []) if x]
            safe_m = [str(x).upper() for x in (u.get("safe") or []) if x]
            bench = str(u.get("benchmark") or "SPY")
        syms = order_full if order_full else list(w.keys())
        sel_for_pie = str(selected).strip().upper() if selected else None
        fig = fig_p0_portfolio_pie(
            w,
            syms,
            tpl,
            tech=tech_m,
            hedge=hedge_m,
            safe=safe_m,
            benchmark=bench,
            pie_selected=sel_for_pie,
            figure_title="Figure0.1",
        )
        if selected:
            sel = str(selected).upper()
            wc = float(w.get(sel, 0.0))
            label = f"已选：{sel}（当前权重 {wc:.1%}）"
            return fig, False, label
        return fig, True, "默认等权；点击饼图扇区或左侧准星选中资产，再拖动滑块调整权重"

    @app.callback(
        Output("p0-pie-selected", "data"),
        Input("fig-p0-pie", "clickData"),
        prevent_initial_call=True,
    )
    def _pie_click(click):
        if not click:
            raise PreventUpdate
        pts = (click or {}).get("points") or []
        if not pts:
            raise PreventUpdate
        return pts[0].get("label")

    @app.callback(
        Output("p0-pie-selected", "data", allow_duplicate=True),
        Input({"type": "p0-sym-select", "sym": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def _p0_sym_select_pie(_n_clicks):
        tid = ctx.triggered_id
        if not isinstance(tid, dict) or tid.get("type") != "p0-sym-select":
            raise PreventUpdate
        sym = str(tid.get("sym") or "").strip().upper()
        if not sym:
            raise PreventUpdate
        return sym

    @app.callback(
        Output("p0-pie-slider", "value", allow_duplicate=True),
        Input("p0-pie-selected", "data"),
        State("p0-weight-store", "data"),
        State("asset-universe-store", "data"),
        State("p0-pie-slider", "value"),
        prevent_initial_call=True,
    )
    def _p0_slider_sync_to_selection(selected, weights, universe, slider_val):
        if not selected or not isinstance(weights, dict) or len(weights) == 0:
            raise PreventUpdate
        order_full = _flatten_universe(universe or dict(_DEFAULT_UNIVERSE))
        w = _merge_alias_weight_keys(dict(weights), order_full)
        sel = str(selected).upper()
        new_v = float(w.get(sel, 0.0))
        try:
            cur = float(slider_val) if slider_val is not None else None
        except (TypeError, ValueError):
            cur = None
        if cur is not None and abs(cur - new_v) < 1e-8:
            raise PreventUpdate
        return new_v

    @app.callback(
        Output("p0-weight-store", "data"),
        Input("p0-pie-slider", "value"),
        State("p0-pie-selected", "data"),
        State("p0-weight-store", "data"),
        State("asset-universe-store", "data"),
        prevent_initial_call=True,
    )
    def _pie_slider(val, selected, weights, universe):
        if not selected or not isinstance(weights, dict) or len(weights) == 0:
            raise PreventUpdate
        order_full = _flatten_universe(universe or dict(_DEFAULT_UNIVERSE))
        w = _merge_alias_weight_keys(dict(weights), order_full)
        before = {k: float(w.get(k, 0.0)) for k in order_full}
        sel = str(selected).upper()
        if sel not in w:
            raise PreventUpdate
        total = sum(w.values())
        if total <= 0:
            raise PreventUpdate
        others = {k: v for k, v in w.items() if k != sel}
        others_sum = sum(others.values())
        new_sel = max(0.0, min(1.0, float(val or 0.0)))
        remaining = 1.0 - new_sel
        if others_sum > 0:
            factor = remaining / others_sum
            for k in others:
                w[k] = others[k] * factor
        w[sel] = new_sel
        after = {k: float(w.get(k, 0.0)) for k in order_full}
        if all(abs(after[k] - before[k]) < 1e-8 for k in order_full):
            raise PreventUpdate
        return w

    # ── P0 asset tree (left: display only; weights from p0-weight-store) ────
    @app.callback(
        Output("p0-assets", "children"),
        Output("p0-weight-order", "data"),
        Output("p0-weight-store", "data", allow_duplicate=True),
        Output("p0-pie-selected", "data", allow_duplicate=True),
        Input("last-snap", "data"),
        Input("asset-universe-store", "data"),
        Input("p0-strike-store", "data"),
        Input("p0-weight-store", "data"),
        State("p0-pie-selected", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def _p0_asset_panel(snap, universe, strike_store, cur_w, pie_sel):
        from dash import no_update

        univ = universe or dict(_DEFAULT_UNIVERSE)
        order_full = _flatten_universe(univ)
        struck_set = _struck_resolved_symbols(univ, strike_store)
        order_active = [s for s in order_full if s not in struck_set]
        tid = ctx.triggered_id
        trig_keys: Set[str] = set()
        if ctx.triggered_prop_ids:
            trig_keys = set(ctx.triggered_prop_ids.keys())
        elif ctx.triggered:
            trig_keys = {str(t.get("prop_id", "")) for t in ctx.triggered if isinstance(t, dict)}
        _struct_props = ("last-snap.data", "asset-universe-store.data", "p0-strike-store.data")
        struct_in = bool(trig_keys and (trig_keys & set(_struct_props)))
        weight_in = any(k == "p0-weight-store.data" or k.startswith("p0-weight-store.") for k in trig_keys)
        if not trig_keys:
            struct_in = tid in ("last-snap", "asset-universe-store", "p0-strike-store")
            weight_in = tid == "p0-weight-store"
        cur_empty = cur_w is None or (isinstance(cur_w, dict) and len(cur_w) == 0)
        reset_eq = (struct_in and not weight_in) or (cur_empty and not weight_in)
        ss = set((strike_store or {}).get("syms") or [])
        sc = set((strike_store or {}).get("cats") or [])

        ps = str(pie_sel).strip().upper() if pie_sel else ""
        pie_clear = no_update
        # 仅结构变化（快照/Universe/划线）时若已选标的已不参与组合则清空选中；
        # 纯权重刷新时不要清空，避免与「准星换标的→滑块→写权重→重建树」竞态导致第二个标的选不中。
        if struct_in and ps and ps not in order_active:
            pie_clear = None

        if not order_full:
            return html.Div(get_status_message("asset_config_empty", "资产配置为空"), className="small text-muted"), [], no_update, pie_clear
        if not snap:
            if not order_active:
                warn = html.Div(
                    "当前划线已排除全部参与标的，请取消部分划线后再应用。",
                    className="small text-warning",
                )
                return warn, [], no_update, pie_clear
            diag_m: Dict[str, Dict[str, Any]] = {}
            eq_w = _normalize_weight_dict(
                {s: 1.0 / len(order_active) for s in order_active}, order_active
            )
            cur_m = _merge_alias_weight_keys(cur_w if isinstance(cur_w, dict) else {}, order_full)
            if reset_eq:
                w_use = eq_w
            else:
                w_use = _normalize_weight_dict(
                    {s: float(cur_m.get(s, 0.0)) for s in order_active}, order_active
                )
            if reset_eq:
                w_display = {s: float(w_use.get(s, 0.0)) for s in order_full}
            else:
                w_display = {s: max(0.0, float(cur_m.get(s, 0.0))) for s in order_full}
            tree = _build_p0_asset_tree(univ, order_full, w_display, diag_m, ss, sc)
            banner = dbc.Alert(
                "尚未运行「应用」或侧栏「应用并重算」：可先调整 Universe、划线、饼图权重；统计指示灯将显示为「待诊断」。",
                color="info",
                className="py-2 mb-2 small",
            )
            w_out = no_update if (weight_in and not struct_in) else w_use
            return html.Div([banner, tree]), order_active, w_out, pie_clear
        if not order_active:
            warn = html.Div(
                "划线已排除全部参与组合的标的，请取消部分划线后点击「应用」。",
                className="small text-warning",
            )
            return warn, [], no_update, pie_clear
        p1 = snap.get("phase1") or {}
        diag_m = {d.get("symbol"): d for d in (p1.get("diagnostics") or []) if d.get("symbol")}
        eq_w = _normalize_weight_dict(
            {s: 1.0 / len(order_active) for s in order_active}, order_active
        )
        cur_m = _merge_alias_weight_keys(cur_w if isinstance(cur_w, dict) else {}, order_full)
        if reset_eq:
            w_use = eq_w
        else:
            w_use = _normalize_weight_dict(
                {s: float(cur_m.get(s, 0.0)) for s in order_active}, order_active
            )
        if reset_eq:
            w_display = {s: float(w_use.get(s, 0.0)) for s in order_full}
        else:
            w_display = {s: max(0.0, float(cur_m.get(s, 0.0))) for s in order_full}
        tree = _build_p0_asset_tree(univ, order_full, w_display, diag_m, ss, sc)
        w_out = no_update if (weight_in and not struct_in) else w_use
        return tree, order_active, w_out, pie_clear

    @app.callback(
        Output("p0-strike-store", "data"),
        Input({"type": "p0-sym-row", "sym": ALL}, "n_clicks"),
        Input({"type": "p0-cat-row", "cat": ALL}, "n_clicks"),
        State("p0-strike-store", "data"),
        State("asset-universe-store", "data"),
        prevent_initial_call=True,
    )
    def _toggle_strike(_sym_clicks, _cat_clicks, store, universe):
        tid = ctx.triggered_id
        if not isinstance(tid, dict):
            raise PreventUpdate
        tr = ctx.triggered or []
        if tr and tr[0].get("value") in (None, 0):
            raise PreventUpdate
        st = dict(store or {})
        syms = list(st.get("syms") or [])
        cats = list(st.get("cats") or [])
        univ = universe or dict(_DEFAULT_UNIVERSE)
        if tid.get("type") == "p0-sym-row":
            sym = str(tid.get("sym") or "").upper()
            if not sym:
                raise PreventUpdate
            parent_keys = _symbol_parent_category_keys(univ, sym)
            if sym in syms:
                syms = [s for s in syms if s != sym]
                for ck in parent_keys:
                    if ck in cats:
                        cats = [c for c in cats if c != ck]
            else:
                cleared_cat = False
                for ck in parent_keys:
                    if ck in cats:
                        cats = [c for c in cats if c != ck]
                        cleared_cat = True
                if not cleared_cat:
                    syms.append(sym)
        elif tid.get("type") == "p0-cat-row":
            cat = str(tid.get("cat") or "")
            if not cat:
                raise PreventUpdate
            if cat in cats:
                cats = [c for c in cats if c != cat]
                rm = {str(s).upper() for s in _symbols_in_category(univ, cat)}
                syms = [s for s in syms if str(s).upper() not in rm]
            else:
                cats.append(cat)
        else:
            raise PreventUpdate
        return {"syms": syms, "cats": cats}

    @app.callback(
        Output("asset-universe-store", "data"),
        Output("p0-strike-store", "data", allow_duplicate=True),
        Output("p0-weight-store", "data", allow_duplicate=True),
        Input("btn-p0-remove-assets", "n_clicks"),
        State("asset-universe-store", "data"),
        State("p0-strike-store", "data"),
        prevent_initial_call=True,
    )
    def _remove_marked_assets(n, universe, strike_store):
        if not n:
            raise PreventUpdate
        univ = copy.deepcopy(universe or dict(_DEFAULT_UNIVERSE))
        ss = set((strike_store or {}).get("syms") or [])
        sc = set((strike_store or {}).get("cats") or [])
        to_remove: Set[str] = set(ss)
        for ck in sc:
            to_remove.update(_symbols_in_category(univ, ck))
        if not to_remove:
            raise PreventUpdate
        _remove_symbols_from_universe(univ, to_remove)
        order = _flatten_universe(univ)
        eq_w = _normalize_weight_dict({s: 1.0 / len(order) for s in order}, order) if order else {}
        return univ, {"syms": [], "cats": []}, eq_w

    @app.callback(
        Output("modal-add-asset", "is_open"),
        Input("btn-p0-add-asset", "n_clicks"),
        Input("btn-add-asset-cancel", "n_clicks"),
        Input("btn-add-asset-save", "n_clicks"),
        prevent_initial_call=True,
    )
    def _modal_add_open(n_open, n_cancel, n_save):
        tid = ctx.triggered_id
        if tid == "btn-p0-add-asset" and n_open:
            return True
        if tid in ("btn-add-asset-cancel", "btn-add-asset-save"):
            return False
        raise PreventUpdate

    @app.callback(
        Output("asset-universe-store", "data", allow_duplicate=True),
        Output("p0-weight-store", "data", allow_duplicate=True),
        Input("btn-add-asset-save", "n_clicks"),
        State("asset-universe-store", "data"),
        State("inp-add-sym", "value"),
        State("inp-add-w", "value"),
        State("dd-add-cat", "value"),
        State("inp-new-cat-name", "value"),
        State("p0-weight-store", "data"),
        State("p0-weight-order", "data"),
        prevent_initial_call=True,
    )
    def _save_new_asset(n, universe, sym_raw, w_raw, cat_dd, new_cat_name, cur_w, order):
        if not n:
            raise PreventUpdate
        sym = str(sym_raw or "").strip().upper()
        if not sym:
            raise PreventUpdate
        try:
            w_new = float(w_raw)
        except (TypeError, ValueError):
            w_new = 0.05
        w_new = max(0.0, min(1.0, w_new))
        if w_new >= 1.0:
            raise PreventUpdate
        univ = copy.deepcopy(universe or dict(_DEFAULT_UNIVERSE))
        ord_prev = list(order or _flatten_universe(univ))
        if sym in ord_prev:
            raise PreventUpdate
        cat = cat_dd or "tech"
        if cat == "__new__":
            nm = (new_cat_name or "").strip() or "自定义"
            ex = univ.setdefault("extra", {})
            if not isinstance(ex, dict):
                ex = {}
                univ["extra"] = ex
            ex.setdefault(nm, []).append(sym)
        elif cat in ("tech", "hedge", "safe"):
            lst = list(univ.get(cat) or [])
            if sym not in [str(x).upper() for x in lst]:
                lst.append(sym)
            univ[cat] = lst
        ord_new = ord_prev + [sym]
        base = {s: float((cur_w or {}).get(s, 1.0 / max(len(ord_prev), 1))) for s in ord_prev}
        tot = sum(base.values())
        if tot <= 1e-12:
            base = {s: 1.0 / len(ord_prev) for s in ord_prev}
            tot = 1.0
        scale = (1.0 - w_new) / tot
        new_w = {s: base[s] * scale for s in ord_prev}
        new_w[sym] = w_new
        new_w = _normalize_weight_dict(new_w, ord_new)
        return univ, new_w
