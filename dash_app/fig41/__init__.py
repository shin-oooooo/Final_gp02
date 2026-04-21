"""Fig 4.1 · 预警有效性检验 — 高内聚渲染模块。

本模块把原本散落在 ``dashboard_face_render.py`` 中 130 余行、与 58 元组深度
耦合的 Fig4.1 渲染逻辑重构为：

* ``contracts``  — 纯数据契约（dataclass，不可变）
* ``extract``    — 从快照抽取的纯函数（带断言 + 日志）
* ``render``     — 组装 Dash 组件的纯函数（无副作用）

外部仅使用 :func:`build_fig41`；返回 :class:`Fig41Components`，调用方按名取
四个组件即可。任何 bug 都可以通过：

    python -c "from dash_app.fig41 import build_fig41; import json; ..."

构造最小可运行案例复现，不再需要启动整条管线。
"""

from __future__ import annotations

from dash_app.fig41.contracts import (
    Fig41Baselines,
    Fig41Bundle,
    Fig41Components,
    Fig41Context,
    Fig41DualVerdict,
    Fig41Hits,
    Fig41PostAlarm,
)
from dash_app.fig41.extract import extract_fig41_bundle
from dash_app.fig41.render import (
    build_fig41_components as build_fig41,
    build_fig41_conclusion_card,
)

__all__ = [
    "Fig41Baselines",
    "Fig41Bundle",
    "Fig41Components",
    "Fig41Context",
    "Fig41DualVerdict",
    "Fig41Hits",
    "Fig41PostAlarm",
    "build_fig41",
    "build_fig41_conclusion_card",
    "extract_fig41_bundle",
]
