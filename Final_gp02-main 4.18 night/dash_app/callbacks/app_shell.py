from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

import dash_bootstrap_components as dbc
from dash import ALL, MATCH, Input, Output, State, ctx, dcc, html
from dash.exceptions import PreventUpdate

from dash_app.features.research_trace import (
    get_trace_modal_sections,
    load_code_excerpt,
)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def kronos_weights_ready() -> bool:
    """与 Phase2 / kronos_predictor 一致：模型与分词器目录内须含 .safetensors。"""
    try:
        from kronos_predictor import kronos_parameters_available

        return bool(kronos_parameters_available())
    except Exception:
        return False


def _kronos_topbar_hint_children() -> Any:
    if kronos_weights_ready():
        return html.Span(
            "Kronos 权重就绪：全链路（含影子验证 MSE 与样本外一步预测）使用模型推理。",
            className="text-muted small",
        )
    return html.Span(
        "未检测到 Kronos 权重（或缺少 .safetensors）：Phase2/影子验证对 Kronos 使用统计回退；"
        "建议先点击「拉取」或通过 Git LFS 落盘后再「保存并运行」。",
        className="text-warning small",
    )


def _btn_run_title_kronos() -> str:
    if kronos_weights_ready():
        return ""
    return (
        "未检测到完整 Kronos 权重：保存并运行后 Phase2 对 Kronos 将使用收益统计回退（非 Transformer）。"
        " 建议先拉取权重。"
    )


def _main_tab_panel_styles(active: Optional[str]) -> List[Dict[str, str]]:
    t = (active or "p0").strip()
    keys = ("p0", "p1", "p2", "p3", "p4")
    return [{"display": "block" if t == k else "none"} for k in keys]


def _main_tab_seg_btn_class(active: Optional[str]) -> List[str]:
    t = (active or "p0").strip()
    keys = ("p0", "p1", "p2", "p3", "p4")
    return ["main-tab-seg-btn" + (" active" if t == k else "") for k in keys]


def _ui_mode_seg_btn_class(mode: Optional[str]) -> Tuple[str, str]:
    m = (mode or "invest").strip()
    inv = "ui-mode-seg-btn" + (" active" if m == "invest" else "")
    res = "ui-mode-seg-btn" + (" active" if m == "research" else "")
    return inv, res


def _lang_seg_btn_class(lang: Optional[str]) -> Tuple[str, str]:
    lg = (lang or "chn").strip().lower()
    if lg not in ("chn", "eng"):
        lg = "chn"
    chn = "ui-mode-seg-btn" + (" active" if lg == "chn" else "")
    eng = "ui-mode-seg-btn" + (" active" if lg == "eng" else "")
    return chn, eng


def _research_effective(mode: Optional[str], snap: Any) -> bool:
    """研究模式差异化 UI：仅在已有跑批快照后启用（运行前与投资视图一致）。"""
    if (mode or "invest") != "research":
        return False
    return isinstance(snap, dict) and bool(snap.get("phase0"))


def _p0_resolved_window_strings(snap: Any) -> Tuple[str, str, str, str]:
    """从快照中提取 Phase0 时间窗描述字符串，缺失时回退到默认值。"""
    if isinstance(snap, dict):
        p0 = snap.get("phase0") or {}
        meta = p0.get("meta") or {}
        tw = meta.get("time_windows") or {}
        if tw:
            return (
                str(tw.get("train_start") or "2020-01-01"),
                str(tw.get("train_end") or "2023-06-30"),
                str(tw.get("test_start") or "2023-07-01"),
                str(tw.get("test_end") or "2024-06-30"),
            )
    return ("2020-01-01", "2023-06-30", "2023-07-01", "2024-06-30")


