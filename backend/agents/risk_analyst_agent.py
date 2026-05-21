import json
import numpy as np
import pandas as pd
from typing import Dict, Any
from backend.agents.base_agent import BaseQuantAgent
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class RiskAnalystAgent(BaseQuantAgent):
    async def _run(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        symbol = context.get('symbol')
        data = context.get('data_collection_result', {}).get('data')
        
        if not data or isinstance(data, dict) and 'error' in data:
            return {"error": "Missing market data for risk analysis"}
            
        try:
            df = pd.DataFrame(data) if isinstance(data, list) else data
            returns = df['Close'].pct_change().dropna().values
            
            var_95 = np.percentile(returns, 5)
            cvar_95 = returns[returns <= var_95].mean()
            
            volatility = np.std(returns) * np.sqrt(252)
            
            risk_metrics = {
                "VaR_95": float(var_95),
                "CVaR_95": float(cvar_95),
                "Annualized_Volatility": float(volatility)
            }
            
            # Incorporate WorldMonitor & Mirofish for Predictive Risk
            from backend.utils.worldmonitor_client import WorldMonitorClient
            from backend.utils.mirofish_client import MirofishClient
            wm = WorldMonitorClient()
            mf = MirofishClient()
            
            wm_data = await wm.get_market_probabilities(symbol)
            mf_data = await mf.analyze_deep_patterns(symbol)
            
            prompt = (
                f"Evaluate the risk for {symbol} given these quantitative metrics: {json.dumps(risk_metrics)}\n\n"
                f"WORLDMONITOR MACRO RISK VECTORS:\n{json.dumps(wm_data)}\n\n"
                f"MIROFISH SIMULATION PATTERNS:\n{json.dumps(mf_data)}\n\n"
                f"Combine quantitative VaR/Volatility with WorldMonitor's situational risk and Mirofish's agent behavior simulations."
            )
            llm_analysis = await self.model_router.route("risk_analysis", prompt, "You are a senior quantitative risk manager specializing in black-swan detection and multi-agent simulation risk.")
            
            return {
                "symbol": symbol,
                "metrics": risk_metrics,
                "interpretation": llm_analysis
            }
        except Exception as e:
            logger.error(f"RiskAnalystAgent failed: {e}")
            return {"error": str(e)}
