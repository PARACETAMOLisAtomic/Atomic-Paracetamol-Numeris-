import json
from typing import Dict, Any
from backend.agents.base_agent import BaseQuantAgent
from backend.data.sentiment_fetcher import get_aggregated_sentiment
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class SentimentAnalystAgent(BaseQuantAgent):
    async def _run(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = context.get('symbol')
        if not symbol:
            return {"error": "No symbol provided"}
            
        try:
            sentiment_data = await get_aggregated_sentiment(symbol)
            
            # Incorporate WorldMonitor for Global Macro Sentiment
            from backend.utils.worldmonitor_client import WorldMonitorClient
            wm = WorldMonitorClient()
            wm_data = await wm.get_market_probabilities(symbol)
            
            prompt = (
                f"Analyze the market sentiment for {symbol}: {json.dumps(sentiment_data)}\n\n"
                f"GLOBAL SITUATIONAL AWARENESS (WorldMonitor):\n{json.dumps(wm_data)}\n\n"
                f"Synthesize how global geopolitical and macro signals (WorldMonitor) influence the specific local sentiment (Social/News)."
            )
            llm_analysis = await self.model_router.route("general_analysis", prompt, "You are a senior sentiment analyst specializing in global macro psychology.")
            
            return {
                "symbol": symbol,
                "sentiment_data": sentiment_data,
                "interpretation": llm_analysis
            }
        except Exception as e:
            logger.error(f"SentimentAnalystAgent failed: {e}")
            return {"error": str(e), "sentiment_data": {}}
