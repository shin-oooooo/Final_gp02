"""Shared constants for the Dash application.

所有面向用户的中文字符串都改为 **运行期** 从 ``content-{LANG}/all_labels.md`` 取出，
以便中英文切换立即生效。保留原中文字面量作为 ``get_app_label`` 的回退默认值。
"""

from __future__ import annotations

from dash_app.services.copy import get_app_label

_DEFAULT_UNIVERSE = {
    "tech": ["NVDA", "MSFT", "TSMC", "GOOGL", "AAPL"],
    "hedge": ["XLE"],
    "safe": ["GLD", "TLT"],
    "benchmark": "SPY",
    "extra": {},  # { "自定义类名": ["SYM", ...] }
}


_CAT_DEFAULT_CHN = {"tech": "科技股", "hedge": "对冲类", "safe": "安全资产", "benchmark": "基准"}


class _LazyLabelDict:
    """类 dict 代理：``.get(key, default)`` 在调用时才解析 ``all_labels.md``。

    解决 Python 模块在进程生命周期内只加载一次、而 ``?lang=`` 切换需要即时刷新文案的矛盾。
    传入 ``prefix`` + ``fallback_map``：``self[key]`` / ``self.get(key, ...)`` 调用时
    统一走 ``get_app_label(f"{prefix}{key}", fallback_map[key])``。
    """

    __slots__ = ("_prefix", "_fallback")

    def __init__(self, prefix: str, fallback: dict) -> None:
        self._prefix = prefix
        self._fallback = dict(fallback)

    def _resolve(self, key: str) -> str:
        return get_app_label(f"{self._prefix}{key}", self._fallback.get(key, key))

    def __getitem__(self, key: str) -> str:
        return self._resolve(key)

    def get(self, key: str, default: str = "") -> str:  # noqa: D401 — mapping-style API
        if key in self._fallback:
            return self._resolve(key)
        return default if default else key

    def __contains__(self, key: str) -> bool:
        return key in self._fallback

    def keys(self):
        return self._fallback.keys()

    def values(self):
        return [self._resolve(k) for k in self._fallback]

    def items(self):
        return [(k, self._resolve(k)) for k in self._fallback]

    def __iter__(self):
        return iter(self._fallback)

    def __len__(self) -> int:
        return len(self._fallback)


_CAT_LABELS = _LazyLabelDict("cat_", _CAT_DEFAULT_CHN)
_CAT_COLORS = {"tech": "#4fc3f7", "hedge": "#ffa726", "safe": "#66bb6a", "benchmark": "#b0bec5"}
_CATS = ["tech", "hedge", "safe", "benchmark"]

_EXTRA_COLORS = ["#90a4ae", "#ba68c8", "#4dd0e1", "#ffcc80", "#a5d6a7"]

_P2_MODEL_LABEL = {"naive": "Naive", "arima": "ARIMA", "lightgbm": "LightGBM", "kronos": "Kronos"}
_P2_MODEL_COLOR = {"naive": "#aaaaaa", "arima": "#00e676", "lightgbm": "#c39bff", "kronos": "#ff7f0e"}

_DEFENSE_LABEL = _LazyLabelDict(
    "defense_label_level_",
    {0: "标准防御", 1: "警戒防御", 2: "熔毁防御"},
)

_LEVEL_COLOR = {
    0: "success",
    1: "warning",
    2: "danger",
}

_LEVEL_DARK_BG = {
    0: "#2e7d32",
    1: "#ef6c00",
    2: "#c62828",
}

_LEVEL_STATUS = _LazyLabelDict(
    "level_status_l",
    {0: "STATUS: Level 0 — 标准防御", 1: "STATUS: Level 1 — 警戒防御", 2: "STATUS: Level 2 — 熔毁防御"},
)