def _trace_inline_accordion(repo_root: str, snap_d: Dict[str, Any], trace_key: str, uid: str) -> html.Div:
    """Full trace sections inline (replaces modal)."""
    sec = get_trace_modal_sections(snap_d, trace_key)
    if sec is None:
        return html.Div()
    code_blocks = [dcc.Markdown(load_code_excerpt(repo_root, r), className="small") for r in sec.code]
    idsuf = "".join(ch if ch.isalnum() else "_" for ch in uid)[:48]
    acc = dbc.Accordion(
        [
            dbc.AccordionItem(
                dcc.Markdown(sec.principle_md, className="small"),
                title="原理",
                item_id=f"trac_prin_{idsuf}",
            ),
            dbc.AccordionItem(
                html.Div(code_blocks, className="small"),
                title="代码",
                item_id=f"trac_code_{idsuf}",
            ),
            dbc.AccordionItem(
                dcc.Markdown(sec.assumption_md, className="small"),
                title="假设",
                item_id=f"trac_assum_{idsuf}",
            ),
        ],
        flush=True,
        always_open=True,
        active_item=[f"trac_prin_{idsuf}", f"trac_code_{idsuf}", f"trac_assum_{idsuf}"],
        className="mb-2",
    )
    return html.Div([acc], className="trace-inline-accordion")


