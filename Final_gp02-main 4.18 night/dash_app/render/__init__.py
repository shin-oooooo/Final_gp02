"""Dashboard 渲染层 — 按 UI 区域拆分（非按数据 phase）。

设计原则：**UI 位置 = 代码位置**。
找 bug 的入口 = 你在网页上看到的区域。

::

    render/
    ├── state.py             共享 DashboardState + extract（数据层 → UI 层的契约）
    ├── contracts.py         所有 *Components dataclass
    ├── common.py            跨区域可复用件（最小占位图等）
    │
    ├── topbar.py            顶栏动态内容：defense-intro, reasons-collapse
    ├── sidebar_right.py     侧栏 2：badge / 5 figures / 5 reasons / caption / FigX.1-6 讲解
    │
    ├── main_p0.py           主栏 P0：corr / beta / 4 文本卡 / noise / about
    ├── main_p1.py           主栏 P1：诊断卡片 / 分组分析
    ├── main_p2.py           主栏 P2：一致性 / 最佳模型 / density / 语义块
    ├── main_p3.py           主栏 P3：目标 / S_t / MC / 权重 / shadow
    └── main_p4.py           主栏 P4：experiments stack + fig41（薄壳）

公共入口：上层 orchestrator（``dashboard_face_render.render_dashboard_outputs``）
依次调用本模块各 ``build_*`` 函数，然后按 callback Output 顺序打包 59 元组。
"""

from __future__ import annotations

from dash_app.render.contracts import (
    DashboardState,
    MainP0Components,
    MainP1Components,
    MainP2Components,
    MainP3Components,
    MainP4Components,
    SidebarRightComponents,
    TopbarDynamicComponents,
)
from dash_app.render.main_p0 import build_main_p0_components as build_main_p0
from dash_app.render.main_p1 import build_main_p1_components as build_main_p1
from dash_app.render.main_p2 import build_main_p2_components as build_main_p2
from dash_app.render.main_p3 import build_main_p3_components as build_main_p3
from dash_app.render.main_p4 import build_main_p4_components as build_main_p4
from dash_app.render.sidebar_right import build_sidebar_right_components as build_sidebar_right
from dash_app.render.state import extract_dashboard_state
from dash_app.render.topbar import build_topbar_dynamic_components as build_topbar_dynamic

__all__ = [
    "DashboardState",
    "MainP0Components",
    "MainP1Components",
    "MainP2Components",
    "MainP3Components",
    "MainP4Components",
    "SidebarRightComponents",
    "TopbarDynamicComponents",
    "build_main_p0",
    "build_main_p1",
    "build_main_p2",
    "build_main_p3",
    "build_main_p4",
    "build_sidebar_right",
    "build_topbar_dynamic",
    "extract_dashboard_state",
]
