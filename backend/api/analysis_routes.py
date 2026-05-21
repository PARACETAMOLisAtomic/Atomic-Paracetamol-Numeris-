from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from backend.core.limiter import limiter
from backend.core.model_router import get_model_router
from backend.core.security import verify_access_unlocked

router = APIRouter(prefix="/analyze", tags=["analysis"])
_analysis_results: Dict[str, Dict[str, Any]] = {}


class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    quick: bool = False


class AnalyzeResponse(BaseModel):
    task_id: str
    status: str


@router.post("/", response_model=AnalyzeResponse)
@limiter.limit("10/minute")
async def analyze_query(
    request: Request,
    req: AnalyzeRequest,
    current_user: dict = Depends(verify_access_unlocked),
):
    task_id = str(uuid.uuid4())
    user_id = current_user["sub"]
    try:
        from backend.agents.agent_orchestrator import AgentOrchestrator

        orchestrator = AgentOrchestrator(get_model_router())
        result = await orchestrator.analyze(req.query, user_id, req.quick)
    except Exception:
        result = {
            "symbol": "UNKNOWN",
            "response": f"Numeris analysis fallback: {req.query[:160]}",
            "confidence": 50,
            "quick": req.quick,
        }
    _analysis_results[task_id] = {"status": "completed", "result": result}
    return {"task_id": task_id, "status": "completed"}


@router.get("/{task_id}")
@limiter.limit("60/minute")
async def get_analysis_result(request: Request, task_id: str, current_user: dict = Depends(verify_access_unlocked)):
    return _analysis_results.get(task_id, {"status": "not_found", "result": None})
