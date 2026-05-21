import os
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from backend.core.limiter import limiter
from backend.core.security import verify_access_unlocked

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/synthesize")
@limiter.limit("10/minute")
async def synthesize(request: Request, text: str, current_user: dict = Depends(verify_access_unlocked)):
    return {"audio_url": "/api/voice/audio/test.mp3"}


@router.get("/audio/{filename}")
@limiter.limit("60/minute")
async def get_audio(request: Request, filename: str, current_user: dict = Depends(verify_access_unlocked)):
    path = f"./data_cache/audio/{filename}"
    if os.path.exists(path):
        return FileResponse(path)
    return {"error": "Not found"}
