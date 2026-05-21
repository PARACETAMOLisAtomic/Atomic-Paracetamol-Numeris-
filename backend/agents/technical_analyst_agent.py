from typing import Dict, Any
import json
from backend.agents.base_agent import BaseQuantAgent
from backend.services.technical_analysis import TechnicalAnalyzer
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class TechnicalAnalystAgent(BaseQuantAgent):
    async def _run(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = context.get('symbol')
        data = context.get('data_collection_result', {}).get('data')
        
        if not data or isinstance(data, dict) and 'error' in data:
            return {"error": "Missing or invalid market data for technical analysis"}
            
        try:
            analyzer = TechnicalAnalyzer()
            import pandas as pd
            df = pd.DataFrame(data) if isinstance(data, list) else data
            
            tech_results = analyzer.analyze(df)
            
            prompt = f"Analyze these technical indicators for {symbol}: {json.dumps(tech_results)}"
            llm_analysis = await self.model_router.route("quantitative", prompt, "You are a senior technical analyst.")
            
            return {
                "symbol": symbol,
                "indicators": tech_results,
                "interpretation": llm_analysis
            }
        except Exception as e:
            logger.error(f"TechnicalAnalystAgent failed: {e}")
            return {"error": str(e)}
