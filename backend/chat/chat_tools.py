from typing import Optional, Dict, Any
import yfinance as yf
from backend.utils.cache import redis_cache
from backend.utils.logger import get_logger

logger = get_logger(__name__)

async def get_stock_quote(symbol: str) -> Optional[Dict[str, Any]]:
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.fast_info
        return {
            "symbol": symbol,
            "last_price": info.last_price,
            "previous_close": info.previous_close,
            "market_cap": info.market_cap
        }
    except Exception as e:
        logger.error(f"get_stock_quote failed for {symbol}: {e}")
        return None

@redis_cache(ttl_seconds=60, key_prefix="market_summary")
async def get_market_summary() -> Optional[Dict[str, Any]]:
    try:
        nifty = yf.Ticker("^NSEI").fast_info
        sensex = yf.Ticker("^BSESN").fast_info
        return {
            "NIFTY50": {"last_price": nifty.last_price, "previous_close": nifty.previous_close},
            "SENSEX": {"last_price": sensex.last_price, "previous_close": sensex.previous_close}
        }
    except Exception as e:
        logger.error(f"get_market_summary failed: {e}")
        return None

async def search_company_news(symbol: str) -> Optional[Dict[str, Any]]:
    return None

async def get_financial_calendar() -> Optional[Dict[str, Any]]:
    return None

async def get_top_movers() -> Optional[Dict[str, Any]]:
    return None
