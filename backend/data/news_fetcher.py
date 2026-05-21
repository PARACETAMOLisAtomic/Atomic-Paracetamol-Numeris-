"""
News fetcher for QuantMind Pro.
Sources: NewsAPI, Google News RSS, Moneycontrol RSS, GDELT, SEBI/BSE scraping.
Includes deduplication, relevance scoring, and AI summarisation.
QuantMind Pro v3.0
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import aiohttp

from backend.core.config import settings
from backend.utils.logger import get_logger
from backend.utils.retry import async_retry_with_backoff
from backend.utils.cache import async_sqlite_cache

logger = get_logger("news_fetcher")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
INDIA_KEYWORDS = [
    "india", "nse", "bse", "nifty", "sensex", "rbi", "sebi", "rupee",
    "inr", "reliance", "tata", "infosys", "hdfc", "icici", "wipro",
    "bajaj", "adani", "budget", "modi", "mumbai", "delhi",
]

RSS_FEEDS = {
    "google_news_india": "https://news.google.com/rss/search?q=india+stock+market&hl=en-IN&gl=IN&ceid=IN:en",
    "google_news_nifty": "https://news.google.com/rss/search?q=nifty+sensex+market&hl=en-IN",
    "moneycontrol": "https://www.moneycontrol.com/rss/latestnews.xml",
    "economic_times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "livemint_markets": "https://www.livemint.com/rss/markets",
}


# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------
def _relevance_score(title: str, description: str = "") -> float:
    """Return a 0-1 relevance score for Indian market content."""
    text = (title + " " + description).lower()
    hits = sum(1 for kw in INDIA_KEYWORDS if kw in text)
    return min(1.0, hits / 3)


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------
def _deduplicate(articles: list[Dict[str, Any]], threshold: float = 0.85) -> list[Dict[str, Any]]:
    """Remove near-duplicate articles using title similarity."""
    seen: list[str] = []
    unique: list[Dict[str, Any]] = []
    for art in articles:
        title = art.get("title", "")
        is_dup = any(SequenceMatcher(None, title, s).ratio() > threshold for s in seen)
        if not is_dup:
            seen.append(title)
            unique.append(art)
    return unique


# ---------------------------------------------------------------------------
# NewsAPI
# ---------------------------------------------------------------------------
@async_sqlite_cache(ttl_seconds=3600, key_prefix="newsapi")
@async_retry_with_backoff(max_retries=2, base_delay=2.0)
async def _fetch_newsapi(query: str, limit: int = 20) -> list[Dict[str, Any]]:
    if not settings.NEWS_API_KEY:
        return []
    url = (
        f"https://newsapi.org/v2/everything"
        f"?q={quote_plus(query)}&language=en&sortBy=publishedAt"
        f"&pageSize={limit}&apiKey={settings.NEWS_API_KEY}"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    logger.warning("NewsAPI non-200", extra={"status": resp.status})
                    return []
                data = await resp.json()
                articles = []
                for a in data.get("articles", []):
                    articles.append({
                        "title": a.get("title", ""),
                        "source": a.get("source", {}).get("name", "NewsAPI"),
                        "url": a.get("url", ""),
                        "published_at": a.get("publishedAt", ""),
                        "summary": a.get("description", ""),
                        "relevance_score": _relevance_score(a.get("title", ""), a.get("description", "")),
                    })
                return articles
    except Exception as exc:
        logger.warning("NewsAPI fetch failed", extra={"error": str(exc)})
        return []


# ---------------------------------------------------------------------------
# RSS feeds
# ---------------------------------------------------------------------------
@async_retry_with_backoff(max_retries=2, base_delay=1.0)
async def _fetch_rss(feed_name: str, url: str, limit: int = 20) -> list[Dict[str, Any]]:
    try:
        import feedparser  # type: ignore[import]
    except ImportError:
        # feedparser not installed — use aiohttp raw
        return await _fetch_rss_raw(url, limit)

    loop = asyncio.get_event_loop()
    try:
        feed = await loop.run_in_executor(None, lambda: feedparser.parse(url))
        articles = []
        for entry in feed.entries[:limit]:
            title = getattr(entry, "title", "")
            link = getattr(entry, "link", "")
            summary = getattr(entry, "summary", "")
            published = getattr(entry, "published", "")
            articles.append({
                "title": title,
                "source": feed_name,
                "url": link,
                "published_at": published,
                "summary": summary[:300],
                "relevance_score": _relevance_score(title, summary),
            })
        return articles
    except Exception as exc:
        logger.warning("RSS parse failed", extra={"feed": feed_name, "error": str(exc)})
        return []


async def _fetch_rss_raw(url: str, limit: int = 20) -> list[Dict[str, Any]]:
    """Minimal RSS parser using aiohttp + basic XML parsing."""
    try:
        import xml.etree.ElementTree as ET  # noqa: N813
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                text = await resp.text()
                root = ET.fromstring(text)
                articles = []
                for item in root.iter("item"):
                    title = item.findtext("title", "")
                    link = item.findtext("link", "")
                    desc = item.findtext("description", "")
                    pub = item.findtext("pubDate", "")
                    articles.append({
                        "title": title,
                        "source": "rss",
                        "url": link,
                        "published_at": pub,
                        "summary": desc[:300],
                        "relevance_score": _relevance_score(title, desc),
                    })
                    if len(articles) >= limit:
                        break
                return articles
    except Exception as exc:
        logger.warning("RSS raw fetch failed", extra={"url": url, "error": str(exc)})
        return []


# ---------------------------------------------------------------------------
# GDELT
# ---------------------------------------------------------------------------
@async_sqlite_cache(ttl_seconds=3600, key_prefix="gdelt")
@async_retry_with_backoff(max_retries=2, base_delay=2.0)
async def fetch_gdelt_events(country_code: str = "IN", days: int = 7) -> list[Dict[str, Any]]:
    """Fetch GDELT geopolitical events for a country.

    Parameters
    ----------
    country_code:
        ISO-3166 alpha-2 country code (default ``"IN"``).
    days:
        Lookback window in days.

    Returns
    -------
    list[dict]
        Events with ``goldstein_scale`` impact score.
    """
    query = f"india economy market trade+{country_code}"
    url = (
        f"https://api.gdeltproject.org/api/v2/doc/doc"
        f"?query={quote_plus(query)}&mode=artlist&maxrecords=25"
        f"&format=json&timespan={days}d"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json(content_type=None)
                events = []
                for art in data.get("articles", []):
                    events.append({
                        "title": art.get("title", ""),
                        "url": art.get("url", ""),
                        "source": art.get("domain", "GDELT"),
                        "published_at": art.get("seendate", ""),
                        "goldstein_scale": float(art.get("tone", 0.0)),
                        "country": country_code,
                        "relevance_score": _relevance_score(art.get("title", "")),
                    })
                return events
    except Exception as exc:
        logger.warning("GDELT fetch failed", extra={"error": str(exc)})
        return []


# ---------------------------------------------------------------------------
# SEBI / BSE insider trading disclosures
# ---------------------------------------------------------------------------
@async_sqlite_cache(ttl_seconds=86400, key_prefix="sebi")
async def fetch_sebi_disclosures(symbol: str) -> list[Dict[str, Any]]:
    """Scrape BSE for insider trading disclosures for a symbol.

    Parameters
    ----------
    symbol:
        NSE ticker symbol (bare, no suffix).

    Returns
    -------
    list[dict]
        Recent insider trading disclosures.
    """
    try:
        from bs4 import BeautifulSoup  # type: ignore[import]
        url = f"https://www.bseindia.com/corporates/Insider_Trading.aspx?scripcode=&scrip_name={symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession(headers=headers) as session:
            await asyncio.sleep(2)  # Polite delay
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
                soup = BeautifulSoup(html, "lxml")
                rows = soup.select("table tr")[1:20]  # skip header
                disclosures = []
                for row in rows:
                    cells = [td.get_text(strip=True) for td in row.find_all("td")]
                    if len(cells) >= 4:
                        disclosures.append({
                            "date": cells[0],
                            "name": cells[1],
                            "transaction": cells[2],
                            "shares": cells[3],
                            "symbol": symbol,
                        })
                return disclosures
    except Exception as exc:
        logger.warning("SEBI disclosure scrape failed", extra={"symbol": symbol, "error": str(exc)})
        return []


# ---------------------------------------------------------------------------
# AI summarisation (optional — 1-line summary via Groq)
# ---------------------------------------------------------------------------
async def summarize_news(articles: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """Add a 1-line AI summary to each article using the model router.

    Parameters
    ----------
    articles:
        List of article dicts (must have ``"title"`` and ``"summary"`` fields).

    Returns
    -------
    list[dict]
        Same articles with ``"ai_summary"`` field added.
    """
    try:
        from backend.core.model_router import get_model_router
        router = get_model_router()
        for article in articles[:10]:  # limit to 10 to avoid API overuse
            try:
                prompt = (
                    f"Summarize this financial news in exactly one sentence (max 20 words):\n"
                    f"Title: {article.get('title', '')}\n"
                    f"Content: {article.get('summary', '')}"
                )
                summary = await router.route("chat", prompt, max_tokens=50)
                article["ai_summary"] = summary.strip()
            except Exception:
                article["ai_summary"] = article.get("summary", "")[:100]
    except Exception as exc:
        logger.debug("AI summarisation skipped", extra={"error": str(exc)})
        for a in articles:
            a.setdefault("ai_summary", a.get("summary", "")[:100])
    return articles


# ---------------------------------------------------------------------------
# Main aggregator
# ---------------------------------------------------------------------------
async def fetch_market_news(
    topics: Optional[list[str]] = None,
    limit: int = 50,
    add_ai_summary: bool = False,
) -> list[Dict[str, Any]]:
    """Aggregate news from all sources.

    Parameters
    ----------
    topics:
        List of search topics (default: ``["india stock market", "nifty"]``).
    limit:
        Maximum articles to return after deduplication.
    add_ai_summary:
        Whether to add AI-generated 1-line summaries (uses LLM calls).

    Returns
    -------
    list[dict]
        Deduplicated, sorted-by-recency news articles.
    """
    if topics is None:
        topics = ["india stock market", "nifty sensex"]

    all_articles: list[Dict[str, Any]] = []

    # NewsAPI (cached 1 hour)
    for topic in topics[:2]:
        arts = await _fetch_newsapi(topic, limit=20)
        all_articles.extend(arts)

    # RSS feeds (concurrent)
    rss_tasks = [_fetch_rss(name, url, limit=15) for name, url in RSS_FEEDS.items()]
    rss_results = await asyncio.gather(*rss_tasks, return_exceptions=True)
    for res in rss_results:
        if isinstance(res, list):
            all_articles.extend(res)

    # GDELT
    gdelt = await fetch_gdelt_events("IN", days=3)
    all_articles.extend(gdelt)

    # Dedup + sort
    unique = _deduplicate(all_articles)
    unique.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    result = unique[:limit]

    if add_ai_summary:
        result = await summarize_news(result)

    return result
