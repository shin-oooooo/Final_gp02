"""Automatic incremental data refresh for data.json.

Called once at app startup (background thread, non-blocking).
Triggers when data.json is older than `max_age_hours`, or on a weekday when the
latest bar date in the file is before the calendar today (catch “file recently
touched but still yesterday’s last close”).

Design constraints:
- Never blocks the Dash server: runs in a daemon thread.
- Incremental only: loads existing payload, appends new rows, writes back.
- Safe for concurrent use: writes to a temp file then atomic rename.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import date
from typing import Any, Dict, Optional

_log = logging.getLogger(__name__)
_refresh_lock = threading.Lock()
_refresh_thread: Optional[threading.Thread] = None
_last_refresh_ts: float = 0.0   # unix timestamp of last successful refresh


def _data_age_hours(json_path: str) -> float:
    """Return age of data.json in hours; inf if file absent."""
    if not os.path.exists(json_path):
        return float("inf")
    return (time.time() - os.path.getmtime(json_path)) / 3600.0


def _payload_max_bar_date(json_path: str) -> Optional[date]:
    """Latest `date` across all asset/stock series in data.json; None if unreadable/empty."""
    if not os.path.exists(json_path):
        return None
    try:
        from ass1_core import load_json_first_document

        data: Dict[str, Any] = load_json_first_document(json_path)
    except Exception:
        return None
    max_d: Optional[date] = None
    for bucket in ("assets", "stocks"):
        section = data.get(bucket)
        if not isinstance(section, dict):
            continue
        for rows in section.values():
            if not isinstance(rows, list) or not rows:
                continue
            last = rows[-1]
            if not isinstance(last, dict):
                continue
            ds = last.get("date")
            if not ds:
                continue
            try:
                d = date.fromisoformat(str(ds)[:10])
            except ValueError:
                continue
            if max_d is None or d > max_d:
                max_d = d
    return max_d


def _weekday_calendar_stale(last_bar: Optional[date]) -> bool:
    """True if last close is before calendar today (Mon–Fri only; weekends rely on file age)."""
    if last_bar is None:
        return False
    today = date.today()
    if today.weekday() >= 5:
        return False
    return last_bar < today


def _do_refresh(json_path: str) -> None:
    """Blocking incremental download; run inside a thread."""
    global _last_refresh_ts
    try:
        import sys
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if _root not in sys.path:
            sys.path.insert(0, _root)

        from fetch_data import (
            FetchConfig,
            _load_payload,
            _universe_symbols,
            _default_symbols,
            _write_outputs,
            download_one,
        )

        out_dir = os.path.dirname(os.path.abspath(json_path))
        cfg = FetchConfig()
        payload = _load_payload(json_path, cfg)
        assets, stocks = _default_symbols()
        asset_set = set(assets)
        universe = _universe_symbols()

        n_ok = 0
        for sym in universe:
            kind = "asset" if sym in asset_set else "stock"
            try:
                payload = download_one(cfg, sym, kind, payload)
                n_ok += 1
            except Exception as e:
                _log.warning("[data_refresher] %s download failed: %s", sym, e)

        _write_outputs(out_dir, payload)
        _last_refresh_ts = time.time()
        _log.info("[data_refresher] refresh done (%d/%d symbols OK)", n_ok, len(universe))

    except Exception as exc:
        _log.error("[data_refresher] refresh failed: %s", exc, exc_info=True)


def maybe_refresh(json_path: str, max_age_hours: float = 18.0, enabled: bool = True) -> None:
    """Trigger a background refresh if the data file is stale.

    Parameters
    ----------
    json_path       : absolute path to data.json
    max_age_hours   : trigger threshold in hours (default 18 ≈ after market close)
    enabled         : if False, do nothing (respects `data_auto_refresh` policy flag)
    """
    if not enabled:
        return

    age = _data_age_hours(json_path)
    last_bar = _payload_max_bar_date(json_path)
    stale_by_age = age >= max_age_hours
    stale_by_calendar = _weekday_calendar_stale(last_bar)
    if not stale_by_age and not stale_by_calendar:
        _log.debug(
            "[data_refresher] skip: age=%.1fh < %.1fh, last_bar=%s",
            age, max_age_hours, last_bar.isoformat() if last_bar else "—",
        )
        return
    if stale_by_calendar and not stale_by_age:
        _log.info(
            "[data_refresher] weekday calendar stale (last_bar=%s < today=%s) → refresh",
            last_bar.isoformat() if last_bar else "—",
            date.today().isoformat(),
        )

    global _refresh_thread
    with _refresh_lock:
        if _refresh_thread is not None and _refresh_thread.is_alive():
            _log.debug("[data_refresher] refresh already running, skipping duplicate")
            return
        _log.info(
            "[data_refresher] data age=%.1fh ≥ threshold=%.1fh → starting background refresh",
            age, max_age_hours,
        )
        t = threading.Thread(
            target=_do_refresh,
            args=(json_path,),
            daemon=True,
            name="data-refresher",
        )
        t.start()
        _refresh_thread = t


def refresh_status() -> dict:
    """Return a dict summarising the current refresh state (for UI display)."""
    global _refresh_thread, _last_refresh_ts
    running = _refresh_thread is not None and _refresh_thread.is_alive()
    last_ok = (
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_last_refresh_ts))
        if _last_refresh_ts > 0
        else "未运行"
    )
    return {
        "running": running,
        "last_success": last_ok,
        "last_refresh_ts": _last_refresh_ts,
    }
