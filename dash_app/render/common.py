"""跨 UI 区域共享的渲染助手。

放在此处的函数必须在**至少 2 个**不同区域被用到；否则应归入其所属区域的文件。
"""

from __future__ import annotations

import plotly.graph_objects as go


def minimal_placeholder_figure(template: str) -> go.Figure:
    """超小透明占位 Figure（用于尚未启用的槽位）。

    main_p2 的 ``fig-p2-forecast`` 与 main_p3 的 ``fig-p3-shadow`` 都用它。
    """
    assert isinstance(template, str) and template, "template must be non-empty str"
    return go.Figure(
        layout=dict(
            template=template,
            height=10,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
    )
