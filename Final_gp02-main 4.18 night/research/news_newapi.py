"""NewAPI (NewsAPI-like) client: fetch dated headlines for sentiment.

This module is intentionally lightweight and only depends on `requests`.

Environment variables
---------------------
NEWSAPI_KEY
    API key. If missing, the client returns empty results.
NEWSAPI_BASE_URL
    Base URL, default: https://newsapi.org
NEWSAPI_TIMEOUT_SEC
    Request timeout seconds, default: 18
NEWSAPI_USER_AGENT
    Optional UA string.
NEWSAPI_LOOKBACK_DAYS
    Default ``29`` → request ``from = today - 29`` (about 30 calendar days).
    NewsAPI.org free/developer tiers often reject ranges longer than ~1 month.
NEWSAPI_INTER_REQUEST_SEC
    Sleep between per-day requests (default ``0.12``); set ``0`` to disable.
NEWSAPI_MAX_RAW_ARTICLES
    Safety cap on raw rows collected across all days (default ``2500``).
NEWSAPI_HEADLINES_CAP
    Hard max on (title, date, …) tuples returned after sort/dedupe (default ``2000``).

Callers (e.g. ``sentiment_proxy``) may pass ``only_days`` to limit which calendar days are
requested — see ``NEWSAPI_FETCH_STRATEGY`` / ``NEWSAPI_GAP_*`` in that module.

``NEWSAPI_FETCH_STRATEGY=interval_vader`` (set in ``sentiment_proxy``): builds random
endpoints on day indices ``1..30`` (day ``d`` = calendar day ``test_start + (d-1)``,
clipped to ``as_of``), consecutive endpoint gaps in ``{2,3,4}``, one ``/everything`` call
per interval, then VADER compound stratification (5 bins) for roughly uniform semantic
mix per interval before global dedupe.

Notes
-----
We use the common "NewsAPI.org" style contract:
  - GET /v2/everything
  - Header: X-Api-Key: <key>
  - Params: q, from, to, language, sortBy, pageSize, page

If your "NewAPI" provider uses a different contract, keep the public function
`fetch_newapi_headlines` (4-tuple rows including ``publishedAt``) and adjust the request mapping here.
"""

from __future__ import annotations

import os
import random
import time
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


@dataclass(frozen=True)
class NewApiConfig:
    base_url: str = "https://newsapi.org"
    api_key: str = ""
    timeout_sec: float = 18.0
    user_agent: str = "AIE1902-NewAPI/1.0"


def _load_cfg() -> NewApiConfig:
    key = (os.environ.get("NEWSAPI_KEY") or "").strip()
    base = (os.environ.get("NEWSAPI_BASE_URL") or "https://newsapi.org").strip().rstrip("/")
    ua = (os.environ.get("NEWSAPI_USER_AGENT") or "AIE1902-NewAPI/1.0").strip()
    try:
        t = float((os.environ.get("NEWSAPI_TIMEOUT_SEC") or "").strip() or 18.0)
    except ValueError:
        t = 18.0
    t = float(max(3.0, min(60.0, t)))
    return NewApiConfig(base_url=base, api_key=key, timeout_sec=t, user_agent=ua)


def _parse_published_at(v: Any) -> Optional[date]:
    if not v:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    if not s:
        return None
    # NewsAPI style: 2026-04-16T08:30:00Z
    try:
        if s.endswith("Z"):
            s2 = s[:-1] + "+00:00"
            return datetime.fromisoformat(s2).date()
        return datetime.fromisoformat(s).date()
    except Exception:
        pass
    # Fallback: YYYY-MM-DD...
    try:
        return date.fromisoformat(s[:10])
    except Exception:
        return None


