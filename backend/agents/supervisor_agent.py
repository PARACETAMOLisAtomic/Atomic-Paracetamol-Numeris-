import asyncio
from typing import Dict, Any, TypedDict, List
from langgraph.graph import StateGraph, END
from backend.core.model_router import ModelRouter
from backend.utils.logger import get_logger
from backend.agents.data_collector_agent import DataCollectorAgent
from backend.agents.technical_analyst_agent import TechnicalAnalystAgent
from backend.agents.fundamental_analyst_agent import FundamentalAnalystAgent
from backend.agents.sentiment_analyst_agent import SentimentAnalystAgent
from backend.agents.risk_analyst_agent import RiskAnalystAgent
from backend.agents.portfolio_strategist_agent import PortfolioStrategistAgent

logger = get_logger(__name__)

class GraphState(TypedDict):
    query: str
    user_id: str
    symbol: str
    agents_to_run: List[str]
    collected_data: Dict[str, Any]
    technical_result: Dict[str, Any]
    fundamental_result: Dict[str, Any]
    sentiment_result: Dict[str, Any]
    risk_result: Dict[str, Any]
    portfolio_result: Dict[str, Any]
    final_response: str
    confidence_score: float
    errors: List[str]

class SupervisorAgent:
    def __init__(self, model_router: ModelRouter):
        self.model_router = model_router
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(GraphState)
        
        workflow.add_node("route_query", self.route_query)
        workflow.add_node("run_data_collection", self.run_data_collection)
        workflow.add_node("run_technical", self.run_technical)
        workflow.add_node("run_fundamental", self.run_fundamental)
        workflow.add_node("run_sentiment", self.run_sentiment)
        workflow.add_node("run_risk", self.run_risk)
        workflow.add_node("run_portfolio", self.run_portfolio)
        workflow.add_node("aggregate_results", self.aggregate_results)
        
        workflow.add_edge("route_query", "run_data_collection")
        workflow.add_edge("run_data_collection", "run_technical")
        workflow.add_edge("run_technical", "run_fundamental")
        workflow.add_edge("run_fundamental", "run_sentiment")
        workflow.add_edge("run_sentiment", "run_risk")
        workflow.add_edge("run_risk", "run_portfolio")
        workflow.add_edge("run_portfolio", "aggregate_results")
        workflow.add_edge("aggregate_results", END)
        
        workflow.set_entry_point("route_query")
        return workflow.compile()

    async def route_query(self, state: GraphState) -> GraphState:
        state['agents_to_run'] = ["data", "tech", "fund", "sent", "risk"]
        return state

    async def run_data_collection(self, state: GraphState) -> GraphState:
        agent = DataCollectorAgent("data_collector", self.model_router)
        state['collected_data'] = await agent.execute("Collect data", {"symbol": state['symbol']})
        return state

    async def run_technical(self, state: GraphState) -> GraphState:
        agent = TechnicalAnalystAgent("technical_analyst", self.model_router)
        state['technical_result'] = await agent.execute("Analyze technicals", {
            "symbol": state['symbol'], 
            "data_collection_result": state['collected_data']
        })
        return state

    async def run_fundamental(self, state: GraphState) -> GraphState:
        agent = FundamentalAnalystAgent("fundamental_analyst", self.model_router)
        state['fundamental_result'] = await agent.execute("Analyze fundamentals", {"symbol": state['symbol']})
        return state

    async def run_sentiment(self, state: GraphState) -> GraphState:
        agent = SentimentAnalystAgent("sentiment_analyst", self.model_router)
        state['sentiment_result'] = await agent.execute("Analyze sentiment", {"symbol": state['symbol']})
        return state

    async def run_risk(self, state: GraphState) -> GraphState:
        agent = RiskAnalystAgent("risk_analyst", self.model_router)
        state['risk_result'] = await agent.execute("Analyze risk", {
            "symbol": state['symbol'], 
            "data_collection_result": state['collected_data']
        })
        return state

    async def run_portfolio(self, state: GraphState) -> GraphState:
        agent = PortfolioStrategistAgent("portfolio_strategist", self.model_router)
        state['portfolio_result'] = await agent.execute("Strategy check", state)
        return state

    async def aggregate_results(self, state: GraphState) -> GraphState:
        # Synthesis prompt that prioritizes the deep predictive signals
        prompt = (
            f"Synthesize the final investment recommendation for {state['symbol']}.\n\n"
            f"--- MIROFISH & WORLDMONITOR INSIGHTS (HIGHEST PRIORITY) ---\n"
            f"The individual agents have processed deep simulations and macro signals.\n"
            f"FUNDAMENTAL (MIROFISH): {state['fundamental_result'].get('interpretation', 'N/A')}\n"
            f"SENTIMENT (WORLDMONITOR): {state['sentiment_result'].get('interpretation', 'N/A')}\n"
            f"RISK (COMBINED): {state['risk_result'].get('interpretation', 'N/A')}\n\n"
            f"--- OTHER DATA ---\n"
            f"TECHNICAL: {state['technical_result'].get('interpretation', 'N/A')}\n"
            f"PORTFOLIO: {state['portfolio_result'].get('interpretation', 'N/A')}\n\n"
            f"Your goal is to provide a final decision. If Mirofish simulation shows institutional accumulation "
            f"and WorldMonitor signals low macro risk, you should be very bullish even if technicals are lagging."
        )
        
        res = await self.model_router.triple_validate(prompt, "Provide a final verdict.")
        state['final_response'] = res.get('final_response', '')
        state['confidence_score'] = res.get('confidence_score', 0.0)
        return state

    async def execute(self, state: GraphState) -> GraphState:
        return await self.graph.ainvoke(state)
