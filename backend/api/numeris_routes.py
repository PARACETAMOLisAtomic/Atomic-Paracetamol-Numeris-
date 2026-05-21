from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from backend.core.limiter import limiter
from backend.core.security import verify_access_unlocked
from backend.db.supabase_client import get_supabase_client
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["numeris-ui"])

_FALLBACK_MODULES: List[Dict[str, Any]] = [
    {"id": 1, "name": "Data Collector Agent", "domain": "Market Data", "description": "Fetches OHLCV, options chain, corporate actions, and macro inputs with cached fallbacks.", "status": "ACTIVE", "metric": 94, "gradient": "linear-gradient(135deg,#06b6d4,#8b5cf6)", "depth": 1},
    {"id": 2, "name": "Technical Analyst Agent", "domain": "Technicals", "description": "Computes RSI, MACD, Fibonacci levels, candlestick patterns, and signal conviction.", "status": "ACTIVE", "metric": 88, "gradient": "linear-gradient(135deg,#10b981,#06b6d4)", "depth": 2},
    {"id": 3, "name": "Fundamental Analyst Agent", "domain": "Fundamentals", "description": "Normalizes valuation, quality, earnings, and filing data for long-horizon scoring.", "status": "ACTIVE", "metric": 82, "gradient": "linear-gradient(135deg,#f59e0b,#ef4444)", "depth": 3},
    {"id": 4, "name": "Sentiment Analyst Agent", "domain": "Sentiment", "description": "Combines news, social velocity, and text sentiment into reflexivity-aware market context.", "status": "ACTIVE", "metric": 79, "gradient": "linear-gradient(135deg,#8b5cf6,#ec4899)", "depth": 4},
    {"id": 5, "name": "Risk Analyst Agent", "domain": "Risk", "description": "Tracks VaR, CVaR, stress tests, beta, drawdown, and correlation concentration.", "status": "ACTIVE", "metric": 91, "gradient": "linear-gradient(135deg,#ef4444,#f59e0b)", "depth": 5},
    {"id": 6, "name": "Portfolio Strategist Agent", "domain": "Portfolio", "description": "Optimizes allocations and reconciles manual holdings with broker-linked exposure.", "status": "ACTIVE", "metric": 85, "gradient": "linear-gradient(135deg,#3b82f6,#10b981)", "depth": 6},
    {"id": 7, "name": "Supervisor Agent", "domain": "Orchestration", "description": "Routes tasks across specialist agents and merges consensus into operator-ready briefs.", "status": "ACTIVE", "metric": 96, "gradient": "linear-gradient(135deg,#06b6d4,#3b82f6)", "depth": 7},
    {"id": 8, "name": "Report Generator Agent", "domain": "Reporting", "description": "Creates structured research, risk alerts, executive summaries, and audio-ready briefs.", "status": "ACTIVE", "metric": 77, "gradient": "linear-gradient(135deg,#ec4899,#8b5cf6)", "depth": 8},
]

_FALLBACK_SIGNALS: List[Dict[str, Any]] = [
    {"id": 1, "symbol": "RELIANCE", "verdict": "BUY", "confidence": 87, "momentum": 78, "risk": 32, "agent": "Technical+Sentiment", "price": 2840.50},
    {"id": 2, "symbol": "TCS", "verdict": "HOLD", "confidence": 72, "momentum": 55, "risk": 28, "agent": "Fundamental", "price": 3920.00},
    {"id": 3, "symbol": "HDFCBANK", "verdict": "BUY", "confidence": 81, "momentum": 69, "risk": 25, "agent": "Multi-agent Swarm", "price": 1710.30},
    {"id": 4, "symbol": "INFY", "verdict": "SELL", "confidence": 63, "momentum": 38, "risk": 61, "agent": "Risk Analyst", "price": 1420.75},
    {"id": 5, "symbol": "AAPL", "verdict": "BUY", "confidence": 78, "momentum": 82, "risk": 34, "agent": "Technical Analyst", "price": 212.20},
]

_FALLBACK_SIMULATIONS: List[Dict[str, Any]] = [
    {"id": 1, "name": "India Rate Shock Simulation", "engine": "Mirofish", "region": "South Asia", "intensity": 65, "forecast": "RBI tightening scenario: banks soften while defensive cash-flow sectors lead.", "updated_at": datetime.now(timezone.utc).isoformat()},
    {"id": 2, "name": "US Growth Slowdown", "engine": "WorldMonitor", "region": "Americas", "intensity": 45, "forecast": "Export demand headwind with pharma and staples acting as lower-beta hedges.", "updated_at": datetime.now(timezone.utc).isoformat()},
    {"id": 3, "name": "APAC Semiconductor Disruption", "engine": "WorldMonitor", "region": "APAC", "intensity": 72, "forecast": "Chip supply stress lifts defense and infra while pressuring high-duration technology.", "updated_at": datetime.now(timezone.utc).isoformat()},
]

