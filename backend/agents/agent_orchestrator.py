import os
import json
import re
import asyncio
from typing import Dict, Any
from backend.agents.supervisor_agent import SupervisorAgent, GraphState
from backend.core.model_router import ModelRouter
from backend.utils.logger import get_logger

logger = get_logger(__name__)

class AgentOrchestrator:
    def __init__(self, model_router: ModelRouter):
        self.model_router = model_router
        self.supervisor = SupervisorAgent(model_router)

    async def analyze(self, query: str, user_id: str, quick: bool = False) -> Dict[str, Any]:
        symbol = self._extract_symbol(query)
        
        state = GraphState(
            query=query,
            user_id=user_id,
            symbol=symbol,
            agents_to_run=[],
            collected_data={},
            technical_result={},
            fundamental_result={},
            sentiment_result={},
            risk_result={},
            portfolio_result={},
            final_response="",
            confidence_score=0.0,
            errors=[]
        )
        
        final_state = await self.supervisor.execute(state)
        
        response = {
            "symbol": symbol,
            "response": final_state['final_response'],
            "confidence": final_state['confidence_score'],
            "quick": quick
        }
        
        try:
            cache_dir = f"./data_cache/analyses/{user_id}"
            os.makedirs(cache_dir, exist_ok=True)
            import uuid
            analysis_id = str(uuid.uuid4())
            with open(f"{cache_dir}/{analysis_id}.json", "w") as f:
                json.dump(response, f)
        except Exception as e:
            logger.error(f"Failed to save analysis response: {e}")
            
        return response

    def _extract_symbol(self, query: str) -> str:
        match = re.search(r'\b[A-Z]{2,5}\b', query.upper())
        return match.group(0) if match else "UNKNOWN"