def fetch_newapi_everything(
    *,
    q: str,
    date_from: str,
    date_to: str,
    language: str = "en",
    sort_by: str = "publishedAt",
    page_size: int = 100,
    max_items: int = 200,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch articles from NewAPI-like provider.

    Returns:
        (articles, meta)
    """
    cfg = _load_cfg()
    meta: Dict[str, Any] = {
        "provider": "newapi",
        "enabled": bool(cfg.api_key),
        "base_url": cfg.base_url,
        "q": q,
        "from": date_from,
        "to": date_to,
        "language": language,
        "sortBy": sort_by,
        "page_size": int(page_size),
        "max_items": int(max_items),
        "pages_fetched": 0,
        "status": "skipped" if not cfg.api_key else "ok",
        "error": None,
    }
    if not cfg.api_key:
        return [], meta

    try:
        import requests
    except Exception as exc:
        meta["status"] = "error"
        meta["error"] = f"requests import failed: {exc!r}"
        return [], meta

    page_size = int(max(1, min(int(page_size), 100)))
    # NewsAPI.org: at most 100 articles per /everything request (single page on many tiers).
    max_items = int(max(0, min(int(max_items), 100)))
    if max_items == 0:
        return [], meta

    url = f"{cfg.base_url}/v2/everything"
    headers = {"X-Api-Key": cfg.api_key, "User-Agent": cfg.user_agent}
    params_base = {
        "q": q,
        "from": date_from,
        "to": date_to,
        "language": language,
        "sortBy": sort_by,
        "pageSize": page_size,
    }

    out: List[Dict[str, Any]] = []
    page = 1
    while len(out) < max_items:
        params = dict(params_base)
        params["page"] = page
        try:
            r = requests.get(url, params=params, headers=headers, timeout=cfg.timeout_sec)
            js = r.json() if r.content else {}
        except Exception as exc:
            meta["status"] = "error"
            meta["error"] = f"request failed: {exc!r}"
            break

        if not isinstance(js, dict):
            meta["status"] = "error"
            meta["error"] = "non-dict json response"
            break
        if not r.ok:
            meta["status"] = "error"
            meta["error"] = str(js.get("message") or js.get("error") or f"http {r.status_code}")
            break

        articles = js.get("articles") or []
        if not isinstance(articles, list) or not articles:
            meta["pages_fetched"] = int(meta["pages_fetched"]) + 1
            break

        for a in articles:
            if not isinstance(a, dict):
                continue
            out.append(a)
            if len(out) >= max_items:
                break

        meta["pages_fetched"] = int(meta["pages_fetched"]) + 1
        if len(out) >= max_items:
            break
        # Short page ⇒ no further results; do not request page+1 (developer tier errors on offset ≥100).
        if len(articles) < page_size:
            break
        page += 1
        if page > 20:
            break

    return out[:max_items], meta


# Day index d ∈ [1,30]: calendar day = test_start + (d-1), clipped to [test_start, as_of].
_VADER_BIN_THRESHOLDS = (-0.6, -0.2, 0.2, 0.6)


def _day_index_to_date(test_start: date, d: int, as_of: date) -> date:
    d = int(max(1, min(30, d)))
    cal = test_start + timedelta(days=d - 1)
    if cal < test_start:
        return test_start
    if cal > as_of:
        return as_of
    return cal


def generate_random_interval_endpoints_1_30(rng: random.Random, *, max_tries: int = 800) -> List[int]:
    """Strictly increasing integers in [1,30] with first 1, last 30, adjacent gaps in {2,3,4}."""
    for _ in range(max_tries):
        cur = 30
        rev: List[int] = [30]
        ok = True
        while cur > 1:
            choices = [s for s in (2, 3, 4) if cur - s >= 1]
            if not choices:
                ok = False
                break
            step = rng.choice(choices)
            cur -= step
            rev.append(cur)
            if cur == 1:
                break
        if not ok or rev[-1] != 1:
            continue
        rev.reverse()
        diffs = [rev[i + 1] - rev[i] for i in range(len(rev) - 1)]
        if all(d in (2, 3, 4) for d in diffs):
            return rev
    return [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 30]


def _calendar_intervals_from_endpoints(
    test_start: date, as_of: date, endpoints: List[int]
) -> List[Tuple[date, date]]:
    out: List[Tuple[date, date]] = []
    for i in range(len(endpoints) - 1):
        d_lo, d_hi = endpoints[i], endpoints[i + 1]
        a = _day_index_to_date(test_start, d_lo, as_of)
        b = _day_index_to_date(test_start, d_hi, as_of)
        if a > b:
            a, b = b, a
        out.append((a, b))
    return out


def _vader_stratified_pick_rows(
    rows: List[Tuple[str, date, str, str]], sia: Any, cap: int
) -> List[Tuple[str, date, str, str]]:
    """Round-robin across 5 VADER compound bins for roughly uniform semantic coverage."""
    if cap <= 0 or not rows:
        return []
    buckets: List[List[Tuple[str, date, str, str]]] = [[] for _ in range(5)]
    for row in rows:
        title = str(row[0] or "").strip()
        if not title:
            continue
        try:
            c = float(sia.polarity_scores(title)["compound"])
        except Exception:
            continue
        bi = bisect_left(_VADER_BIN_THRESHOLDS, c)
        bi = int(max(0, min(4, bi)))
        buckets[bi].append(row)
    picked: List[Tuple[str, date, str, str]] = []
    guard = 0
    while len(picked) < cap and guard < cap * 10:
        progressed = False
        for bi in range(5):
            if len(picked) >= cap:
                break
            b = buckets[bi]
            if b:
                picked.append(b.pop(0))
                progressed = True
        if not progressed:
            break
        guard += 1
    # Drain remainder without strict bin balance
    for bi in range(5):
        while len(picked) < cap and buckets[bi]:
            picked.append(buckets[bi].pop(0))
    return picked[:cap]


def fetch_newapi_headlines_interval_vader(
    *,
    q: str,
    max_items: int,
    test_start: date,
    as_of: date,
    language: str = "en",
    rng: random.Random,
) -> Tuple[List[Tuple[str, date, str, str]], Dict[str, Any]]:
    """One NewsAPI ``/everything`` call per random [1..30] day-index interval; VADER-balanced picks.

    Day index ``d`` maps to ``min(test_start + (d-1), as_of)``. Endpoints are monotone on
    ``1..30`` with consecutive gaps in ``{2,3,4}``, endpoints include 1 and 30.
    """
    cfg = _load_cfg()
    meta: Dict[str, Any] = {
        "provider": "newapi",
        "enabled": bool(cfg.api_key),
        "fetch_mode": "interval_vader",
        "status": "skipped" if not cfg.api_key else "ok",
        "error": None,
        "test_start": test_start.isoformat(),
        "as_of": as_of.isoformat(),
        "interval_endpoints_day_index": [],
        "intervals": [],
        "articles_raw": 0,
        "headlines_out": 0,
    }
    if not cfg.api_key:
        return [], meta

    try:
        inter = float((os.environ.get("NEWSAPI_INTER_REQUEST_SEC") or "0.12").strip())
    except ValueError:
        inter = 0.12
    inter = float(max(0.0, min(inter, 5.0)))

    endpoints = generate_random_interval_endpoints_1_30(rng)
    meta["interval_endpoints_day_index"] = list(endpoints)
    intervals = _calendar_intervals_from_endpoints(test_start, as_of, endpoints)
    n_iv = max(1, len(intervals))
    try:
        head_cap = int((os.environ.get("NEWSAPI_HEADLINES_CAP") or "2000").strip())
    except ValueError:
        head_cap = 2000
    head_cap = int(max(1, min(head_cap, 5000)))
    max_items = int(max(0, min(int(max_items), head_cap)))
    per_interval_cap = max(5, (max_items + n_iv - 1) // n_iv) if max_items else 0

    try:
        from research.sentiment_proxy import _make_vader_analyzer

        sia = _make_vader_analyzer()
    except Exception as exc:
        meta["status"] = "error"
        meta["error"] = f"vader init failed: {exc!r}"
        return [], meta

    seen_keys: Set[str] = set()
    pooled: List[Tuple[str, date, str, str]] = []
    raw_total = 0

    for a0, b0 in intervals:
        iv_meta: Dict[str, Any] = {
            "from": a0.isoformat(),
            "to": b0.isoformat(),
            "raw_articles": 0,
            "after_vader_pick": 0,
        }
        arts, m_day = fetch_newapi_everything(
            q=q,
            date_from=a0.isoformat(),
            date_to=b0.isoformat(),
            language=language,
            sort_by="publishedAt",
            page_size=100,
            max_items=100,
        )
        if m_day.get("status") == "error" and m_day.get("error"):
            iv_meta["api_error"] = m_day["error"]
        rows_iv: List[Tuple[str, date, str, str]] = []
        for a in arts:
            if not isinstance(a, dict):
                continue
            title = str(a.get("title") or "").strip()
            if not title:
                continue
            raw_pub = a.get("publishedAt") or a.get("published_at") or a.get("published")
            raw_str = str(raw_pub).strip() if raw_pub is not None else ""
            pub = _parse_published_at(raw_pub)
            if pub is None or pub < a0 or pub > b0:
                continue
            src_obj = a.get("source") or {}
            src = ""
            if isinstance(src_obj, dict):
                src = str(src_obj.get("name") or src_obj.get("id") or "").strip()
            if not src:
                src = str(a.get("source") or "").strip()
            src = src or "newapi"
            rows_iv.append((title, pub, f"newapi:{src}", raw_str))
        raw_total += len(rows_iv)
        iv_meta["raw_articles"] = len(rows_iv)
        picked = _vader_stratified_pick_rows(rows_iv, sia, per_interval_cap)
        iv_meta["after_vader_pick"] = len(picked)
        for row in picked:
            k = row[0].lower()[:160]
            if k in seen_keys:
                continue
            seen_keys.add(k)
            pooled.append(row)
        meta["intervals"].append(iv_meta)
        if inter > 0:
            time.sleep(inter)

    meta["articles_raw"] = raw_total
    pooled.sort(key=lambda x: (x[1], x[3] or "", x[2], x[0][:80]))
    out = pooled[:max_items]
    meta["headlines_out"] = len(out)
    meta["status"] = "ok"
    return out, meta


def fetch_newapi_headlines(
    *,
    q: str,
    max_items: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    language: str = "en",
    only_days: Optional[Sequence[date]] = None,
) -> Tuple[List[Tuple[str, date, str, str]], Dict[str, Any]]:
    """Fetch (title, published_date, source_label, publishedAt_raw) tuples.

    **Modes**

    - ``only_days`` **None** (default): walk **every** calendar day from ``date_from``
      through ``date_to`` (oldest first), one ``/everything`` call per day (≤100 rows
      each), then dedupe and sort oldest-first.
    - ``only_days`` **non-empty**: request **only** those dates (after clipping to
      ``[date_from, date_to]``), sorted — for RSS-gap sampling with few API calls.
    - ``only_days`` **empty list**: return no rows (no HTTP).

    ``publishedAt_raw`` is the provider's original ``publishedAt`` string when present
    (e.g. ``2026-04-16T08:30:00Z``). Calendar ``published_date`` is derived from it for
    window checks and merge logic.
    """
    cfg = _load_cfg()
    to_d = date_to or date.today()
    try:
        lb = int((os.environ.get("NEWSAPI_LOOKBACK_DAYS") or "29").strip())
    except ValueError:
        lb = 29
    lb = int(max(1, min(lb, 364)))
    from_d = date_from or (to_d - timedelta(days=lb))
    if from_d > to_d:
        from_d, to_d = to_d, from_d

    try:
        head_cap = int((os.environ.get("NEWSAPI_HEADLINES_CAP") or "2000").strip())
    except ValueError:
        head_cap = 2000
    head_cap = int(max(1, min(head_cap, 5000)))

    try:
        max_raw = int((os.environ.get("NEWSAPI_MAX_RAW_ARTICLES") or "2500").strip())
    except ValueError:
        max_raw = 2500
    max_raw = int(max(50, min(max_raw, 20000)))

    try:
        inter = float((os.environ.get("NEWSAPI_INTER_REQUEST_SEC") or "0.12").strip())
    except ValueError:
        inter = 0.12
    inter = float(max(0.0, min(inter, 5.0)))

    meta: Dict[str, Any] = {
        "provider": "newapi",
        "enabled": bool(cfg.api_key),
        "base_url": cfg.base_url,
        "q": q,
        "from": from_d.isoformat(),
        "to": to_d.isoformat(),
        "language": language,
        "sortBy": "publishedAt",
        "status": "skipped" if not cfg.api_key else "ok",
        "error": None,
        "per_day_errors": [],
        "articles_raw": 0,
        "pages_fetched_total": 0,
    }
    if not cfg.api_key:
        meta["headlines_out"] = 0
        return [], meta

    if only_days is not None and len(list(only_days)) == 0:
        meta["fetch_mode"] = "only_days"
        meta["days_requested"] = 0
        meta["headlines_out"] = 0
        meta["status"] = "ok"
        return [], meta

    seen_keys: Set[str] = set()
    raw_rows: List[Dict[str, Any]] = []
    if only_days is None:
        day_iter: List[date] = []
        dc = from_d
        while dc <= to_d:
            day_iter.append(dc)
            dc += timedelta(days=1)
    else:
        day_iter = sorted({d for d in only_days if from_d <= d <= to_d})
    meta["fetch_mode"] = "only_days" if only_days is not None else "daily_chronological_full"
    meta["days_requested"] = len(day_iter)

    for day_cur in day_iter:
        if len(raw_rows) >= max_raw:
            break
        arts, m_day = fetch_newapi_everything(
            q=q,
            date_from=day_cur.isoformat(),
            date_to=day_cur.isoformat(),
            language=language,
            sort_by="publishedAt",
            page_size=100,
            max_items=100,
        )
        meta["pages_fetched_total"] = int(meta.get("pages_fetched_total") or 0) + int(
            m_day.get("pages_fetched") or 0
        )
        if m_day.get("status") == "error" and m_day.get("error"):
            meta["per_day_errors"].append({"day": day_cur.isoformat(), "error": m_day["error"]})
        for a in arts:
            if not isinstance(a, dict):
                continue
            url = str(a.get("url") or "").strip()
            title = str(a.get("title") or "").strip()
            raw_pub = a.get("publishedAt") or a.get("published_at") or a.get("published")
            dedupe_key = url if url else f"{title[:220].lower()}|{raw_pub!s}"
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            raw_rows.append(a)
            if len(raw_rows) >= max_raw:
                break
        if inter > 0:
            time.sleep(inter)

    meta["articles_raw"] = len(raw_rows)

    out: List[Tuple[str, date, str, str]] = []
    for a in raw_rows:
        title = str(a.get("title") or "").strip()
        if not title:
            continue
        raw_pub = a.get("publishedAt") or a.get("published_at") or a.get("published")
        raw_str = str(raw_pub).strip() if raw_pub is not None else ""
        pub = _parse_published_at(raw_pub)
        if pub is None:
            continue
        src_obj = a.get("source") or {}
        src = ""
        if isinstance(src_obj, dict):
            src = str(src_obj.get("name") or src_obj.get("id") or "").strip()
        if not src:
            src = str(a.get("source") or "").strip()
        src = src or "newapi"
        if pub < from_d or pub > to_d:
            continue
        out.append((title, pub, f"newapi:{src}", raw_str))

    take = int(min(max_items, head_cap, len(out)))
    out.sort(key=lambda x: (x[1], x[3] or "", x[2], x[0][:80]))
    meta["headlines_out"] = take
    if out:
        meta["status"] = "ok"
    elif meta.get("per_day_errors"):
        meta["status"] = "error"
        if not meta.get("error"):
            meta["error"] = meta["per_day_errors"][0].get("error")
    return out[:take], meta

