"""
Macroeconomic data fetcher for QuantMind Pro.
Sources: RBI (scraping), World Bank API, FRED (CSV), Polymarket API.
All macro data cached 6 hours. get_market_context() aggregates everything.
QuantMind Pro v3.0
"""

from __future__ import annotations

import asyncio
import csv
import io
from typing import Any, Dict, List, Optional

import aiohttp

from backend.utils.logger import get_logger
from backend.utils.retry import async_retry_with_backoff
from backend.utils.cache import async_sqlite_cache
from backend.utils.formatters import safe_float

logger = get_logger("macro_fetcher")

_CACHE_TTL = 21600  # 6 hours


# ---------------------------------------------------------------------------
# RBI data
# ---------------------------------------------------------------------------
@async_sqlite_cache(ttl_seconds=_CACHE_TTL, key_prefix="rbi")
@async_retry_with_backoff(max_retries=2, base_delay=3.0)
async def fetch_rbi_data() -> Dict[str, Any]:
    """Scrape RBI for latest monetary policy rates.

    Returns
    -------
    dict
        ``{"repo_rate", "reverse_repo", "crr", "slr", "inflation_cpi", "forex_reserves"}``
    """
    default = {
        "repo_rate": 6.5,
        "reverse_repo": 6.25,
        "crr": 4.0,
        "slr": 18.0,
        "inflation_cpi": 0.0,
        "forex_reserves_bn_usd": 0.0,
        "source": "rbi",
        "note": "Live scraping unavailable — using last-known values",
    }
    try:
        from bs4 import BeautifulSoup  # type: ignore[import]
        url = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return default
                html = await resp.text()
                soup = BeautifulSoup(html, "lxml")
                # Look for policy rate tables
                tables = soup.find_all("table")
                for table in tables:
                    text = table.get_text(" ", strip=True).lower()
                    if "repo" in text:
                        rows = table.find_all("tr")
                        for row in rows:
                            cells = [td.get_text(strip=True) for td in row.find_all("td")]
                            if len(cells) >= 2:
                                name = cells[0].lower()
                                if "repo rate" in name and "reverse" not in name:
                                    default["repo_rate"] = safe_float(cells[-1].replace("%", ""))
                                elif "reverse repo" in name:
                                    default["reverse_repo"] = safe_float(cells[-1].replace("%", ""))
                        break
                default["note"] = "scraped"
                return default
    except Exception as exc:
        logger.warning("RBI scrape failed", extra={"error": str(exc)})
        return default


# ---------------------------------------------------------------------------
# World Bank
# ---------------------------------------------------------------------------
@async_sqlite_cache(ttl_seconds=_CACHE_TTL, key_prefix="worldbank")
@async_retry_with_backoff(max_retries=2, base_delay=2.0)
async def fetch_world_bank_india() -> Dict[str, Any]:
    """Fetch key Indian macro indicators from the World Bank API.

    Returns
    -------
    dict
        ``{"gdp_growth", "fdi_inflows_bn_usd", "current_account_pct_gdp", ...}``
    """
    # Indicator codes
    indicators = {
        "gdp_growth": "NY.GDP.MKTP.KD.ZG",
        "fdi_inflows": "BX.KLT.DINV.CD.WD",
        "inflation": "FP.CPI.TOTL.ZG",
        "unemployment": "SL.UEM.TOTL.ZS",
    }
    results: Dict[str, Any] = {"source": "world_bank", "country": "India"}

    async def _fetch_indicator(key: str, code: str) -> None:
        url = f"https://api.worldbank.org/v2/country/IN/indicator/{code}?format=json&mrv=1"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        results[key] = None
                        return
                    data = await resp.json(content_type=None)
                    if len(data) >= 2 and data[1]:
                        entry = data[1][0]
                        results[key] = {
                            "value": safe_float(entry.get("value")),
                            "date": entry.get("date", ""),
                        }
                    else:
                        results[key] = None
        except Exception as exc:
            logger.debug("World Bank indicator failed", extra={"indicator": code, "error": str(exc)})
            results[key] = None

    await asyncio.gather(*[_fetch_indicator(k, v) for k, v in indicators.items()])
    return results


