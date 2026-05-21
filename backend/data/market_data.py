"""
Market data fetcher for QuantMind Pro.
Primary: yfinance. Fallback: nsepython (NSE).
Caches results as Parquet (zstd compression) in PARQUET_CACHE_DIR.
QuantMind Pro v3.0
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from backend.core.config import settings
from backend.utils.logger import get_logger
from backend.utils.formatters import normalize_symbol, safe_float
from backend.utils.retry import async_retry_with_backoff

logger = get_logger("market_data")

# ---------------------------------------------------------------------------
# Rate limiter (simple in-memory bucket — 100 yfinance calls/hour)
# ---------------------------------------------------------------------------
_yf_calls: list[float] = []
_YF_LIMIT = 100
_YF_WINDOW = 3600  # 1 hour


def _yf_rate_check() -> None:
    """Block if we're approaching the yfinance call limit."""
    now = time.time()
    cutoff = now - _YF_WINDOW
    _yf_calls[:] = [t for t in _yf_calls if t > cutoff]
    if len(_yf_calls) >= _YF_LIMIT:
        sleep_for = _yf_calls[0] + _YF_WINDOW - now
        if sleep_for > 0:
            logger.warning("yfinance rate limit — sleeping", extra={"seconds": round(sleep_for, 1)})
            time.sleep(sleep_for)
    _yf_calls.append(time.time())


# ---------------------------------------------------------------------------
# Parquet cache helpers
# ---------------------------------------------------------------------------
def _parquet_path(symbol: str, interval: str) -> Path:
    base = Path(settings.PARQUET_CACHE_DIR)
    safe_sym = symbol.replace("/", "_").replace(".", "_")
    return base / safe_sym / f"{interval}.parquet"


def _load_parquet(path: Path) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        return pd.read_parquet(path)
    except Exception as exc:
        logger.warning("Parquet load failed", extra={"path": str(path), "error": str(exc)})
        return None


def _save_parquet(df: pd.DataFrame, path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, compression="zstd", index=True)
    except Exception as exc:
        logger.warning("Parquet save failed", extra={"path": str(path), "error": str(exc)})


def _is_cache_fresh(path: Path, max_age_seconds: int) -> bool:
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < max_age_seconds


def _check_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """Flag data quality issues."""
    issues: list[str] = []
    if "Volume" in df.columns and (df["Volume"] == 0).all():
        issues.append("volume_all_zero")
    # Check for gaps > 5 consecutive days (only relevant for daily+ data)
    if len(df) > 10 and isinstance(df.index, pd.DatetimeIndex):
        diffs = df.index.to_series().diff().dt.days.dropna()
        max_gap = int(diffs.max()) if not diffs.empty else 0
        if max_gap > 5:
            issues.append(f"gap_detected_{max_gap}_days")
    return {"quality_score": 100 - len(issues) * 20, "issues": issues}


# ---------------------------------------------------------------------------
# Main fetch function
# ---------------------------------------------------------------------------
@async_retry_with_backoff(max_retries=2, base_delay=2.0, exceptions=(Exception,))
async def fetch_stock_data(
    symbol: str,
    exchange: str = "NSE",
    period: str = "1y",
    interval: str = "1d",
) -> Optional[pd.DataFrame]:
    """Fetch OHLCV data for a stock symbol.

    Parameters
    ----------
    symbol:
        Ticker symbol (e.g. ``"RELIANCE"`` or ``"AAPL"``).
    exchange:
        ``"NSE"``, ``"BSE"``, or ``"NYSE"``/``"NASDAQ"``.
    period:
        yfinance period string: ``"1d"``, ``"5d"``, ``"1mo"``, ``"3mo"``, ``"1y"``, ``"5y"``.
    interval:
        yfinance interval: ``"1m"``, ``"5m"``, ``"15m"``, ``"1h"``, ``"1d"``, ``"1wk"``.

    Returns
    -------
    pd.DataFrame or None
        OHLCV DataFrame with DatetimeIndex, or ``None`` on complete failure.
    """
    yf_symbol = normalize_symbol(symbol, exchange)

    # Cache TTL: 15 min for intraday, 24h for daily+
    is_intraday = interval in ("1m", "2m", "5m", "15m", "30m", "1h")
    max_age = 900 if is_intraday else 86400

    path = _parquet_path(yf_symbol, interval)
    if _is_cache_fresh(path, max_age):
        cached = _load_parquet(path)
        if cached is not None and not cached.empty:
            logger.debug("Cache hit", extra={"symbol": yf_symbol, "interval": interval})
            return cached

    # --- yfinance primary ---
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(None, lambda: _yf_fetch(yf_symbol, period, interval))

    # --- nsepython fallback for NSE ---
    if (df is None or df.empty) and exchange.upper() == "NSE":
        df = await loop.run_in_executor(None, lambda: _jugaad_fetch(symbol, period, interval))

    if df is None or df.empty:
        logger.warning("No data fetched", extra={"symbol": yf_symbol})
        return None

    # Data quality
    quality = _check_data_quality(df)
    if quality["issues"]:
        logger.warning("Data quality issues", extra={"symbol": yf_symbol, "issues": quality["issues"]})

    _save_parquet(df, path)
    return df