_FALLBACK_REPORTS: List[Dict[str, Any]] = [
    {"id": 1, "title": "NIFTY50 Weekly Intelligence Brief", "category": "Market Overview", "severity": "MEDIUM", "summary": "Consolidation above long-term trend. Accumulate quality large-caps on measured pullbacks.", "created_at": datetime.now(timezone.utc).isoformat()},
    {"id": 2, "title": "Banking Sector Risk Alert", "category": "Sector Alert", "severity": "HIGH", "summary": "Credit-cycle dispersion rising. Private banks retain relative strength while weaker lenders need caution.", "created_at": datetime.now(timezone.utc).isoformat()},
    {"id": 3, "title": "Geopolitical Risk Surface Update", "category": "Geopolitics", "severity": "HIGH", "summary": "Shipping-risk premium remains elevated and can transmit into crude, INR, and logistics margins.", "created_at": datetime.now(timezone.utc).isoformat()},
]

_FALLBACK_INTERACTIONS: List[Dict[str, Any]] = [
    {"id": 1, "prompt": "What is the current NIFTY50 outlook?", "response": "Numeris sees bullish consolidation above long-term trend. Watch breadth, bank leadership, and crude-linked INR pressure before adding exposure.", "agent": "Numeris Supervisor", "confidence": 88, "created_at": datetime.now(timezone.utc).isoformat()},
]

_FALLBACK_EVENTS: List[Dict[str, Any]] = [
    {"id": 1, "event_type": "RISK_PULSE", "title": "VaR threshold crossed for concentrated exposure", "detail": "Daily VaR exceeded policy limits. Position size flagged for review.", "impact": 82, "region": "India", "created_at": datetime.now(timezone.utc).isoformat()},
    {"id": 2, "event_type": "SIGNAL_SYNC", "title": "Swarm consensus confirms RELIANCE setup", "detail": "Technical and sentiment agents agree on constructive momentum.", "impact": 74, "region": "NSE", "created_at": datetime.now(timezone.utc).isoformat()},
    {"id": 3, "event_type": "WORLD_MONITOR", "title": "Crude volatility pulse detected", "detail": "Energy and logistics margin sensitivity moved higher in the latest scenario run.", "impact": 91, "region": "Global", "created_at": datetime.now(timezone.utc).isoformat()},
]

_FALLBACK_BRAIN_TRAITS: List[Dict[str, Any]] = [
    {"id": 1, "label": "Reasoning", "value": 94, "color": "#06b6d4", "priority": 1},
    {"id": 2, "label": "Speed", "value": 88, "color": "#8b5cf6", "priority": 2},
    {"id": 3, "label": "Memory", "value": 91, "color": "#10b981", "priority": 3},
    {"id": 4, "label": "Risk Sense", "value": 96, "color": "#ef4444", "priority": 4},
]

_FALLBACK_BRAIN_REGIONS: List[Dict[str, Any]] = [
    {"id": 1, "name": "Memory", "system": "RAG Memory", "description": "Research memory and chat context.", "section_id": "vault", "x": 32, "y": 36, "position_order": 1},
    {"id": 2, "name": "Analysis", "system": "Market Signals", "description": "Technical and fundamental model output.", "section_id": "markets", "x": 58, "y": 31, "position_order": 2},
    {"id": 3, "name": "Risk", "system": "Exposure Guard", "description": "VaR, stress, and drawdown controls.", "section_id": "command-deck", "x": 70, "y": 52, "position_order": 3},
    {"id": 4, "name": "World", "system": "Geopolitics", "description": "WorldMonitor and GDELT event feeds.", "section_id": "geopolitics", "x": 42, "y": 63, "position_order": 4},
    {"id": 5, "name": "Terminal", "system": "Supervisor", "description": "Operator prompt routing.", "section_id": "terminal", "x": 62, "y": 72, "position_order": 5},
]

_FALLBACK_ENTRANCE_SEQUENCE = [
    {"id": 1, "label": "Security", "value": "verified", "sequence_order": 1},
    {"id": 2, "label": "Memory", "value": "hydrated", "sequence_order": 2},
    {"id": 3, "label": "World", "value": "synced", "sequence_order": 3},
    {"id": 4, "label": "Swarm", "value": "awake", "sequence_order": 4},
]

_interactions = list(_FALLBACK_INTERACTIONS)
_simulations = list(_FALLBACK_SIMULATIONS)
_next_interaction_id = len(_interactions) + 1


def _sb():
    return get_supabase_client(use_service_role=True)