# ---------------------------------------------------------------------------
# FRED (Federal Reserve Economic Data)
# ---------------------------------------------------------------------------
@async_sqlite_cache(ttl_seconds=_CACHE_TTL, key_prefix="fred")
@async_retry_with_backoff(max_retries=2, base_delay=2.0)
async def fetch_fred_data(series_ids: Optional[list[str]] = None) -> Dict[str, Any]:
    """Fetch economic series from FRED via their CSV endpoint.

    Parameters
    ----------
    series_ids:
        List of FRED series IDs (default: Fed Funds Rate, Unemployment, CPI).

    Returns
    -------
    dict
        ``{series_id: {"value", "date", "unit"}}``
    """
    if series_ids is None:
        series_ids = ["DFF", "UNRATE", "CPIAUCSL", "T10Y2Y", "DEXINUS"]

    series_meta = {
        "DFF": "Fed Funds Rate (%)",
        "UNRATE": "US Unemployment (%)",
        "CPIAUCSL": "US CPI (index)",
        "T10Y2Y": "10Y-2Y Yield Spread",
        "DEXINUS": "USD/INR Exchange Rate",
    }

    results: Dict[str, Any] = {}

    async def _fetch_series(sid: str) -> None:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        results[sid] = None
                        return
                    text = await resp.text()
                    reader = csv.reader(io.StringIO(text))
                    rows = list(reader)
                    if len(rows) >= 2:
                        last_row = rows[-1]
                        results[sid] = {
                            "value": safe_float(last_row[1]) if len(last_row) > 1 else None,
                            "date": last_row[0] if last_row else "",
                            "unit": series_meta.get(sid, sid),
                        }
        except Exception as exc:
            logger.debug("FRED series failed", extra={"series": sid, "error": str(exc)})
            results[sid] = None

    await asyncio.gather(*[_fetch_series(sid) for sid in series_ids])
    return results


# ---------------------------------------------------------------------------
# Polymarket
# ---------------------------------------------------------------------------
@async_sqlite_cache(ttl_seconds=_CACHE_TTL, key_prefix="polymarket")
@async_retry_with_backoff(max_retries=2, base_delay=2.0)
async def get_polymarket_odds(market_slugs: Optional[list[str]] = None) -> Dict[str, Any]:
    """Fetch prediction market odds from Polymarket.

    Parameters
    ----------
    market_slugs:
        Optional list of market slugs to filter. Returns all active markets if ``None``.

    Returns
    -------
    dict
        ``{market_question: {"yes_price", "probability", "volume"}}``
    """
    url = "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=20"
    results: Dict[str, Any] = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return results
                markets = await resp.json(content_type=None)
                for market in markets:
                    question = market.get("question", "")
                    slug = market.get("slug", "")
                    if market_slugs and slug not in market_slugs:
                        continue
                    # Filter for India/oil/USD-relevant markets
                    keywords = ["india", "oil", "usd", "inr", "crude", "rupee", "fed", "rbi"]
                    if not any(kw in question.lower() for kw in keywords):
                        continue
                    outcomes = market.get("outcomes", [])
                    yes_price = 0.5
                    for outcome in outcomes:
                        if outcome.get("title", "").lower() == "yes":
                            yes_price = safe_float(outcome.get("price", 0.5))
                    results[question] = {
                        "yes_price": yes_price,
                        "probability": yes_price,
                        "volume": safe_float(market.get("volume", 0)),
                        "slug": slug,
                    }
    except Exception as exc:
        logger.warning("Polymarket fetch failed", extra={"error": str(exc)})
    return results


# ---------------------------------------------------------------------------
# Aggregated market context
# ---------------------------------------------------------------------------
async def get_market_context() -> Dict[str, Any]:
    """Aggregate all macro data into a single context dict.

    Returns
    -------
    dict
        Combined macro data from RBI, World Bank, FRED, and Polymarket.
    """
    rbi_task = fetch_rbi_data()
    wb_task = fetch_world_bank_india()
    fred_task = fetch_fred_data()
    poly_task = get_polymarket_odds()

    results = await asyncio.gather(rbi_task, wb_task, fred_task, poly_task, return_exceptions=True)

    rbi_data = results[0] if not isinstance(results[0], Exception) else {}
    wb_data = results[1] if not isinstance(results[1], Exception) else {}
    fred_data = results[2] if not isinstance(results[2], Exception) else {}
    poly_data = results[3] if not isinstance(results[3], Exception) else {}

    # Extract key values for quick access
    usd_inr = safe_float((fred_data.get("DEXINUS") or {}).get("value", 83.0))
    fed_rate = safe_float((fred_data.get("DFF") or {}).get("value", 5.25))
    us_cpi = safe_float((fred_data.get("CPIAUCSL") or {}).get("value", 0))
    yield_spread = safe_float((fred_data.get("T10Y2Y") or {}).get("value", 0))
    india_gdp = safe_float((wb_data.get("gdp_growth") or {}).get("value", 0))

    return {
        "rbi": rbi_data,
        "world_bank": wb_data,
        "fred": fred_data,
        "polymarket": poly_data,
        "summary": {
            "repo_rate": rbi_data.get("repo_rate", 6.5),
            "usd_inr": usd_inr,
            "fed_rate": fed_rate,
            "us_cpi": us_cpi,
            "yield_spread": yield_spread,
            "india_gdp_growth": india_gdp,
        },
    }
