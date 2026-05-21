import secrets
import asyncio
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.core.limiter import limiter
from backend.core.security import get_current_user, get_current_user_optional, verify_admin_role
from backend.utils.logger import get_logger

logger = get_logger("auth_routes")
router = APIRouter(prefix="/auth", tags=["auth"])


class RedeemRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=100)


class GenerateCodeRequest(BaseModel):
    role: str = Field("standard_user", pattern="^(admin|beta_user|standard_user)$")
    count: int = Field(1, ge=1, le=100)


class RevokeCodeRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=100)
    is_active: bool


def generate_random_code(role: str = "standard_user") -> str:
    """Generate a randomized secure access/invite code."""
    # Use distinct uppercase alphanumeric characters (omitting O, 0, I, 1 for user convenience)
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    part1 = "".join(secrets.choice(chars) for _ in range(4))
    part2 = "".join(secrets.choice(chars) for _ in range(4))
    role_prefix = "ADMN" if role == "admin" else "BETA" if role == "beta_user" else "USER"
    return f"NUM-{role_prefix}-{part1}-{part2}"


@router.get("/me")
@limiter.limit("60/minute")
async def get_me(request: Request, current_user: dict = Depends(get_current_user)):
    """Return current authenticated user profile."""
    return {
        "id": current_user["sub"],
        "email": current_user.get("email"),
        "role": current_user.get("role", "authenticated"),
        "provider": "supabase",
    }


@router.get("/status")
@limiter.limit("60/minute")
async def get_auth_status(request: Request, user: Optional[dict] = Depends(get_current_user_optional)):
    """Check authentication, invite status, roles, and feature flags."""
    if not user:
        return {
            "authenticated": False,
            "has_access": False,
            "role": None,
            "feature_flags": {},
        }

    user_id = user["sub"]
    from backend.db.supabase_client import get_supabase_client
    client = get_supabase_client(use_service_role=True)
    if client is None:
        # Offline or local development fallback configuration
        return {
            "authenticated": True,
            "has_access": True,
            "role": "admin",
            "feature_flags": {
                "portfolio_optimization": True,
                "voice_commands": True,
                "advanced_risk_analytics": True,
            },
        }

    try:
        def check_status_and_flags():
            access = client.table("numeris_user_access").select("*").eq("user_id", user_id).execute()
            flags = client.table("numeris_feature_flags").select("*").execute()
            return access, flags

        access_resp, flags_resp = await asyncio.to_thread(check_status_and_flags)

        has_access = len(access_resp.data) > 0
        role = access_resp.data[0].get("role", "standard_user") if has_access else "standard_user"

        feature_flags = {flag["name"]: flag["is_enabled"] for flag in (flags_resp.data or [])}

        return {
            "authenticated": True,
            "has_access": has_access,
            "role": role,
            "feature_flags": feature_flags,
        }
    except Exception as exc:
        logger.error(f"Error checking authentication status for {user_id}: {exc}")
        return {
            "authenticated": True,
            "has_access": False,
            "role": "standard_user",
            "feature_flags": {},
        }


@router.post("/redeem")
@limiter.limit("10/minute")
async def redeem_code(
    request: Request,
    body: RedeemRequest,
    current_user: dict = Depends(get_current_user),
):
    """Redeem a private access code to unlock platform access and set user role."""
    user_id = current_user["sub"]
    code = body.code.strip()

    from backend.db.supabase_client import get_supabase_client
    client = get_supabase_client(use_service_role=True)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable.",
        )

    try:
        def verify_code():
            return client.table("numeris_access_codes").select("*").eq("code", code).eq("is_active", True).execute()

        verify_resp = await asyncio.to_thread(verify_code)
        if not verify_resp.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or inactive access code.",
            )

        code_info = verify_resp.data[0]
        role = code_info.get("role", "standard_user")

        def link_user():
            return client.table("numeris_user_access").upsert({
                "user_id": user_id,
                "code": code,
                "role": role,
            }).execute()

        await asyncio.to_thread(link_user)
        logger.info(f"User {user_id} redeemed code {code} assigning role {role}")
        return {"status": "success", "role": role}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to redeem code {code} for user {user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Code redemption validation failed.",
        )


# ---------------------------------------------------------------------------
# Admin Management Routes
# ---------------------------------------------------------------------------

@router.get("/admin/codes")
@limiter.limit("20/minute")
async def get_admin_codes(
    request: Request,
    admin: dict = Depends(verify_admin_role),
):
    """List all access codes (Admin only)."""
    from backend.db.supabase_client import get_supabase_client
    client = get_supabase_client(use_service_role=True)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable.",
        )

    try:
        def fetch_codes():
            return client.table("numeris_access_codes").select("*").order("created_at", desc=True).execute()

        resp = await asyncio.to_thread(fetch_codes)
        return {"codes": resp.data or []}
    except Exception as exc:
        logger.error(f"Admin fetch codes failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve access codes.",
        )


@router.post("/admin/codes")
@limiter.limit("10/minute")
async def generate_admin_codes(
    request: Request,
    req: GenerateCodeRequest,
    admin: dict = Depends(verify_admin_role),
):
    """Generate dynamic randomized access codes (Admin only)."""
    from backend.db.supabase_client import get_supabase_client
    client = get_supabase_client(use_service_role=True)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable.",
        )

    role = req.role.strip()
    count = max(1, min(100, req.count))
    generated = []

    for _ in range(count):
        code = generate_random_code(role)
        generated.append({
            "code": code,
            "is_active": True,
            "role": role,
        })

    try:
        def insert_codes():
            return client.table("numeris_access_codes").insert(generated).execute()

        await asyncio.to_thread(insert_codes)
        logger.info(f"Admin {admin['sub']} generated {count} access codes for role {role}")
        return {"status": "success", "codes": generated}
    except Exception as exc:
        logger.error(f"Admin generate access codes failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store generated access codes.",
        )


@router.put("/admin/codes/revoke")
@limiter.limit("20/minute")
async def revoke_admin_code(
    request: Request,
    req: RevokeCodeRequest,
    admin: dict = Depends(verify_admin_role),
):
    """Revoke or restore access codes (Admin only)."""
    from backend.db.supabase_client import get_supabase_client
    client = get_supabase_client(use_service_role=True)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable.",
        )

    code = req.code.strip()
    try:
        def update_code():
            return client.table("numeris_access_codes").update({"is_active": req.is_active}).eq("code", code).execute()

        resp = await asyncio.to_thread(update_code)
        if not resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Access code not found.",
            )
        logger.info(f"Admin {admin['sub']} updated code {code} active status to {req.is_active}")
        return {"status": "success", "code": code, "is_active": req.is_active}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Admin code status update failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update access code status.",
        )
