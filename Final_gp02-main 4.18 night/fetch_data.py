import json
import os
import argparse
from dataclasses import dataclass
from datetime import date, datetime, timezone
from io import StringIO
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

from ass1_core import load_json_first_document


@dataclass(frozen=True)
class FetchConfig:
    # Step 2: 起始日期 = Today - 3 Years
    start: str = (datetime.now() - pd.DateOffset(years=3)).strftime("%Y-%m-%d")
    end: str = datetime.now().strftime("%Y-%m-%d")
    zscore_threshold: float = 3.0


def check_symbol_validity(symbol: str) -> bool:
    """
    Step 2: 实现 check_symbol_validity 函数
    检查标的是否存在且有交易数据
    """
    import akshare as ak
    try:
        # 简单尝试获取最近一天的行情来验证
        if symbol.upper() == "AU0":
            df = ak.futures_main_ak(symbol="AU0")
        else:
            # 尝试美股
            df = ak.stock_us_daily(symbol=symbol.upper(), adjust="qfq")
        return not df.empty
    except:
        return False


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _to_yyyymmdd(date_str: str) -> str:
    return date_str.replace("-", "")


_REQUESTS_HTTP_PATCHED = False
_SYMBOL_ALIASES = {"TSMC": "TSM"}


def _enable_http_for_requests(logs: List[Dict[str, Any]]):
    global _REQUESTS_HTTP_PATCHED
    if _REQUESTS_HTTP_PATCHED:
        return
    import requests

    original = requests.sessions.Session.request

    def patched(self, method, url, *args, **kwargs):
        if isinstance(url, str) and url.startswith("https://"):
            url = "http://" + url[len("https://") :]
        return original(self, method, url, *args, **kwargs)

    requests.sessions.Session.request = patched
    _REQUESTS_HTTP_PATCHED = True
    logs.append({"time": _now_iso(), "level": "INFO", "code": "REQUESTS_HTTP_PATCHED", "message": "force https->http"})


def _normalize_us_hist_symbol(symbol: str) -> str:
    s = symbol.strip()
    if "." in s:
        return s
    return f"105.{s}"


def _standardize_date_close(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "close"])
    out = df.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]

    date_col = None
    for c in ["date", "日期", "time", "datetime", "timestamp"]:
        if c.lower() in out.columns:
            date_col = c.lower()
            break
    close_col = None
    for c in ["close", "收盘价", "收盘", "close_price", "closing"]:
        if c.lower() in out.columns:
            close_col = c.lower()
            break

    if date_col is None or close_col is None:
        raise RuntimeError(f"无法识别 date/close 列: columns={list(out.columns)}")

    out = out[[date_col, close_col]].rename(columns={date_col: "date", close_col: "close"})
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.date.astype("string")
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    out = out.dropna(subset=["date", "close"])
    out["date"] = out["date"].astype(str)
    out = out.sort_values("date").reset_index(drop=True)
    return out


def _filter_date_range(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "close"])
    m = (df["date"] >= start) & (df["date"] <= end)
    out = df.loc[m].copy()
    out = out.sort_values("date").reset_index(drop=True)
    return out


def _dedup_by_date(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "close"]), 0
    before = len(df)
    out = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return out, before - len(out)


def _zscore_filter_on_returns(df: pd.DataFrame, threshold: float) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    if df is None or df.empty or len(df) < 5:
        return df, []
    out = df.copy()
    out["ret"] = out["close"].pct_change()
    rets = out["ret"].to_numpy(dtype=float)
    mask = np.isfinite(rets)
    if mask.sum() < 5:
        out = out.drop(columns=["ret"])
        return out, []
    mu = float(np.nanmean(rets[mask]))
    sigma = float(np.nanstd(rets[mask]))
    if sigma == 0.0 or not np.isfinite(sigma):
        out = out.drop(columns=["ret"])
        return out, []
    z = (rets - mu) / sigma
    outliers: List[Dict[str, Any]] = []
    keep = np.ones(len(out), dtype=bool)
    for i in range(len(out)):
        if not np.isfinite(z[i]):
            continue
        if abs(float(z[i])) > threshold:
            keep[i] = False
            outliers.append(
                {"date": str(out["date"].iloc[i]), "close": float(out["close"].iloc[i]), "ret": float(rets[i]), "z": float(z[i])}
            )
    out = out.loc[keep].drop(columns=["ret"]).reset_index(drop=True)
    return out, outliers


