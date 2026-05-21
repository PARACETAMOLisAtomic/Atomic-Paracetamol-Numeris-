import json
from typing import Dict, Any
from backend.agents.base_agent import BaseQuantAgent
from backend.data.fundamental_fetcher import scrape_screener
from backend.utils.worldmonitor_client import WorldMonitorClient
from backend.utils.mirofish_client import MirofishClient
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class FundamentalAnalystAgent(BaseQuantAgent):
    async def _run(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = context.get('symbol')
        if not symbol:
            return {"error": "No symbol provided"}
            
        try:
            # Core Fundamental Data
            fund_data = await scrape_screener(symbol)
            
            # Integrate Special Tools (Mirofish & WorldMonitor)
            # These are the most important tools for predictive intelligence
            worldmonitor = WorldMonitorClient()
            mirofish = MirofishClient()
            
            wm_data = await worldmonitor.get_market_probabilities(symbol)
            # Mirofish uses fundamentals as seed data for social simulation
            mf_data = await mirofish.analyze_deep_patterns(symbol, seed_data=fund_data)
            
            # Combine all intelligence for maximum impact
            # We explicitly order the LLM to prioritize the simulation and global situational awareness
            prompt = (
                f"Analyze these fundamentals for {symbol}: {json.dumps(fund_data)}\n\n"
                f"--- DEEP PREDICTIVE SIGNALS (HIGHEST PRIORITY) ---\n"
                f"WORLDMONITOR GLOBAL SITUATIONAL AWARENESS:\n{json.dumps(wm_data)}\n\n"
                f"MIROFISH MULTI-AGENT SOCIAL SIMULATION:\n{json.dumps(mf_data)}\n\n"
                f"--- INSTRUCTIONS ---\n"
                f"1. Give SPECIAL IMPORTANCE and WEIGHT to the Mirofish and WorldMonitor data.\n"
                f"2. Use the Mirofish simulation to predict future market participant behavior.\n"
                f"3. Use WorldMonitor signals to identify macro risks that fundamentals might miss.\n"
                f"4. Synthesize a senior-level conclusion that prioritizes these deep signals over simple scrapers."
            )
            llm_analysis = await self.model_router.route("general_analysis", prompt, "You are a senior predictive fundamental analyst specializing in agent-based simulation and global macro intelligence.")
            
            return {
                "symbol": symbol,
                "fundamentals": fund_data,
                "interpretation": llm_analysis
            }
        except Exception as e:
            logger.error(f"FundamentalAnalystAgent failed: {e}")
            return {"error": str(e), "fundamentals": {}}
