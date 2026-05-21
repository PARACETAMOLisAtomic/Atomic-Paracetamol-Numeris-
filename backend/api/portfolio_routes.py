from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.core.limiter import limiter
from backend.core.security import verify_access_unlocked
from backend.db import supabase_client

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class ManualHoldingRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Za-z0-9._-]+$")
    quantity: float = Field(..., gt=0)
    buy_price: float = Field(..., ge=0)


@router.get("/manual")
@limiter.limit("60/minute")
async def get_manual_portfolio(request: Request, current_user: dict = Depends(verify_access_unlocked)):
    holdings = await supabase_client.get_manual_holdings(current_user["sub"])
    return {"holdings": holdings}


@router.post("/manual")
@limiter.limit("60/minute")
async def add_to_portfolio(
    request: Request,
    req: ManualHoldingRequest,
    current_user: dict = Depends(verify_access_unlocked),
):
    success = await supabase_client.add_manual_holding(
        current_user["sub"],
        req.symbol,
        req.quantity,
        req.buy_price,
    )
    if not success:
        raise HTTPException(status_code=503, detail="Portfolio storage is unavailable")
    return {"status": "success"}


@router.delete("/manual/{symbol}")
@limiter.limit("60/minute")
async def remove_from_portfolio(
    request: Request,
    symbol: str,
    current_user: dict = Depends(verify_access_unlocked),
):
    success = await supabase_client.delete_manual_holding(current_user["sub"], symbol)
    if not success:
        raise HTTPException(status_code=503, detail="Portfolio storage is unavailable")
    return {"status": "success"}


@router.get("/")
@limiter.limit("60/minute")
async def get_portfolio(request: Request, current_user: dict = Depends(verify_access_unlocked)):
    holdings = await supabase_client.get_manual_holdings(current_user["sub"])
    return {"holdings": holdings}