def fetch_us_daily_qfq(symbol: str, start: str, end: str, logs: List[Dict[str, Any]]) -> pd.DataFrame:
    _enable_http_for_requests(logs)
    try:
        import akshare as ak
    except Exception as e:
        logs.append({"time": _now_iso(), "level": "ERROR", "code": "AK_IMPORT_FAIL", "message": str(e), "context": {"symbol": symbol}})
        raise

    def _fetch_yahoo_chart_daily(sym: str) -> pd.DataFrame:
        """
        Fallback US daily close from Yahoo Finance chart API (urllib only — avoids
        ``requests`` https→http monkeypatch used for AkShare).
        """
        import pandas as _pd

        s = sym.strip().upper()

        def _utc_ts(dstr: str) -> int:
            return int(datetime.strptime(dstr[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())

        t0 = _utc_ts(start)
        t1 = _utc_ts(end) + 86400 * 5
        qs = urllib.parse.urlencode({"period1": t0, "period2": t1, "interval": "1d"})
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?{qs}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            logs.append(
                {
                    "time": _now_iso(),
                    "level": "ERROR",
                    "code": "YAHOO_CHART_HTTP",
                    "message": str(e),
                    "context": {"symbol": s, "url": url},
                }
            )
            raise
        except Exception as e:
            logs.append(
                {"time": _now_iso(), "level": "ERROR", "code": "YAHOO_CHART_FETCH_FAIL", "message": str(e), "context": {"symbol": s, "url": url}}
            )
            raise

        try:
            js = json.loads(raw)
        except json.JSONDecodeError as e:
            logs.append({"time": _now_iso(), "level": "ERROR", "code": "YAHOO_CHART_JSON", "message": str(e), "context": {"symbol": s}})
            raise

        chart = js.get("chart") or {}
        err = chart.get("error")
        if err:
            logs.append({"time": _now_iso(), "level": "ERROR", "code": "YAHOO_CHART_ERR", "message": str(err), "context": {"symbol": s}})
            raise RuntimeError(str(err))
        results = chart.get("result") or []
        if not results:
            logs.append({"time": _now_iso(), "level": "ERROR", "code": "YAHOO_CHART_EMPTY", "message": "no result", "context": {"symbol": s}})
            raise RuntimeError("Yahoo chart: empty result")

        res = results[0]
        ts_list = res.get("timestamp") or []
        quotes = ((res.get("indicators") or {}).get("quote") or [{}])[0]
        closes = quotes.get("close") or []
        if not ts_list or not closes or len(ts_list) != len(closes):
            logs.append(
                {
                    "time": _now_iso(),
                    "level": "ERROR",
                    "code": "YAHOO_CHART_SHAPE",
                    "message": "timestamp/close mismatch",
                    "context": {"symbol": s, "n_ts": len(ts_list), "n_c": len(closes)},
                }
            )
            raise RuntimeError("Yahoo chart: timestamp/close length mismatch")

        rows: List[Dict[str, Any]] = []
        for t, c in zip(ts_list, closes):
            if t is None or c is None:
                continue
            d = datetime.fromtimestamp(int(t), tz=timezone.utc).date().isoformat()
            rows.append({"date": d, "close": float(c)})
        out = _pd.DataFrame(rows)
        if out.empty:
            logs.append({"time": _now_iso(), "level": "ERROR", "code": "YAHOO_CHART_NOROWS", "message": "no valid bars", "context": {"symbol": s}})
            raise RuntimeError("Yahoo chart: no valid rows after filtering")
        out = out.sort_values("date").reset_index(drop=True)
        logs.append({"time": _now_iso(), "level": "INFO", "code": "YAHOO_CHART_OK", "message": "yahoo chart v8", "context": {"symbol": s}})
        return out

    def _fetch_stooq(sym: str) -> pd.DataFrame:
        """
        Fallback US daily close from Stooq CSV.
        - URL format: https://stooq.com/q/d/l/?s=spy.us&i=d
        - Columns: Date, Open, High, Low, Close, Volume
        - Stooq may require ``STOOQ_API_KEY`` in env (plain CSV without key returns instructions, not data).
        """
        import pandas as _pd

        stooq_code = f"{sym.strip().lower()}.us"
        apikey = os.environ.get("STOOQ_API_KEY", "").strip()
        url = f"https://stooq.com/q/d/l/?s={stooq_code}&i=d"
        if apikey:
            url = f"{url}&apikey={urllib.parse.quote(apikey)}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            logs.append({"time": _now_iso(), "level": "ERROR", "code": "STOOQ_FETCH_FAIL", "message": str(e), "context": {"symbol": sym, "url": url}})
            raise

        if "Get your apikey" in raw or raw.lstrip().lower().startswith("get your apikey"):
            msg = "Stooq 已要求 apikey；未设置 STOOQ_API_KEY 时无法使用该源"
            logs.append({"time": _now_iso(), "level": "WARN", "code": "STOOQ_APIKEY_REQUIRED", "message": msg, "context": {"symbol": sym}})
            raise RuntimeError(msg)

        header_idx = None
        lines = raw.splitlines()
        for i, line in enumerate(lines):
            low = line.strip().lower()
            if low.startswith("date,") or ("," in line and "date" in low and "close" in low):
                header_idx = i
                break
        if header_idx is None:
            logs.append(
                {
                    "time": _now_iso(),
                    "level": "ERROR",
                    "code": "STOOQ_NOT_CSV",
                    "message": "response is not a Stooq CSV",
                    "context": {"symbol": sym, "preview": raw[:200]},
                }
            )
            raise RuntimeError("Stooq: response is not a recognizable CSV")

        body = "\n".join(lines[header_idx:])
        try:
            df = _pd.read_csv(StringIO(body), engine="python", on_bad_lines="skip")
        except TypeError:
            df = _pd.read_csv(StringIO(body), engine="python", error_bad_lines=False, warn_bad_lines=False)

        if df is None or df.empty:
            logs.append({"time": _now_iso(), "level": "ERROR", "code": "STOOQ_EMPTY", "message": "empty dataframe", "context": {"symbol": sym, "url": url}})
            return _pd.DataFrame(columns=["date", "close"])
        cols = {c.lower(): c for c in df.columns}
        if "date" not in cols or "close" not in cols:
            raise RuntimeError(f"Stooq CSV 缺少 Date/Close 列: columns={list(df.columns)}")
        out = df[[cols["date"], cols["close"]]].rename(columns={cols["date"]: "date", cols["close"]: "close"})
        out["date"] = _pd.to_datetime(out["date"], errors="coerce").dt.date.astype("string")
        out["close"] = _pd.to_numeric(out["close"], errors="coerce")
        out = out.dropna(subset=["date", "close"])
        out["date"] = out["date"].astype(str)
        out = out.sort_values("date").reset_index(drop=True)
        logs.append({"time": _now_iso(), "level": "INFO", "code": "STOOQ_OK", "message": "stooq csv", "context": {"symbol": sym, "url": url}})
        return out

    df = None
    try:
        df = ak.stock_us_daily(symbol=symbol, adjust="qfq")
        logs.append({"time": _now_iso(), "level": "INFO", "code": "AK_US_DAILY_OK", "message": "stock_us_daily", "context": {"symbol": symbol}})
    except Exception as e:
        logs.append({"time": _now_iso(), "level": "WARN", "code": "AK_US_DAILY_FAIL", "message": str(e), "context": {"symbol": symbol}})

    if df is None or getattr(df, "empty", True):
        try:
            df = ak.stock_us_hist(
                symbol=_normalize_us_hist_symbol(symbol),
                period="daily",
                start_date=_to_yyyymmdd(start),
                end_date=_to_yyyymmdd(end),
                adjust="qfq",
            )
            if df is None or getattr(df, "empty", True):
                raise RuntimeError("stock_us_hist returned empty/None")
            logs.append({"time": _now_iso(), "level": "INFO", "code": "AK_US_HIST_OK", "message": "stock_us_hist", "context": {"symbol": symbol}})
        except Exception as e:
            # AkShare sometimes returns None payload or breaks on US tickers/ETFs.
            logs.append({"time": _now_iso(), "level": "WARN", "code": "AK_US_HIST_FAIL", "message": str(e), "context": {"symbol": symbol}})
            try:
                df = _fetch_yahoo_chart_daily(symbol)
            except Exception as e_y:
                logs.append(
                    {
                        "time": _now_iso(),
                        "level": "WARN",
                        "code": "YAHOO_CHART_FALLBACK_FAIL",
                        "message": str(e_y),
                        "context": {"symbol": symbol},
                    }
                )
                df = _fetch_stooq(symbol)
            return _filter_date_range(df, start, end)

    return _standardize_date_close(df)


def fetch_futures_au0_daily(symbol: str, start: str, end: str, logs: List[Dict[str, Any]]) -> pd.DataFrame:
    _enable_http_for_requests(logs)
    try:
        import akshare as ak
    except Exception as e:
        logs.append({"time": _now_iso(), "level": "ERROR", "code": "AK_IMPORT_FAIL", "message": str(e), "context": {"symbol": symbol}})
        raise

    y1 = _to_yyyymmdd(start)
    y2 = _to_yyyymmdd(end)

    if not hasattr(ak, "futures_main_sina"):
        raise RuntimeError("当前 AkShare 版本缺少 futures_main_sina，无法拉取 AU0")

    last_err: Optional[Exception] = None
    for sym_try in [symbol, symbol.upper(), symbol.lower()]:
        try:
            df = ak.futures_main_sina(symbol=sym_try, start_date=y1, end_date=y2)
            logs.append(
                {"time": _now_iso(), "level": "INFO", "code": "AK_FUT_MAIN_SINA_OK", "message": "futures_main_sina", "context": {"symbol": sym_try}}
            )
            return _standardize_date_close(df)
        except Exception as e:
            last_err = e
            logs.append(
                {"time": _now_iso(), "level": "WARN", "code": "AK_FUT_MAIN_SINA_FAIL", "message": str(e), "context": {"symbol": sym_try}}
            )
    raise RuntimeError(str(last_err) if last_err is not None else "futures_main_sina failed")


def _summary_stats(symbol: str, df_raw: pd.DataFrame, df_clean: pd.DataFrame, outliers: List[Dict[str, Any]], dup_removed: int) -> Dict[str, Any]:
    s: Dict[str, Any] = {
        "symbol": symbol,
        "n_raw": int(len(df_raw)) if df_raw is not None else 0,
        "n_clean": int(len(df_clean)) if df_clean is not None else 0,
        "duplicate_date_removed": int(dup_removed),
        "zscore_outlier_removed_count": int(len(outliers)),
    }
    if df_clean is None or df_clean.empty:
        return s
    closes = df_clean["close"].astype(float)
    s.update(
        {
            "date_min": str(df_clean["date"].iloc[0]),
            "date_max": str(df_clean["date"].iloc[-1]),
            "close_mean": float(closes.mean()),
            "close_min": float(closes.min()),
            "close_max": float(closes.max()),
            "first_close": float(closes.iloc[0]),
            "last_close": float(closes.iloc[-1]),
        }
    )
    return s


def _monthly_means(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    tmp = df.copy()
    tmp["ym"] = tmp["date"].str.slice(0, 7)
    g = tmp.groupby("ym", as_index=False).agg(mean_close=("close", "mean"), n=("close", "count"))
    out = []
    for _, r in g.iterrows():
        out.append({"month": str(r["ym"]), "mean_close": float(r["mean_close"]), "n": int(r["n"])})
    out = sorted(out, key=lambda x: x["month"])
    return out


def _default_symbols() -> Tuple[List[str], List[str]]:
    # Align with Phase0.md universe (tech, hedge, safe, benchmark)
    assets = ["SPY", "GLD", "TLT", "XLE", "USO", "AU0"]
    stocks = ["NVDA", "MSFT", "TSMC", "GOOGL", "AAPL"]
    return assets, stocks


def _universe_symbols() -> List[str]:
    assets, stocks = _default_symbols()
    # Keep list stable for output ordering, but MUST be unique (duplicate columns break pandas selection)
    ordered = [*stocks, "XLE", "USO", "GLD", "TLT", "SPY", "AU0"]
    seen = set()
    out: List[str] = []
    for s in ordered:
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _train_test_meta(cfg: FetchConfig) -> Dict[str, str]:
    from research.sentiment_calendar import DEFAULT_TEST_START

    train_start = "2024-01-01"
    train_end = "2026-01-31"
    test_start = DEFAULT_TEST_START
    test_end = min(cfg.end, date.today().isoformat())
    return {
        "train_start": max(cfg.start, train_start),
        "train_end": min(cfg.end, train_end),
        "test_start": max(cfg.start, test_start),
        "test_end": test_end,
    }


def _new_payload(cfg: FetchConfig) -> Dict[str, Any]:
    assets, stocks = _default_symbols()
    universe = _universe_symbols()
    split = _train_test_meta(cfg)
    return {
        "meta": {
            "source": "akshare",
            "generated_at": _now_iso(),
            "start": cfg.start,
            "end": cfg.end,
            "assets": assets,
            "stocks": stocks,
            "universe": universe,
            **split,
            "zscore_threshold": cfg.zscore_threshold,
        },
        "assets": {},
        "stocks": {},
        "summary": {"assets": {}, "stocks": {}},
        "outliers": {},
        "monthly_means": {},
        "logs": [],
    }


def _load_payload(path: str, cfg: FetchConfig) -> Dict[str, Any]:
    if not os.path.exists(path):
        return _new_payload(cfg)
    data = load_json_first_document(path)
    if "meta" not in data:
        return _new_payload(cfg)
    assets, stocks = _default_symbols()
    universe = _universe_symbols()
    split = _train_test_meta(cfg)
    data["meta"]["generated_at"] = _now_iso()
    data["meta"]["start"] = cfg.start
    data["meta"]["end"] = cfg.end
    data["meta"]["zscore_threshold"] = cfg.zscore_threshold
    data["meta"]["assets"] = assets
    data["meta"]["stocks"] = stocks
    data["meta"]["universe"] = universe
    data["meta"].update(split)
    for k in ["assets", "stocks", "summary", "outliers", "monthly_means", "logs"]:
        if k not in data:
            data[k] = {} if k != "logs" else []
    if "assets" not in data["summary"]:
        data["summary"]["assets"] = {}
    if "stocks" not in data["summary"]:
        data["summary"]["stocks"] = {}
    return data


def _write_outputs(out_dir: str, payload: Dict[str, Any]):
    json_path = os.path.join(out_dir, "data.json")
    txt_path = os.path.join(out_dir, "read.txt")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    universe = payload.get("meta", {}).get("universe", None) or _universe_symbols()
    lines: List[str] = []
    for sym in universe:
        lines.append(sym)
        for row in payload.get("monthly_means", {}).get(sym, []):
            lines.append(f"  {row['month']}: mean_close={row['mean_close']:.6f}, n={row['n']}")
        lines.append("")
    read_txt = "\n".join(lines).rstrip() + "\n"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(read_txt)


def download_one(cfg: FetchConfig, symbol: str, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    logs: List[Dict[str, Any]] = []
    sym = symbol.strip().upper()
    fetch_sym = _SYMBOL_ALIASES.get(sym, sym)
    if fetch_sym != sym:
        logs.append({"time": _now_iso(), "level": "INFO", "code": "SYMBOL_ALIAS", "message": "alias", "context": {"symbol": sym, "fetch_symbol": fetch_sym}})
    if sym == "AU0":
        df0 = fetch_futures_au0_daily(sym, cfg.start, cfg.end, logs)
    else:
        df0 = fetch_us_daily_qfq(fetch_sym, cfg.start, cfg.end, logs)
    df0 = _filter_date_range(df0, cfg.start, cfg.end)
    df1, dup_removed = _dedup_by_date(df0)
    df2, outliers = _zscore_filter_on_returns(df1, cfg.zscore_threshold)

    if kind == "asset":
        payload["assets"][sym] = df2.to_dict(orient="records")
        payload["summary"]["assets"][sym] = _summary_stats(sym, df0, df2, outliers, dup_removed)
    else:
        payload["stocks"][sym] = df2.to_dict(orient="records")
        payload["summary"]["stocks"][sym] = _summary_stats(sym, df0, df2, outliers, dup_removed)
    payload["outliers"][sym] = outliers
    payload["monthly_means"][sym] = _monthly_means(df2)

    payload["logs"].extend(logs)
    payload["logs"].append(
        {
            "time": _now_iso(),
            "level": "INFO",
            "code": "SYMBOL_DONE",
            "message": "processed",
            "context": {"symbol": sym, "kind": kind, "n_raw": int(len(df0)), "n_clean": int(len(df2)), "dup_removed": int(dup_removed), "outliers": int(len(outliers))},
        }
    )
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=str, default=FetchConfig.start)
    parser.add_argument("--end", type=str, default=FetchConfig.end)
    parser.add_argument("--z", type=float, default=FetchConfig.zscore_threshold)
    parser.add_argument("--symbol", type=str, default="")
    parser.add_argument("--all", action="store_true", help="Download all symbols in universe")
    parser.add_argument("--kind", type=str, choices=["asset", "stock"], default="")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    cfg = FetchConfig(start=args.start, end=args.end, zscore_threshold=float(args.z))
    out_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "data.json")

    if args.reset:
        payload = _new_payload(cfg)
    else:
        payload = _load_payload(json_path, cfg)

    assets, stocks = _default_symbols()
    
    if args.all:
        target_symbols = _universe_symbols()
    else:
        sym = args.symbol.strip().upper()
        if not sym:
            raise RuntimeError("必须提供 --symbol 或 --all")
        target_symbols = [sym]

    for sym in target_symbols:
        kind = args.kind
        if not kind:
            kind = "asset" if sym in set(assets) else "stock"
        print(f"Downloading {sym}...")
        payload = download_one(cfg, sym, kind, payload)
    
    _write_outputs(out_dir, payload)


if __name__ == "__main__":
    main()
