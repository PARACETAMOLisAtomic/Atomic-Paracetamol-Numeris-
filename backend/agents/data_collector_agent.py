from typing import Dict, Any
from backend.agents.base_agent import BaseQuantAgent
from backend.data.market_data import fetch_stock_data
from backend.data.news_fetcher import fetch_market_news
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class DataCollectorAgent(BaseQuantAgent):
    async def _run(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = context.get('symbol')
        if not symbol:
            return {"error": "No symbol provided for data collection"}
            
        result = {"symbol": symbol, "data": {}, "news": []}
        
        try:
            market_data = await fetch_stock_data(symbol, period="1y", interval="1d")
            result["data"] = market_data.to_dict(orient="records") if market_data is not None else {}
        except Exception as e:
            logger.error(f"DataCollectorAgent: failed to fetch market data: {e}")
            result["data"] = {"error": str(e)}
            
        try:
            news = await fetch_market_news([symbol])
            result["news"] = news
        except Exception as e:
            logger.error(f"DataCollectorAgent: failed to fetch news: {e}")
            result["news"] = []
            
        return result
