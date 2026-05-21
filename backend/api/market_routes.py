from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Query, Request, Depends

from backend.core.limiter import limiter
from backend.core.security import verify_access_unlocked

router = APIRouter(prefix="/market", tags=["market"])

_MARKET_UNIVERSE = [
    {"symbol": "RELIANCE", "name": "Reliance Industries", "type": "Equity", "region": "India"},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "type": "Equity", "region": "India"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank", "type": "Equity", "region": "India"},
    {"symbol": "INFY", "name": "Infosys", "type": "Equity", "region": "India"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank", "type": "Equity", "region": "India"},
    {"symbol": "AAPL", "name": "Apple Inc.", "type": "Equity", "region": "USA"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "type": "Equity", "region": "USA"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "type": "Equity", "region": "USA"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "type": "Equity", "region": "USA"},
]


def _fallback_candles(symbol: str, days: int = 120) -> List[Dict[str, Any]]:
    seed = sum(ord(ch) for ch in symbol.upper())
    base = 80 + (seed % 180)
    today = date.today()
    candles: List[Dict[str, Any]] = []
    close = float(base)

    for index in range(days):
        current_day = today - timedelta(days=days - index)
        if current_day.weekday() >= 5:
            continue
        wave = math.sin((index + seed) / 8) * 1.8
        drift = (index / days) * ((seed % 17) - 7) * 0.08
        open_price = close
        close = max(1, open_price + wave + drift)
        high = max(open_price, close) + 1.4 + (index % 5) * 0.18
        low = min(open_price, close) - 1.2 - (index % 3) * 0.15
        candles.append(
            {
                "time": current_day.isoformat(),
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(max(0.1, low), 2),
                "close": round(close, 2),
                "volume": int(800_000 + (seed % 1000) * 1200 + index * 4500),
            }
        )
    return candles


@router.get("/summary")
@limiter.limit("60/minute")
async def get_market_summary(request: Request, current_user: dict = Depends(verify_access_unlocked)):
    return {"indices": {"NIFTY50": 22000, "SENSEX": 73000, "NASDAQ": 17800}}


@router.get("/movers")
@limiter.limit("60/minute")
async def get_top_movers(request: Request, current_user: dict = Depends(verify_access_unlocked)):
    return {"gainers": _MARKET_UNIVERSE[:3], "losers": _MARKET_UNIVERSE[-2:]}


@router.get("/news")
@limiter.limit("60/minute")
async def get_market_news(request: Request, current_user: dict = Depends(verify_access_unlocked)):
    try:
        from backend.data.news_fetcher import fetch_market_news

        return {"articles": await fetch_market_news(limit=20)}
    except Exception:
        return {"articles": []}


@router.get("/search")
@limiter.limit("60/minute")
async def search_stocks(
    request: Request,
    query: str = Query(..., min_length=1, max_length=64),
    current_user: dict = Depends(verify_access_unlocked),
):
    normalized = query.strip().lower()
    results = [
        row
        for row in _MARKET_UNIVERSE
        if normalized in row["symbol"].lower() or normalized in row["name"].lower()
    ]

    if len(results) < 5:
        try:
            import yfinance as yf

            search = yf.Search(query, max_results=8)
            quotes = getattr(search, "quotes", []) or []
            for quote in quotes:
                symbol = quote.get("symbol")
                name = quote.get("shortname") or quote.get("longname") or symbol
                if symbol and all(item["symbol"] != symbol for item in results):
                    results.append(
                        {
                            "symbol": symbol,
                            "name": name,
                            "type": quote.get("quoteType", "Equity"),
                            "region": quote.get("exchange", "Global"),
                        }
                    )
        except Exception:
            pass

    return {"results": results[:8]}


@router.get("/candles")
@limiter.limit("60/minute")
async def get_market_candles(
    request: Request,
    symbol: str = Query("AAPL", min_length=1, max_length=24),
    period: str = Query("6mo", max_length=12),
    interval: str = Query("1d", max_length=8),
    current_user: dict = Depends(verify_access_unlocked),
):
    normalized_symbol = symbol.upper().strip()
    yahoo_symbol = f"{normalized_symbol}.NS" if normalized_symbol in {"RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"} else normalized_symbol

    try:
        import yfinance as yf

        ticker = yf.Ticker(yahoo_symbol)
        frame = ticker.history(period=period, interval=interval, auto_adjust=False)
        if frame is not None and not frame.empty:
            candles = []
            for timestamp, row in frame.tail(180).iterrows():
                candles.append(
                    {
                        "time": timestamp.date().isoformat(),
                        "open": round(float(row["Open"]), 2),
                        "high": round(float(row["High"]), 2),
                        "low": round(float(row["Low"]), 2),
                        "close": round(float(row["Close"]), 2),
                        "volume": int(row.get("Volume", 0) or 0),
                    }
                )
            if candles:
                return {"symbol": normalized_symbol, "candles": candles}
    except Exception:
        pass

    return {"symbol": normalized_symbol, "candles": _fallback_candles(normalized_symbol)}
