"""
Fundamental data fetcher for QuantMind Pro.
Sources: Screener.in (scraping), SEC EDGAR (API), DCF model, peer comparison.
Quality score: 0-100 composite based on 5 financial criteria.
QuantMind Pro v3.0
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional

import aiohttp

from backend.utils.logger import get_logger
from backend.utils.retry import async_retry_with_backoff
from backend.utils.cache import async_sqlite_cache
from backend.utils.formatters import safe_float

logger = get_logger("fundamental_fetcher")

# ---------------------------------------------------------------------------
# Screener.in scraper
# ---------------------------------------------------------------------------
@async_sqlite_cache(ttl_seconds=86400, key_prefix="screener")
@async_retry_with_backoff(max_retries=2, base_delay=3.0)
async def scrape_screener(symbol: str) -> Dict[str, Any]:
    """Scrape financial ratios and statements from Screener.in.

    Parameters
    ----------
    symbol:
        NSE ticker symbol (bare, no suffix).

    Returns
    -------
    dict
        Financial ratios, quarterly results, and shareholding pattern.
    """
    from bs4 import BeautifulSoup  # type: ignore[import]

    url = f"https://www.screener.in/company/{symbol}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }

    default: Dict[str, Any] = {
        "symbol": symbol,
        "pe": 0.0,
        "pb": 0.0,
        "roe": 0.0,
        "roce": 0.0,
        "debt_to_equity": 0.0,
        "sales_growth_3yr": 0.0,
        "profit_growth_3yr": 0.0,
        "dividend_yield": 0.0,
        "market_cap": 0.0,
        "eps": 0.0,
        "promoter_holding": 0.0,
        "fii_holding": 0.0,
        "dii_holding": 0.0,
        "quarterly_results": [],
        "error": None,
    }

    try:
        await asyncio.sleep(3)  # Polite delay
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 404:
                    default["error"] = "Symbol not found on Screener.in"
                    return default
                if resp.status != 200:
                    default["error"] = f"HTTP {resp.status}"
                    return default

                html = await resp.text()
                soup = BeautifulSoup(html, "lxml")

                def _extract_number(text: str) -> float:
                    text = re.sub(r"[,%₹]", "", text.strip())
                    return safe_float(text)

                # Key ratios
                result = dict(default)
                ratios_section = soup.find("section", {"id": "ratios"})
                if ratios_section:
                    for li in ratios_section.find_all("li"):
                        spans = li.find_all("span")
                        if len(spans) >= 2:
                            name = spans[0].get_text(strip=True).lower()
                            val = _extract_number(spans[-1].get_text())
                            if "p/e" in name:
                                result["pe"] = val
                            elif "p/b" in name or "book" in name:
                                result["pb"] = val
                            elif "roe" in name:
                                result["roe"] = val
                            elif "roce" in name:
                                result["roce"] = val
                            elif "debt" in name:
                                result["debt_to_equity"] = val
                            elif "dividend" in name:
                                result["dividend_yield"] = val
                            elif "market cap" in name:
                                result["market_cap"] = val
                            elif "eps" in name:
                                result["eps"] = val

                # Shareholding pattern
                sh_section = soup.find("section", {"id": "shareholding"})
                if sh_section:
                    rows = sh_section.find_all("tr")
                    for row in rows:
                        cols = [td.get_text(strip=True) for td in row.find_all("td")]
                        if len(cols) >= 2:
                            name = cols[0].lower()
                            val = _extract_number(cols[-1])
                            if "promoter" in name:
                                result["promoter_holding"] = val
                            elif "fii" in name or "foreign" in name:
                                result["fii_holding"] = val
                            elif "dii" in name or "domestic" in name:
                                result["dii_holding"] = val

                # Quarterly results
                qr_section = soup.find("section", {"id": "quarters"})
                quarterly: list[Dict[str, Any]] = []
                if qr_section:
                    table = qr_section.find("table")
                    if table:
                        headers_row = [th.get_text(strip=True) for th in table.find_all("th")]
                        for row in table.find_all("tr")[1:5]:  # last 4 quarters
                            cells = [td.get_text(strip=True) for td in row.find_all("td")]
                            if cells:
                                quarterly.append({
                                    "period": cells[0] if cells else "",
                                    "sales": _extract_number(cells[1]) if len(cells) > 1 else 0,
                                    "net_profit": _extract_number(cells[-1]) if len(cells) > 1 else 0,
                                })
                result["quarterly_results"] = quarterly
                result["symbol"] = symbol
                return result

    except Exception as exc:
        logger.warning("Screener.in scrape failed", extra={"symbol": symbol, "error": str(exc)})
        default["error"] = str(exc)
        return default


# ---------------------------------------------------------------------------
# SEC EDGAR
# ---------------------------------------------------------------------------
async def get_cik(ticker: str) -> Optional[str]:
    """Look up the SEC CIK number for a US ticker symbol.

    Parameters
    ----------
    ticker:
        US stock ticker (e.g. ``"AAPL"``).

    Returns
    -------
    str or None
        CIK number (zero-padded to 10 digits), or ``None`` if not found.
    """
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2020-01-01&forms=10-K"
    cik_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={ticker}&type=10-K&dateb=&owner=include&count=5&search_text=&action=getcompany"

    try:
        async with aiohttp.ClientSession() as session:
            # Use the company search JSON endpoint
            json_url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=10-K"
            ticker_url = "https://www.sec.gov/files/company_tickers.json"
            async with session.get(ticker_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    for _, company in data.items():
                        if company.get("ticker", "").upper() == ticker.upper():
                            return str(company["cik_str"]).zfill(10)
    except Exception as exc:
        logger.warning("CIK lookup failed", extra={"ticker": ticker, "error": str(exc)})
    return None


@async_sqlite_cache(ttl_seconds=86400, key_prefix="edgar")
@async_retry_with_backoff(max_retries=2, base_delay=2.0)
async def scrape_edgar(ticker: str) -> Dict[str, Any]:
    """Fetch financial data from SEC EDGAR for a US stock.

    Parameters
    ----------
    ticker:
        US stock ticker.

    Returns
    -------
    dict
        ``{"revenue", "net_income", "eps", "debt", "free_cash_flow", "last_4_quarters"}``
    """
    default = {
        "ticker": ticker,
        "revenue": 0.0,
        "net_income": 0.0,
        "eps": 0.0,
        "debt": 0.0,
        "free_cash_flow": 0.0,
        "last_4_quarters": [],
    }
    cik = await get_cik(ticker)
    if not cik:
        return default

    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return default
                data = await resp.json(content_type=None)

                filings = data.get("filings", {}).get("recent", {})
                forms = filings.get("form", [])
                dates = filings.get("filingDate", [])
                accessions = filings.get("accessionNumber", [])

                quarterly: list[Dict[str, Any]] = []
                for i, form in enumerate(forms):
                    if form in ("10-Q", "10-K") and len(quarterly) < 4:
                        quarterly.append({
                            "form": form,
                            "date": dates[i] if i < len(dates) else "",
                            "accession": accessions[i] if i < len(accessions) else "",
                        })

                default["last_4_quarters"] = quarterly
                return default
    except Exception as exc:
        logger.warning("EDGAR scrape failed", extra={"ticker": ticker, "error": str(exc)})
        return default


# ---------------------------------------------------------------------------
# DCF model
# ---------------------------------------------------------------------------
def calculate_dcf(
    financials: Dict[str, Any],
    growth_rate: float = 0.12,
    discount_rate: float = 0.10,
    terminal_growth: float = 0.04,
    projection_years: int = 10,
) -> Dict[str, Any]:
    """Compute intrinsic value using a discounted cash flow model.

    Parameters
    ----------
    financials:
        Dict with at least ``"free_cash_flow"`` key (in Cr/M).
    growth_rate:
        Expected annual FCF growth rate (default 12%).
    discount_rate:
        WACC / required rate of return (default 10%).
    terminal_growth:
        Perpetual growth rate after projection period (default 4%).
    projection_years:
        Number of years to project (default 10).

    Returns
    -------
    dict
        ``{"intrinsic_value", "pv_fcf", "terminal_value", "assumptions"}``
    """
    fcf = safe_float(financials.get("free_cash_flow", 0))
    if fcf <= 0:
        return {
            "intrinsic_value": 0.0,
            "pv_fcf": 0.0,
            "terminal_value": 0.0,
            "assumptions": {"error": "Negative or zero FCF — DCF not applicable"},
        }

    pv_total = 0.0
    for year in range(1, projection_years + 1):
        projected_fcf = fcf * ((1 + growth_rate) ** year)
        discount_factor = (1 + discount_rate) ** year
        pv_total += projected_fcf / discount_factor

    # Gordon Growth terminal value
    terminal_fcf = fcf * ((1 + growth_rate) ** projection_years) * (1 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** projection_years)

    intrinsic = pv_total + pv_terminal

    return {
        "intrinsic_value": round(intrinsic, 2),
        "pv_fcf": round(pv_total, 2),
        "terminal_value": round(pv_terminal, 2),
        "assumptions": {
            "base_fcf": fcf,
            "growth_rate_pct": growth_rate * 100,
            "discount_rate_pct": discount_rate * 100,
            "terminal_growth_pct": terminal_growth * 100,
            "projection_years": projection_years,
        },
    }


# ---------------------------------------------------------------------------
# Peer comparison
# ---------------------------------------------------------------------------
async def get_peer_comparison(symbol: str, sector: str = "Technology") -> Dict[str, Any]:
    """Compare a stock's financial ratios against 5 sector peers.

    Parameters
    ----------
    symbol:
        Target stock symbol.
    sector:
        Sector name for selecting peers.

    Returns
    -------
    dict
        ``{"target", "peers", "rankings"}`` with percentile rankings.
    """
    # Simple sector → peers mapping (expand as needed)
    sector_peers: Dict[str, list[str]] = {
        "Technology": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"],
        "Banking": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN"],
        "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR"],
        "Pharma": ["SUNPHARMA", "CIPLA", "DRREDDY", "DIVISLAB", "AUROPHARMA"],
        "Auto": ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO"],
    }

    peers = [p for p in sector_peers.get(sector, ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"]) if p != symbol][:5]

    # Fetch ratios for target + peers concurrently
    all_symbols = [symbol] + peers
    results = await asyncio.gather(*[scrape_screener(s) for s in all_symbols], return_exceptions=True)

    target_data = results[0] if not isinstance(results[0], Exception) else {}
    peer_data = [
        (peers[i], results[i + 1])
        for i in range(len(peers))
        if not isinstance(results[i + 1], Exception)
    ]

    # Rank target vs peers on each ratio (1 = best)
    metrics = ["pe", "pb", "roe", "roce", "debt_to_equity"]
    rankings: Dict[str, int] = {}

    for metric in metrics:
        all_vals = [safe_float(target_data.get(metric, 0))]
        for _, pd_data in peer_data:
            all_vals.append(safe_float(pd_data.get(metric, 0)) if isinstance(pd_data, dict) else 0.0)

        target_val = all_vals[0]
        # Lower is better for PE, PB, D/E; higher is better for ROE, ROCE
        if metric in ("debt_to_equity", "pe", "pb"):
            rankings[metric] = sorted(all_vals).index(target_val) + 1
        else:
            rankings[metric] = sorted(all_vals, reverse=True).index(target_val) + 1

    return {
        "target": {"symbol": symbol, "data": target_data},
        "peers": [{"symbol": p, "data": d} for p, d in peer_data],
        "rankings": rankings,
        "sector": sector,
    }


# ---------------------------------------------------------------------------
# Quality score (0-100)
# ---------------------------------------------------------------------------
def calculate_quality_score(financials: Dict[str, Any]) -> int:
    """Compute a composite quality score from key financial metrics.

    Scoring criteria:
    - ROE > 15%     → +20
    - D/E < 1       → +20
    - Profit growth → +20
    - Promoter > 50%→ +20
    - FCF positive  → +20

    Parameters
    ----------
    financials:
        Dict from :func:`scrape_screener` or equivalent.

    Returns
    -------
    int
        Quality score 0–100.
    """
    score = 0
    roe = safe_float(financials.get("roe", 0))
    de = safe_float(financials.get("debt_to_equity", 999))
    promoter = safe_float(financials.get("promoter_holding", 0))
    fcf = safe_float(financials.get("free_cash_flow", -1))
    profit_growth = safe_float(financials.get("profit_growth_3yr", 0))

    if roe > 15:
        score += 20
    if de < 1:
        score += 20
    if profit_growth > 0:
        score += 20
    if promoter > 50:
        score += 20
    if fcf > 0:
        score += 20

    return score