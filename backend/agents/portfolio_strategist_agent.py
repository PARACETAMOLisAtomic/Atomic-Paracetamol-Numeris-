import json
import numpy as np
import cvxpy as cp
from typing import Dict, Any
from backend.agents.base_agent import BaseQuantAgent
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class PortfolioStrategistAgent(BaseQuantAgent):
    async def _run(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        symbols = context.get('symbols', [])
        returns_data = context.get('returns_data', {})
        
        if not symbols or not returns_data:
            return {"error": "Insufficient data for portfolio optimization"}
            
        try:
            n = len(symbols)
            returns_matrix = np.array([returns_data[sym] for sym in symbols])
            mu = np.mean(returns_matrix, axis=1)
            sigma = np.cov(returns_matrix)
            
            w = cp.Variable(n)
            gamma = cp.Parameter(nonneg=True)
            gamma.value = 1.0
            
            ret = mu.T @ w
            risk = cp.quad_form(w, sigma)
            
            prob = cp.Problem(cp.Maximize(ret - gamma * risk),
                              [cp.sum(w) == 1, w >= 0])
            
            prob.solve()
            
            weights = {symbols[i]: float(w.value[i]) for i in range(n)}
            
            prompt = f"Provide a strategy based on optimal weights: {json.dumps(weights)}"
            llm_analysis = await self.model_router.route("general_analysis", prompt, "You are a portfolio manager.")
            
            return {
                "weights": weights,
                "interpretation": llm_analysis
            }
        except Exception as e:
            logger.error(f"PortfolioStrategistAgent failed: {e}")
            return {"error": str(e)}
