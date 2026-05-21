"""
Sentiment fetcher for QuantMind Pro.
Sources: Mirofish (Playwright scrape), StockTwits, Reddit PRAW, Google Trends.
Scoring: VADER + TextBlob composite. Anomaly detection on 24h change.
QuantMind Pro v3.0
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from backend.core.config import settings
from backend.utils.logger import get_logger
from backend.utils.retry import async_retry_with_backoff
from backend.utils.cache import async_sqlite_cache

logger = get_logger("sentiment_fetcher")


# ---------------------------------------------------------------------------
# VADER + TextBlob scoring helpers
# ---------------------------------------------------------------------------
def _vader_score(text: str) -> float:
    """Return VADER compound score (–1 to +1) → mapped to 0–100."""
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore[import]
        sid = SentimentIntensityAnalyzer()
        compound = sid.polarity_scores(text)["compound"]
        return (compound + 1) / 2 * 100  # map –1..+1 → 0..100
    except Exception:
        return 50.0


def _textblob_score(text: str) -> float:
    """Return TextBlob polarity (–1 to +1) → mapped to 0–100."""
    try:
        from textblob import TextBlob  # type: ignore[import]
        polarity = TextBlob(text).sentiment.polarity
        return (polarity + 1) / 2 * 100
    except Exception:
        return 50.0


def _composite_score(texts: list[str]) -> float:
    """Average VADER and TextBlob across multiple texts."""
    if not texts:
        return 50.0
    scores = [(_vader_score(t) + _textblob_score(t)) / 2 for t in texts]
    return sum(scores) / len(scores)


# ---------------------------------------------------------------------------
# Mirofish (Playwright scraping — primary, optional)
# ---------------------------------------------------------------------------
@async_sqlite_cache(ttl_seconds=3600, key_prefix="mirofish")
async def fetch_mirofish_sentiment(topic: str) -> Optional[Dict[str, Any]]:
    """Scrape Mirofish for sentiment on a topic.

    Attempts Playwright headless Chrome scraping.
    Returns ``None`` if blocked or unavailable (triggers fallback pipeline).

    Parameters
    ----------
    topic:
        Stock symbol or topic keyword to search for.

    Returns
    -------
    dict or None
        ``{"sentiment_score", "trending_narratives", "key_themes"}`` or ``None``.
    """
    try:
        from playwright.async_api import async_playwright, TimeoutError as PWTimeout  # type: ignore[import]

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(
                    f"https://mirofish.com/search?q={topic}",
                    timeout=10_000,
                    wait_until="domcontentloaded",
                )
                # Try to extract text content
                content = await page.inner_text("body")
                await browser.close()

                if not content or len(content) < 100:
                    return None

                score = _composite_score([content[:2000]])
                return {
                    "sentiment_score": score,
                    "trending_narratives": [content[:200]],
                    "key_themes": [],
                    "source": "mirofish",
                }
            except PWTimeout:
                await browser.close()
                return None
    except ImportError:
        logger.debug("Playwright not installed — Mirofish scraping disabled")
        return None
    except Exception as exc:
        logger.debug("Mirofish scrape failed", extra={"error": str(exc)})
        return None


# ---------------------------------------------------------------------------
# StockTwits
# ---------------------------------------------------------------------------
@async_sqlite_cache(ttl_seconds=1800, key_prefix="stocktwits")
@async_retry_with_backoff(max_retries=2, base_delay=1.0)
async def fetch_stocktwits_sentiment(symbol: str) -> Dict[str, Any]:
    """Fetch StockTwits public sentiment for a symbol.

    Parameters
    ----------
    symbol:
        Bare ticker (e.g. ``"RELIANCE"``).

    Returns
    -------
    dict
        ``{"bullish_ratio", "bearish_ratio", "message_volume_24h", "trending_score", "score"}``
    """
    import aiohttp
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
    default = {"bullish_ratio": 0.5, "bearish_ratio": 0.5, "message_volume_24h": 0,
                "trending_score": 0.0, "score": 50.0, "source": "stocktwits"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 404:
                    return default
                if resp.status != 200:
                    return default
                data = await resp.json()
                messages = data.get("messages", [])
                if not messages:
                    return default

                bullish = sum(1 for m in messages if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bullish")
                bearish = sum(1 for m in messages if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bearish")
                total = len(messages)

                bullish_ratio = bullish / total if total else 0.5
                bearish_ratio = bearish / total if total else 0.5
                score = bullish_ratio * 100

                texts = [m.get("body", "") for m in messages[:50]]
                nlp_score = _composite_score(texts)
                final_score = (score + nlp_score) / 2

                return {
                    "bullish_ratio": bullish_ratio,
                    "bearish_ratio": bearish_ratio,
                    "message_volume_24h": total,
                    "trending_score": min(100.0, total / 2),
                    "score": final_score,
                    "source": "stocktwits",
                }
    except Exception as exc:
        logger.warning("StockTwits fetch failed", extra={"symbol": symbol, "error": str(exc)})
        return default


# ---------------------------------------------------------------------------
# Reddit PRAW
# ---------------------------------------------------------------------------
@async_sqlite_cache(ttl_seconds=3600, key_prefix="reddit")
async def fetch_reddit_sentiment(
    subreddits: Optional[list[str]] = None,
    query: str = "market",
) -> Dict[str, Any]:
    """Fetch and score Reddit posts from financial subreddits.

    Parameters
    ----------
    subreddits:
        List of subreddit names (default: IndianStockMarket + IndiaInvestments).
    query:
        Search query string.

    Returns
    -------
    dict
        ``{"avg_sentiment", "post_count", "top_posts", "score", "source"}``
    """
    if subreddits is None:
        subreddits = ["IndianStockMarket", "IndiaInvestments", "wallstreetbets"]

    default = {"avg_sentiment": 50.0, "post_count": 0, "top_posts": [], "score": 50.0, "source": "reddit"}

    if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
        logger.debug("Reddit credentials not configured")
        return default

    loop = asyncio.get_event_loop()

    def _fetch_sync() -> Dict[str, Any]:
        try:
            import praw  # type: ignore[import]
            reddit = praw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT,
            )
            all_texts: list[str] = []
            top_posts: list[Dict[str, Any]] = []

            for sub_name in subreddits[:3]:
                try:
                    sub = reddit.subreddit(sub_name)
                    results = list(sub.search(query, limit=20, time_filter="week"))
                    for post in results:
                        text = f"{post.title} {post.selftext[:500]}"
                        all_texts.append(text)
                        vader = _vader_score(text)
                        top_posts.append({
                            "title": post.title,
                            "score": post.score,
                            "url": f"https://reddit.com{post.permalink}",
                            "sentiment": vader,
                            "subreddit": sub_name,
                        })
                except Exception as sub_exc:
                    logger.debug("Reddit sub failed", extra={"sub": sub_name, "error": str(sub_exc)})

            if not all_texts:
                return default

            avg = _composite_score(all_texts)
            top_posts.sort(key=lambda x: x["score"], reverse=True)

            return {
                "avg_sentiment": avg,
                "post_count": len(all_texts),
                "top_posts": top_posts[:5],
                "score": avg,
                "source": "reddit",
            }
        except ImportError:
            logger.debug("praw not installed — Reddit disabled")
            return default
        except Exception as exc:
            logger.warning("Reddit fetch failed", extra={"error": str(exc)})
            return default

    return await loop.run_in_executor(None, _fetch_sync)


# ---------------------------------------------------------------------------
# Google Trends
# ---------------------------------------------------------------------------
@async_sqlite_cache(ttl_seconds=3600, key_prefix="trends")
async def fetch_google_trends(keywords: list[str]) -> Dict[str, Any]:
    """Fetch Google Trends interest for keywords.

    Parameters
    ----------
    keywords:
        List of search terms (max 5).

    Returns
    -------
    dict
        ``{keyword: {"current_interest", "trend_direction", "spike_detected"}}``
    """
    loop = asyncio.get_event_loop()

    def _fetch_sync() -> Dict[str, Any]:
        try:
            from pytrends.request import TrendReq  # type: ignore[import]
            pytrends = TrendReq(hl="en-US", tz=330, timeout=(10, 25))
            kw_list = keywords[:5]
            pytrends.build_payload(kw_list, timeframe="today 3-m", geo="IN")
            df = pytrends.interest_over_time()
            if df.empty:
                return {}

            result: Dict[str, Any] = {}
            for kw in kw_list:
                if kw not in df.columns:
                    continue
                series = df[kw]
                current = float(series.iloc[-1])
                avg_30d = float(series.tail(30).mean())
                result[kw] = {
                    "current_interest": current,
                    "avg_30d": avg_30d,
                    "trend_direction": "up" if current > avg_30d else "down",
                    "spike_detected": current > avg_30d * 1.5,
                }
            return result
        except ImportError:
            logger.debug("pytrends not installed")
            return {}
        except Exception as exc:
            logger.warning("Google Trends failed", extra={"error": str(exc)})
            return {}

    return await loop.run_in_executor(None, _fetch_sync)


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------
def _detect_anomaly(current_score: float, previous_score: float) -> bool:
    """Return True if sentiment changed >30 points in 24 hours."""
    return abs(current_score - previous_score) > 30


# ---------------------------------------------------------------------------
# Aggregated sentiment
# ---------------------------------------------------------------------------
async def get_aggregated_sentiment(
    symbol: str,
    company_name: str = "",
) -> Dict[str, Any]:
    """Aggregate sentiment from all sources with weighted scoring.

    Weights: Mirofish 35%, StockTwits 25%, Reddit 25%, Trends 15%.
    Falls back to Reddit + StockTwits + VADER if Mirofish is unavailable.

    Parameters
    ----------
    symbol:
        Stock ticker symbol.
    company_name:
        Full company name for news queries.

    Returns
    -------
    dict
        ``{"composite_score", "breakdown", "sources_used", "anomaly_detected"}``
    """
    query = f"{symbol} {company_name}".strip()

    # Run all fetchers concurrently
    mirofish_task = fetch_mirofish_sentiment(symbol)
    stocktwits_task = fetch_stocktwits_sentiment(symbol)
    reddit_task = fetch_reddit_sentiment(query=query)
    trends_task = fetch_google_trends([symbol, company_name] if company_name else [symbol])

    results = await asyncio.gather(
        mirofish_task, stocktwits_task, reddit_task, trends_task,
        return_exceptions=True,
    )

    mirofish_res = results[0] if not isinstance(results[0], Exception) else None
    stocktwits_res = results[1] if not isinstance(results[1], Exception) else {"score": 50.0}
    reddit_res = results[2] if not isinstance(results[2], Exception) else {"score": 50.0}
    trends_res = results[3] if not isinstance(results[3], Exception) else {}

    # Compute trends score from spike detection
    trends_score = 50.0
    if isinstance(trends_res, dict) and trends_res:
        spikes = [v.get("spike_detected", False) for v in trends_res.values()]
        trends_score = 70.0 if any(spikes) else 50.0

    sources_used: list[str] = []
    weighted_score = 0.0
    total_weight = 0.0

    if mirofish_res and isinstance(mirofish_res, dict):
        weighted_score += mirofish_res.get("sentiment_score", 50) * 0.35
        total_weight += 0.35
        sources_used.append("mirofish")
    
    st_score = stocktwits_res.get("score", 50.0) if isinstance(stocktwits_res, dict) else 50.0
    weighted_score += st_score * 0.25
    total_weight += 0.25
    sources_used.append("stocktwits")

    rd_score = reddit_res.get("score", 50.0) if isinstance(reddit_res, dict) else 50.0
    weighted_score += rd_score * 0.25
    total_weight += 0.25
    sources_used.append("reddit")

    weighted_score += trends_score * 0.15
    total_weight += 0.15
    sources_used.append("trends")

    composite = (weighted_score / total_weight) if total_weight > 0 else 50.0

    # Simple previous score comparison (in-memory — TODO: persist to SQLite)
    previous_score = getattr(get_aggregated_sentiment, f"_prev_{symbol}", composite)
    anomaly = _detect_anomaly(composite, previous_score)
    setattr(get_aggregated_sentiment, f"_prev_{symbol}", composite)

    return {
        "composite_score": round(composite, 2),
        "breakdown": {
            "mirofish": mirofish_res.get("sentiment_score", None) if mirofish_res else None,
            "stocktwits": st_score,
            "reddit": rd_score,
            "trends": trends_score,
        },
        "sources_used": sources_used,
        "anomaly_detected": anomaly,
        "symbol": symbol,
        "timestamp": datetime.utcnow().isoformat(),
    }