def _yf_fetch(symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf  # type: ignore[import]
        _yf_rate_check()
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True, prepost=False)
        if df.empty:
            return None
        df.index = pd.to_datetime(df.index, utc=True)
        df.columns = [c.title() for c in df.columns]
        return df
    except Exception as exc:
        logger.warning("yfinance fetch failed", extra={"symbol": symbol, "error": str(exc)})
        return None


def _jugaad_fetch(symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
    try:
        from nsepython import nse_quote  # type: ignore[import]
        quote = nse_quote(symbol)
        if not quote:
            return None
        # Build a minimal single-row DataFrame from the live quote
        price_info = quote.get("priceInfo", {})
        row = {
            "Open": safe_float(price_info.get("open")),
            "High": safe_float(price_info.get("intraDayHighLow", {}).get("max")),
            "Low": safe_float(price_info.get("intraDayHighLow", {}).get("min")),
            "Close": safe_float(price_info.get("lastPrice")),
            "Volume": safe_float(price_info.get("totalTradedVolume")),
        }
        df = pd.DataFrame([row], index=pd.DatetimeIndex([pd.Timestamp.now(tz="UTC")]))
        return df
    except Exception as exc:
        logger.warning("nsepython fetch failed", extra={"symbol": symbol, "error": str(exc)})
        return None


# ---------------------------------------------------------------------------
# Bulk fetch
# ---------------------------------------------------------------------------
async def fetch_bulk_stocks(
    symbols: list[str],
    exchange: str = "NSE",
    period: str = "1y",
    interval: str = "1d",
) -> Dict[str, Optional[pd.DataFrame]]:
    """Fetch up to 50 stocks concurrently (with rate-limit respect).

    Parameters
    ----------
    symbols:
        List of ticker symbols.
    exchange:
        Exchange code applied to all symbols.
    period:
        Historical period string.
    interval:
        Data interval string.

    Returns
    -------
    dict[str, DataFrame | None]
        Mapping of symbol → DataFrame (or None on failure).
    """
    BATCH = 50
    results: Dict[str, Optional[pd.DataFrame]] = {}

    for i in range(0, len(symbols), BATCH):
        batch = symbols[i : i + BATCH]
        tasks = [fetch_stock_data(s, exchange, period, interval) for s in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        for sym, res in zip(batch, batch_results):
            results[sym] = res if not isinstance(res, Exception) else None

        if i + BATCH < len(symbols):
            await asyncio.sleep(1)  # brief pause between batches

    return results


# ---------------------------------------------------------------------------
# Index data
# ---------------------------------------------------------------------------
async def get_nse_indices() -> Dict[str, Any]:
    """Return current values for major Indian and US indices.

    Returns
    -------
    dict
        ``{index_name: {price, change, change_pct}}``
    """
    index_map = {
        "NIFTY50": "^NSEI",
        "SENSEX": "^BSESN",
        "BANKNIFTY": "^NSEBANK",
        "MIDCAP100": "^CNXMIDCAP",
        "SP500": "^GSPC",
        "NASDAQ": "^IXIC",
    }
    results: Dict[str, Any] = {}
    loop = asyncio.get_event_loop()

    async def _fetch_index(name: str, ticker_sym: str) -> None:
        try:
            import yfinance as yf  # type: ignore[import]
            _yf_rate_check()
            ticker = yf.Ticker(ticker_sym)
            info = await loop.run_in_executor(None, lambda: ticker.fast_info)
            results[name] = {
                "price": safe_float(getattr(info, "last_price", 0)),
                "change": safe_float(getattr(info, "regular_market_previous_close", 0)),
                "change_pct": 0.0,
                "symbol": ticker_sym,
            }
            if results[name]["change"]:
                prev = results[name]["change"]
                cur = results[name]["price"]
                results[name]["change"] = cur - prev
                results[name]["change_pct"] = ((cur - prev) / prev * 100) if prev else 0.0
        except Exception as exc:
            logger.warning("Index fetch failed", extra={"index": name, "error": str(exc)})
            results[name] = {"price": 0, "change": 0, "change_pct": 0, "symbol": ticker_sym}

    await asyncio.gather(*[_fetch_index(n, s) for n, s in index_map.items()])
    return results


# ---------------------------------------------------------------------------
# Options chain
# ---------------------------------------------------------------------------
async def get_options_chain(symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
    """Fetch options chain (calls + puts) for a symbol.

    Returns
    -------
    dict
        ``{"calls": [...], "puts": [...], "expiry_dates": [...]}``
    """
    yf_symbol = normalize_symbol(symbol, exchange)
    loop = asyncio.get_event_loop()

    def _fetch() -> Dict[str, Any]:
        try:
            import yfinance as yf  # type: ignore[import]
            _yf_rate_check()
            ticker = yf.Ticker(yf_symbol)
            expiries = ticker.options
            if not expiries:
                return {"calls": [], "puts": [], "expiry_dates": []}
            # Use nearest expiry
            chain = ticker.option_chain(expiries[0])
            calls = chain.calls.to_dict(orient="records")
            puts = chain.puts.to_dict(orient="records")
            return {"calls": calls, "puts": puts, "expiry_dates": list(expiries)}
        except Exception as exc:
            logger.warning("Options chain failed", extra={"symbol": yf_symbol, "error": str(exc)})
            return {"calls": [], "puts": [], "expiry_dates": []}

    return await loop.run_in_executor(None, _fetch)


# ---------------------------------------------------------------------------
# Corporate actions
# ---------------------------------------------------------------------------
async def get_corporate_actions(symbol: str, exchange: str = "NSE") -> list[Dict[str, Any]]:
    """Fetch dividends, splits, and bonus issues for a symbol.

    Returns
    -------
    list[dict]
        Each element: ``{"date", "type", "value"}``.
    """
    yf_symbol = normalize_symbol(symbol, exchange)
    loop = asyncio.get_event_loop()

    def _fetch() -> list[Dict[str, Any]]:
        try:
            import yfinance as yf  # type: ignore[import]
            _yf_rate_check()
            ticker = yf.Ticker(yf_symbol)
            actions: list[Dict[str, Any]] = []
            divs = ticker.dividends
            if not divs.empty:
                for date_idx, val in divs.items():
                    actions.append({"date": str(date_idx.date()), "type": "dividend", "value": val})
            splits = ticker.splits
            if not splits.empty:
                for date_idx, val in splits.items():
                    actions.append({"date": str(date_idx.date()), "type": "split", "ratio": val})
            return sorted(actions, key=lambda x: x["date"], reverse=True)
        except Exception as exc:
            logger.warning("Corporate actions failed", extra={"symbol": yf_symbol, "error": str(exc)})
            return []

    return await loop.run_in_executor(None, _fetch)


# ---------------------------------------------------------------------------
# Background cache update (called by Celery task)
# ---------------------------------------------------------------------------
async def update_parquet_cache() -> Dict[str, int]:
    """Refresh Parquet cache for a default universe of NSE stocks.

    Returns
    -------
    dict
        ``{"updated": int, "failed": int}``
    """
    from backend.data.market_data import NIFTY50_SYMBOLS

    updated = 0
    failed = 0
    for sym in NIFTY50_SYMBOLS:
        try:
            df = await fetch_stock_data(sym, "NSE", "5d", "1d")
            if df is not None:
                updated += 1
            else:
                failed += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.5)

    logger.info("Parquet cache updated", extra={"updated": updated, "failed": failed})
    return {"updated": updated, "failed": failed}


# ---------------------------------------------------------------------------
# Stock universe
# ---------------------------------------------------------------------------
async def get_stock_universe(exchange: str = "NSE") -> list[str]:
    """Return all known symbols for the given exchange.

    Returns
    -------
    list[str]
        Symbol list (bare tickers without exchange suffix).
    """
    if exchange.upper() in ("NSE", "BSE"):
        return NIFTY50_SYMBOLS + NIFTY500_ADDITIONAL
    return SP500_TOP100


# ---------------------------------------------------------------------------
# Commodities
# ---------------------------------------------------------------------------
async def fetch_commodity_prices() -> Dict[str, Any]:
    """Return current prices for major commodities.

    Returns
    -------
    dict
        ``{commodity_name: {price, change, change_pct, unit}}``
    """
    commodity_map = {
        "gold": ("GC=F", "USD/oz"),
        "silver": ("SI=F", "USD/oz"),
        "crude_oil": ("CL=F", "USD/bbl"),
        "natural_gas": ("NG=F", "USD/MMBtu"),
        "copper": ("HG=F", "USD/lb"),
    }
    results: Dict[str, Any] = {}
    loop = asyncio.get_event_loop()

    async def _fetch_commodity(name: str, sym: str, unit: str) -> None:
        try:
            import yfinance as yf  # type: ignore[import]
            _yf_rate_check()
            ticker = yf.Ticker(sym)
            info = await loop.run_in_executor(None, lambda: ticker.fast_info)
            price = safe_float(getattr(info, "last_price", 0))
            prev = safe_float(getattr(info, "regular_market_previous_close", 0))
            change = price - prev
            change_pct = (change / prev * 100) if prev else 0.0
            results[name] = {"price": price, "change": change, "change_pct": change_pct, "unit": unit}
        except Exception as exc:
            logger.warning("Commodity fetch failed", extra={"commodity": name, "error": str(exc)})
            results[name] = {"price": 0, "change": 0, "change_pct": 0, "unit": unit}

    await asyncio.gather(*[_fetch_commodity(n, s, u) for n, (s, u) in commodity_map.items()])
    return results


# ---------------------------------------------------------------------------
# Symbol constants
# ---------------------------------------------------------------------------
NIFTY50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "SBIN",
    "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "AXISBANK", "BAJFINANCE", "ASIANPAINT",
    "MARUTI", "SUNPHARMA", "TITAN", "NESTLEIND", "ULTRACEMCO", "WIPRO",
    "HCLTECH", "ONGC", "POWERGRID", "NTPC", "TATASTEEL", "JSWSTEEL",
    "HINDALCO", "TATAMOTORS", "M&M", "BAJAJFINSV", "ADANIPORTS", "COALINDIA",
    "INDUSINDBK", "CIPLA", "DRREDDY", "DIVISLAB", "GRASIM", "BPCL", "TECHM",
    "EICHERMOT", "HEROMOTOCO", "BRITANNIA", "TATACONSUM", "APOLLOHOSP",
    "BAJAJ-AUTO", "SBILIFE", "HDFCLIFE", "UPL", "ADANIENT", "LTIM",
]

NIFTY500_ADDITIONAL = [
    "PIDILITIND", "BERGEPAINT", "MCDOWELL-N", "GODREJCP", "COLPAL", "MARICO",
    "DABUR", "EMAMILTD", "JYOTHYLAB", "VIPIND", "PAGEIND", "KAJARIACER",
    "POLYCAB", "HAVELLS", "VOLTAS", "BLUESTAR", "WHIRLPOOL", "CROMPTON",
    "DIXON", "AMBER", "SYMPHONY", "BATAINDIA", "RELAXO", "VGUARD",
    "APLAPOLLO", "ASTRAL", "SUPREME", "FINOLEX", "KPRMILL", "TRIDENT",
]

SP500_TOP100 = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "BRK-B", "NVDA", "JPM", "V",
    "UNH", "XOM", "MA", "JNJ", "PG", "HD", "LLY", "ABBV", "MRK", "PEP",
    "AVGO", "KO", "BAC", "COST", "MCD", "CSCO", "ADBE", "WMT", "CRM",
    "ACN", "NFLX", "ABT", "TMO", "LIN", "DHR", "VZ", "CMCSA", "INTC",
    "TXN", "NEE", "PM", "UPS", "BMY", "RTX", "QCOM", "AMGN", "LOW",
    "INTU", "HON", "IBM", "GS", "CAT", "MDT", "SBUX", "SPGI", "CVS",
    "BLK", "PLD", "DE", "AMT", "ISRG", "GE", "MMM", "GILD", "C",
    "MO", "ADP", "BKNG", "TJX", "CB", "MDLZ", "SO", "DUK", "CCI",
    "EL", "ATVI", "ZTS", "ITW", "D", "FIS", "BSX", "APD", "HUM",
    "SHW", "NOC", "ICE", "EMR", "AON", "FCX", "NSC", "MCO", "TGT",
    "GM", "F", "USB", "WM", "PNC", "ILMN", "AIG", "EQR", "KLAC",
]
