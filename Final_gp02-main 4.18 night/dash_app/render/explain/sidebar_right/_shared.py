"""侧栏 FigX 共享的小 helper（仅本目录用到；不往外暴露）。"""

from __future__ import annotations

from typing import Any, Dict, Optional


def iso_test_date(p2: Dict[str, Any], row: Optional[Any]) -> Optional[str]:
    """把测试窗内某行号映射成 ISO 日期（YYYY-MM-DD）。"""
    if row is None or isinstance(row, bool):
        return None
    dates = p2.get("test_forecast_dates") or []
    try:
        ii = int(row)
    except (TypeError, ValueError):
        return None
    if 0 <= ii < len(dates):
        s = str(dates[ii])
        return s[:10] if len(s) >= 10 else s
    return None


def iso_to_yymmdd(iso: Optional[str]) -> str:
    """把 ``YYYY-MM-DD`` 渲染成 ``YY.MM.DD`` 给 Defense-Tag 文案使用。"""
    if not iso:
        return "—"
    s = str(iso)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return f"{s[2:4]}.{s[5:7]}.{s[8:10]}"
    return s


def defense_validation(snap: Dict[str, Any]) -> Dict[str, Any]:
    """从快照里安全地取 ``phase3.defense_validation`` 子字典。"""
    p3 = snap.get("phase3") or {}
    dv = p3.get("defense_validation") or {}
    return dv if isinstance(dv, dict) else {}
