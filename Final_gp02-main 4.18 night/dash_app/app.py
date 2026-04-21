"""Dash research UI: bootstrap `Dash` and wire callbacks.

Heavy UI helpers live in `dash_app.dash_ui_helpers`, full-page render in
`dash_app.dashboard_face_render`, pipeline callbacks in
`dash_app.callbacks.dashboard_pipeline`.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DASH_ASSETS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Dash 默认：并行 RSS、短超时。Crawl4AI 默认开启以抓取历史日期新闻（给 S_t 提供多节点分布）。
os.environ.setdefault("LREPORT_FAST_NEWS", "1")
os.environ.setdefault("CRAWL4AI_ENABLED", "1")
os.environ.setdefault("CRAWL4AI_PAGE_TIMEOUT_MS", "30000")
os.environ.setdefault("CRAWL4AI_MAX_URLS", "5")
os.environ.setdefault("CRAWL4AI_PER_PAGE_HEADLINES", "30")
os.environ.setdefault("NEWS_RSS_HTTP_TIMEOUT", "10")
os.environ.setdefault("NEWS_RSS_PARALLEL", "1")

import dash
import dash_bootstrap_components as dbc
from dash import dcc
from flask import request as _flask_request

from dash_app.services.copy import get_md_text, set_language
from dash_app.ui.layout import build_full_layout


# 全局 MathJax：默认在所有 dcc.Markdown 启用 MathJax 渲染。
# 设计取舍：原本各调用点需逐个传 ``mathjax=True``；改成模块级一次性 patch
# 保证未来新增的 Markdown 文案自动获得公式渲染能力，避免漏配。
_orig_markdown_init = dcc.Markdown.__init__


def _markdown_init_default_mathjax(self, *args, **kwargs):
    if "mathjax" not in kwargs:
        kwargs["mathjax"] = True
    return _orig_markdown_init(self, *args, **kwargs)


if not getattr(dcc.Markdown, "_global_mathjax_applied", False):
    dcc.Markdown.__init__ = _markdown_init_default_mathjax  # type: ignore[assignment]
    dcc.Markdown._global_mathjax_applied = True  # type: ignore[attr-defined]


def _resolve_lang_from_request() -> str:
    """从当前 HTTP 请求 URL 的 ``?lang=`` 读取语言代号。

    缺失、非法或非请求上下文下默认回退到 ``chn``。
    """
    try:
        raw = (_flask_request.args.get("lang") or "").strip().lower()
    except Exception:
        raw = ""
    return raw if raw in ("chn", "eng") else "chn"


def create_dash_app(route_prefix: str = "/", requests_prefix: str | None = None) -> dash.Dash:
    requests_prefix = requests_prefix or route_prefix
    app = dash.Dash(
        __name__,
        assets_folder=_DASH_ASSETS,
        external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME],
        requests_pathname_prefix=requests_prefix,
        routes_pathname_prefix=route_prefix,
        suppress_callback_exceptions=True,
    )

    def _serve_layout():
        """Per-request layout factory：读 ``?lang=`` → 切换 services/copy 语言 → 组装 layout。"""
        lang = _resolve_lang_from_request()
        set_language(lang)
        project_intro_md = get_md_text(
            "project_intro.md",
            "（可将项目统一介绍写入 `dash_app/content-CHN/project_intro.md`。）",
        )
        loading_dashboard_md = get_md_text(
            "loading_dashboard.md",
            "正在计算全链路结果，请稍候…" if lang == "chn" else "Running full pipeline, please wait…",
        )
        return build_full_layout(project_intro_md, loading_dashboard_md, lang=lang)

    app.layout = _serve_layout

    from dash_app.callbacks import (
        register_app_shell_callbacks,
        register_clientside_callbacks,
        register_dashboard_pipeline_callbacks,
        register_defense_rails_callbacks,
        register_p0_assets_callbacks,
        register_p2_symbol_callbacks,
        register_research_panels_callbacks,
        register_sidebar2_visibility_callbacks,
        register_sidebar_layout_callbacks,
    )

    register_sidebar_layout_callbacks(app)
    register_defense_rails_callbacks(app)
    register_sidebar2_visibility_callbacks(app)
    register_app_shell_callbacks(app)
    register_p0_assets_callbacks(app)
    register_p2_symbol_callbacks(app)
    register_research_panels_callbacks(app)
    register_clientside_callbacks(app)
    register_dashboard_pipeline_callbacks(app)

    return app