def register_app_shell_callbacks(app):
    @app.callback(
        Output("app-mode-shell", "className"),
        Input("radio-ui-mode", "data"),
        Input("last-snap", "data"),
        prevent_initial_call=False,
    )
    def _app_mode_shell_class(mode: Optional[str], snap: Any):
        base = "p-3 phase-doc-scope app-shell"
        return f"{base} app-mode-research" if _research_effective(mode, snap) else f"{base} app-mode-invest"

    @app.callback(
        Output("main-tab-store", "data"),
        Input("btn-main-tab-p0", "n_clicks"),
        Input("btn-main-tab-p1", "n_clicks"),
        Input("btn-main-tab-p2", "n_clicks"),
        Input("btn-main-tab-p3", "n_clicks"),
        Input("btn-main-tab-p4", "n_clicks"),
        prevent_initial_call=True,
    )
    def _main_tab_from_buttons(_n0, _n1, _n2, _n3, _n4):
        tid = ctx.triggered_id
        m = {
            "btn-main-tab-p0": "p0",
            "btn-main-tab-p1": "p1",
            "btn-main-tab-p2": "p2",
            "btn-main-tab-p3": "p3",
            "btn-main-tab-p4": "p4",
        }
        if tid not in m:
            raise PreventUpdate
        return m[tid]

    @app.callback(
        Output("main-panel-p0", "style"),
        Output("main-panel-p1", "style"),
        Output("main-panel-p2", "style"),
        Output("main-panel-p3", "style"),
        Output("main-panel-p4", "style"),
        Output("btn-main-tab-p0", "className"),
        Output("btn-main-tab-p1", "className"),
        Output("btn-main-tab-p2", "className"),
        Output("btn-main-tab-p3", "className"),
        Output("btn-main-tab-p4", "className"),
        Input("main-tab-store", "data"),
        prevent_initial_call=False,
    )
    def _main_tab_visual(tab: Optional[str]):
        st = _main_tab_panel_styles(tab)
        cl = _main_tab_seg_btn_class(tab)
        return st[0], st[1], st[2], st[3], st[4], cl[0], cl[1], cl[2], cl[3], cl[4]

    @app.callback(
        Output("radio-ui-mode", "data"),
        Input("btn-ui-mode-invest", "n_clicks"),
        Input("btn-ui-mode-research", "n_clicks"),
        prevent_initial_call=True,
    )
    def _ui_mode_from_buttons(_ni, _nr):
        tid = ctx.triggered_id
        if tid == "btn-ui-mode-invest":
            return "invest"
        if tid == "btn-ui-mode-research":
            return "research"
        raise PreventUpdate

    @app.callback(
        Output("btn-ui-mode-invest", "className"),
        Output("btn-ui-mode-research", "className"),
        Input("radio-ui-mode", "data"),
        prevent_initial_call=False,
    )
    def _ui_mode_visual(mode: Optional[str]):
        return _ui_mode_seg_btn_class(mode)

    # 语言切换：**纯 clientside 一跳**。原先「按钮 → 服务器 `_lang_from_buttons` →
    # Store → clientside → `lang-url-refresh.href`」多跳链路在首次点击存在明显延迟，
    # 且偶发需要二次点击才能跳转。现在按钮点击直接：
    #   1. 写 ``lang-store.data``（保持 active 态样式 via ``_lang_visual``）
    #   2. 写 ``lang-url-refresh.href``（``refresh=True`` → 浏览器整页刷新）
    # 刷新后 app.py 的 layout factory 读取 ``?lang=`` 并调用
    # services.copy.set_language() 重新装载文案，与之前行为一致。
    app.clientside_callback(
        """
        function(nc_chn, nc_eng) {
            var ctx = window.dash_clientside && window.dash_clientside.callback_context;
            if (!ctx || !ctx.triggered || !ctx.triggered.length) {
                return [window.dash_clientside.no_update, window.dash_clientside.no_update];
            }
            var trig = ctx.triggered[0];
            if (!trig || !trig.value) {
                return [window.dash_clientside.no_update, window.dash_clientside.no_update];
            }
            var tid = (trig.prop_id || '').split('.')[0];
            var target = (tid === 'btn-lang-eng') ? 'eng' : 'chn';
            var params = new URLSearchParams(window.location.search || '');
            var current = (params.get('lang') || '').toLowerCase();
            if (current === target) {
                return [target, window.dash_clientside.no_update];
            }
            params.set('lang', target);
            var href = window.location.pathname + '?' + params.toString() + (window.location.hash || '');
            return [target, href];
        }
        """,
        Output("lang-store", "data"),
        Output("lang-url-refresh", "href"),
        Input("btn-lang-chn", "n_clicks"),
        Input("btn-lang-eng", "n_clicks"),
        prevent_initial_call=True,
    )

    @app.callback(
        Output("btn-lang-chn", "className"),
        Output("btn-lang-eng", "className"),
        Input("lang-store", "data"),
        prevent_initial_call=False,
    )
    def _lang_visual(lang: Optional[str]):
        return _lang_seg_btn_class(lang)

    @app.callback(
        Output("btn-kronos-pull", "children"),
        Output("btn-kronos-pull", "disabled"),
        Output("kr-topbar-hint", "children"),
        Output("btn-run", "title"),
        Input("btn-kronos-pull", "n_clicks"),
        prevent_initial_call=False,
    )
    def _kronos_pull_row(n: Optional[int]):
        if n:
            try:
                script = os.path.join(_ROOT, "download_kronos_weights.py")
                subprocess.run(
                    [sys.executable, script],
                    cwd=_ROOT,
                    check=False,
                    timeout=3600,
                )
            except (OSError, subprocess.SubprocessError, ValueError):
                pass
        hint = _kronos_topbar_hint_children()
        run_title = _btn_run_title_kronos() or None
        if kronos_weights_ready():
            return "已检测到Kronos参数，无需拉取", True, hint, run_title
        return "未检测到Kronos参数，点击拉取", False, hint, run_title

    @app.callback(
        Output("download-data-json", "data"),
        Input("btn-download-data-json", "n_clicks"),
        prevent_initial_call=True,
    )
    def _download_data_json(_n):
        jp = os.path.join(_ROOT, "data.json")
        if os.path.isfile(jp):
            with open(jp, "rb") as f:
                content = f.read()
            return dcc.send_bytes(content, filename="data.json")
        return dcc.send_string(
            "data.json 不存在。请使用左侧「立即刷新数据」生成后再下载。",
            filename="data.json_missing.txt",
        )

    @app.callback(
        Output({"type": "overview-card-collapse", "index": ALL}, "is_open"),
        Output({"type": "overview-card-wrap", "index": ALL}, "style"),
        Input("main-tab-store", "data"),
        Input({"type": "overview-card-header", "index": ALL}, "n_clicks"),
        State({"type": "overview-card-collapse", "index": ALL}, "is_open"),
        State({"type": "overview-card-collapse", "index": ALL}, "id"),
        State({"type": "overview-card-wrap", "index": ALL}, "id"),
        State({"type": "overview-card-wrap", "index": ALL}, "style"),
    )
    def _overview_card_open_and_order(
        tab, _header_clicks, current_is_open, collapse_ids, wrap_ids, current_styles
    ):
        if not ctx.triggered:
            default = current_is_open or [False] * len(collapse_ids)
            styles = current_styles or [{} for _ in (wrap_ids or [])]
            return default, styles

        tid = ctx.triggered_id

        # Build safe index→is_open map
        open_map = {}
        for i, c_id in enumerate(collapse_ids or []):
            idx = str(c_id.get("index", i))
            val = current_is_open[i] if current_is_open and i < len(current_is_open) else False
            open_map[idx] = val

        # Build index→current_style map for safe merge (normalize None to {})
        style_map = {}
        for i, w_id in enumerate(wrap_ids or []):
            idx = str(w_id.get("index", i))
            raw_style = current_styles[i] if current_styles and i < len(current_styles) else {}
            style_map[idx] = raw_style if isinstance(raw_style, dict) else {}

        if tid == "main-tab-store":
            # Tab switch: expand matching card (order: 99 = last), collapse others (order: 0 = top).
            # 「project」综述卡不参与 tab 联动：保留其当前 open 状态 + 固定 order 0（钉在顶部）。
            is_open_out = []
            style_out = []
            for c_id in collapse_ids or []:
                idx = str(c_id.get("index"))
                if idx == "project":
                    is_open_out.append(open_map.get(idx, True))
                    style_out.append({**(style_map.get(idx) or {}), "order": 0})
                    continue
                should_open = idx == tab
                is_open_out.append(should_open)
                base_style = style_map.get(idx) or {}
                style_out.append({**base_style, "order": 99 if should_open else 0})
            return is_open_out, style_out

        # Header click: toggle only that card, keep styles/order untouched
        clicked_tab = tid.get("index") if isinstance(tid, dict) else None
        if clicked_tab is not None:
            open_map[str(clicked_tab)] = not open_map.get(str(clicked_tab), False)

        is_open_out = [open_map.get(str(c_id.get("index")), False) for c_id in (collapse_ids or [])]
        style_out = [(style_map.get(str(w_id.get("index"))) or {}) for w_id in (wrap_ids or [])]
        return is_open_out, style_out

    @app.callback(
        Output("topbar-defense-reasons-collapse", "is_open"),
        Input("btn-toggle-defense-reasons", "n_clicks"),
        State("topbar-defense-reasons-collapse", "is_open"),
        prevent_initial_call=True,
    )
    def _toggle_topbar_reasons(n_clicks, is_open):
        return not is_open if n_clicks else is_open

    @app.callback(
        Output("topbar-hint-collapse", "is_open"),
        Input("btn-toggle-topbar-hint", "n_clicks"),
        State("topbar-hint-collapse", "is_open"),
        prevent_initial_call=True,
    )
    def _toggle_topbar_hint(n_clicks, is_open):
        return not is_open if n_clicks else is_open

    @app.callback(
        Output("defense-strategy-intro-collapse", "is_open"),
        Input("btn-toggle-defense-strategy-intro", "n_clicks"),
        State("defense-strategy-intro-collapse", "is_open"),
        prevent_initial_call=True,
    )
    def _toggle_defense_intro(n_clicks, is_open):
        return not is_open if n_clicks else is_open

    @app.callback(
        Output("defense-strategy-intro-chevron", "className"),
        Input("defense-strategy-intro-collapse", "is_open"),
    )
    def _rotate_defense_intro_chevron(is_open):
        return "fa fa-chevron-up ms-2" if is_open else "fa fa-chevron-down ms-2"