async def _select(table: str, fallback: List[Dict[str, Any]], order: Optional[str] = None, desc: bool = False, limit: Optional[int] = None):
    client = _sb()
    if client is None:
        return fallback
    try:
        def run_query():
            query = client.table(table).select("*")
            if order:
                query = query.order(order, desc=desc)
            if limit:
                query = query.limit(limit)
            return query.execute()

        response = await asyncio.to_thread(run_query)
        return response.data or fallback
    except Exception as exc:
        logger.debug("Supabase select failed", extra={"table": table, "error": str(exc)})
        return fallback


@router.get("/numeris")
@limiter.limit("60/minute")
async def get_numeris_dashboard(
    request: Request,
    current_user: dict = Depends(verify_access_unlocked),
) -> Dict[str, Any]:
    modules, signals, simulations, reports, interactions, events, traits, regions = await asyncio.gather(
        _select("numeris_modules", _FALLBACK_MODULES, "id"),
        _select("numeris_signals", _FALLBACK_SIGNALS, "confidence", desc=True),
        _select("numeris_simulations", _simulations, "id"),
        _select("numeris_reports", _FALLBACK_REPORTS, "created_at", desc=True, limit=8),
        _select("numeris_interactions", _interactions, "created_at", limit=12),
        _select("numeris_event_stream", _FALLBACK_EVENTS, "created_at", desc=True, limit=8),
        _select("numeris_brain_traits", _FALLBACK_BRAIN_TRAITS, "priority"),
        _select("numeris_brain_regions", _FALLBACK_BRAIN_REGIONS, "position_order"),
    )
    return {
        "modules": modules,
        "signals": signals,
        "simulations": simulations,
        "reports": reports,
        "interactions": interactions,
        "events": events,
        "brainTraits": traits,
        "brainRegions": regions,
    }


