from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.core.limiter import limiter
from backend.core.model_router import get_model_router
from backend.core.security import verify_access_unlocked

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=64)
    message: str = Field(..., min_length=1, max_length=1000)


def _user_id(current_user: dict) -> str:
    return current_user["sub"]


@router.post("/")
@limiter.limit("10/minute")
async def chat(request: Request, req: ChatMessage, current_user: dict = Depends(verify_access_unlocked)):
    from backend.chat.chat_agent import ChatAgent

    agent = ChatAgent(get_model_router())
    return await agent.chat(_user_id(current_user), req.session_id, req.message)


@router.get("/stream")
@limiter.limit("10/minute")
async def chat_stream(
    request: Request,
    session_id: str,
    message: str,
    current_user: dict = Depends(verify_access_unlocked),
):
    from backend.chat.chat_agent import ChatAgent

    agent = ChatAgent(get_model_router())

    async def event_generator():
        async for chunk in agent.chat_stream(_user_id(current_user), session_id, message[:1000]):
            yield {"data": chunk}
        yield {"data": "[DONE]"}

    return EventSourceResponse(event_generator())


@router.post("/sessions")
@limiter.limit("60/minute")
async def create_session(request: Request, current_user: dict = Depends(verify_access_unlocked)):
    from backend.chat.chat_agent import ChatAgent

    agent = ChatAgent(get_model_router())
    return {"session_id": await agent.new_session(_user_id(current_user))}


@router.get("/sessions")
@limiter.limit("60/minute")
async def get_sessions(request: Request, current_user: dict = Depends(verify_access_unlocked)):
    return []


@router.get("/sessions/{session_id}/history")
@limiter.limit("60/minute")
async def get_history(
    request: Request,
    session_id: str,
    current_user: dict = Depends(verify_access_unlocked),
):
    from backend.chat.chat_agent import ChatAgent

    agent = ChatAgent(get_model_router())
    return await agent.get_history(_user_id(current_user), session_id)