@router.post("/numeris", status_code=201)
@limiter.limit("20/minute")
async def post_numeris_prompt(
    request: Request,
    body: Dict[str, Any] = Body(...),
    current_user: dict = Depends(verify_access_unlocked),
) -> Dict[str, Any]:
    global _next_interaction_id

    prompt = str(body.get("prompt", "")).strip()[:600]
    if len(prompt) < 2:
        raise HTTPException(status_code=400, detail="Prompt is required")

    focus = _classify_focus(prompt)
    response_text = (
        f"Numeris routed your query to the supervisor layer. Primary focus: {focus}. "
        "The recommended workflow is to validate liquidity, compare signal conviction with event risk, "
        "then size exposure with a clear invalidation level."
    )

    try:
        from backend.core.model_router import get_model_router

        router_instance = get_model_router()
        model_response = await router_instance.route(
            "chat",
            prompt,
            "You are Numeris, a concise institutional financial intelligence assistant. Do not provide personalized financial advice.",
            max_tokens=600,
        )
        if model_response:
            response_text = model_response
    except Exception as exc:
        logger.debug("Model route unavailable for Numeris prompt", extra={"error": str(exc)})

    interaction = {
        "id": _next_interaction_id,
        "prompt": prompt,
        "response": response_text,
        "agent": "Numeris Supervisor",
        "confidence": 91,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _interactions.append(interaction)
    _next_interaction_id += 1

    client = _sb()
    if client is not None:
        try:
            payload = {
            "user_id": current_user["sub"],
                "prompt": prompt,
                "response": response_text,
                "agent": "Numeris Supervisor",
                "confidence": 91,
            }
            await asyncio.to_thread(lambda: client.table("numeris_interactions").insert(payload).execute())
        except Exception as exc:
            logger.debug("Supabase interaction insert skipped", extra={"error": str(exc)})

    return interaction


@router.put("/numeris")
@limiter.limit("30/minute")
async def put_numeris_simulation(
    request: Request,
    body: Dict[str, Any] = Body(...),
    current_user: dict = Depends(verify_access_unlocked),
) -> Dict[str, Any]:
    sim_id = int(body.get("id") or 0)
    intensity = body.get("intensity")
    if not sim_id or intensity is None:
        raise HTTPException(status_code=400, detail="Simulation id and intensity are required")

    bounded = max(0, min(100, int(intensity)))
    now = datetime.now(timezone.utc).isoformat()
    for sim in _simulations:
        if sim["id"] == sim_id:
            sim["intensity"] = bounded
            sim["updated_at"] = now
            client = _sb()
            if client is not None:
                try:
                    await asyncio.to_thread(
                        lambda: client.table("numeris_simulations").update({"intensity": bounded, "updated_at": now}).eq("id", sim_id).execute()
                    )
                except Exception as exc:
                    logger.debug("Supabase simulation update skipped", extra={"error": str(exc)})
            return sim
    raise HTTPException(status_code=404, detail="Simulation not found")


@router.delete("/numeris")
@limiter.limit("30/minute")
async def delete_numeris_interaction(
    request: Request,
    body: Dict[str, Any] = Body(...),
    current_user: dict = Depends(verify_access_unlocked),
) -> Dict[str, bool]:
    inter_id = int(body.get("id") or 0)
    if not inter_id:
        raise HTTPException(status_code=400, detail="Interaction id is required")

    global _interactions
    _interactions = [item for item in _interactions if item["id"] != inter_id]
    client = _sb()
    if client is not None:
        try:
            await asyncio.to_thread(lambda: client.table("numeris_interactions").delete().eq("id", inter_id).execute())
        except Exception as exc:
            logger.debug("Supabase interaction delete skipped", extra={"error": str(exc)})
    return {"ok": True}


@router.get("/entrance-sequence")
@limiter.limit("60/minute")
async def get_entrance_sequence(request: Request):
    return await _select("numeris_entrance_sequences", _FALLBACK_ENTRANCE_SEQUENCE, "sequence_order")


@router.get("/geopolitical-news")
@limiter.limit("30/minute")
async def get_geopolitical_news(
    request: Request,
    current_user: dict = Depends(verify_access_unlocked),
) -> List[Dict[str, Any]]:
    try:
        import aiohttp

        query = quote_plus("(geopolitical OR sanctions OR conflict OR trade war OR supply chain OR military OR diplomacy OR election OR oil shipping)")
        gdelt_url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=ArtList&format=json&maxrecords=12&sort=HybridRel&timespan=24h"
        async with aiohttp.ClientSession() as session:
            async with session.get(gdelt_url, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                if resp.status == 200:
                    data = await resp.json(content_type=None)
                    articles = data.get("articles", [])
                    result = [_normalize_article(index, article) for index, article in enumerate(articles[:12])]
                    if result:
                        return result
    except Exception as exc:
        logger.debug("GDELT fetch failed", extra={"error": str(exc)})

    return [
        {"id": 1, "title": "Global markets await central bank policy signals", "source": "WorldMonitor", "url": "#", "region": "Global", "impact": 68, "summary": "Central bank guidance divergence is creating volatility across rates and FX.", "published_at": datetime.now(timezone.utc).isoformat()},
        {"id": 2, "title": "Shipping disruptions keep energy risk premium elevated", "source": "WorldMonitor", "url": "#", "region": "Middle East", "impact": 85, "summary": "Energy and logistics-sensitive sectors remain exposed to shipping-route stress.", "published_at": datetime.now(timezone.utc).isoformat()},
    ]


def _classify_focus(prompt: str) -> str:
    lower = prompt.lower()
    if "risk" in lower:
        return "portfolio exposure and VaR containment"
    if any(word in lower for word in ("geo", "war", "world", "sanction")):
        return "geopolitical stress mapping"
    if any(word in lower for word in ("sentiment", "social", "reddit")):
        return "sentiment reflexivity"
    if any(word in lower for word in ("portfolio", "allocation", "broker")):
        return "allocation optimization"
    if any(word in lower for word in ("technical", "rsi", "macd", "chart")):
        return "technical structure"
    return "multi-agent market intelligence"


def _normalize_article(index: int, article: Dict[str, Any]) -> Dict[str, Any]:
    title = article.get("title", "Geopolitical development")
    source = article.get("domain", "GDELT")
    return {
        "id": index + 1,
        "title": title,
        "source": source,
        "url": article.get("url", "#"),
        "region": _detect_region(title),
        "impact": _score_impact(title, source),
        "summary": f"GDELT-tracked development from {source}. Review source context before making market decisions.",
        "published_at": article.get("seendate", datetime.now(timezone.utc).isoformat()),
    }


def _score_impact(title: str = "", source: str = "") -> int:
    text = f"{title} {source}".lower()
    score = 54
    if any(word in text for word in ("war", "missile", "attack", "sanction", "nuclear", "ceasefire", "conflict", "strike")):
        score += 22
    if any(word in text for word in ("oil", "gas", "shipping", "semiconductor", "supply", "currency", "inflation", "trade")):
        score += 14
    if any(word in text for word in ("china", "russia", "ukraine", "israel", "iran", "taiwan", "red sea", "nato", "india", "pakistan")):
        score += 10
    return min(98, score)


def _detect_region(title: str = "") -> str:
    text = title.lower()
    if any(word in text for word in ("china", "taiwan", "japan", "korea", "south china sea", "apac")):
        return "APAC"
    if any(word in text for word in ("ukraine", "russia", "nato", "europe")):
        return "Europe"
    if any(word in text for word in ("israel", "iran", "gaza", "red sea", "yemen", "saudi", "middle east")):
        return "Middle East"
    if any(word in text for word in ("india", "pakistan", "bangladesh")):
        return "South Asia"
    if any(word in text for word in ("us ", "u.s.", "america", "mexico", "canada")):
        return "Americas"
    return "Global"
