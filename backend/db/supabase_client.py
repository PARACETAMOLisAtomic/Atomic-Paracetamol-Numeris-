"""
Supabase client helpers for Numeris.

Service-role access is used only inside the FastAPI backend. Browser clients
must use Supabase Auth with the anon key and send the resulting access token.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from backend.core.config import settings
from backend.utils.logger import get_logger

logger = get_logger("supabase_client")

_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None
_manual_portfolio_fallback: Dict[str, List[Dict[str, Any]]] = {}


def get_supabase_client(use_service_role: bool = False) -> Optional[Client]:
    """Return a cached Supabase client, or None when Supabase is not configured."""
    global _supabase_client, _supabase_admin_client

    if use_service_role and _supabase_admin_client is not None:
        return _supabase_admin_client
    if not use_service_role and _supabase_client is not None:
        return _supabase_client

    supabase_url = settings.SUPABASE_URL
    supabase_key = settings.SUPABASE_SERVICE_ROLE_KEY if use_service_role else settings.SUPABASE_ANON_KEY
    if use_service_role and not supabase_key:
        supabase_key = settings.SUPABASE_ANON_KEY

    if not supabase_url or not supabase_key:
        logger.warning("Supabase URL or key is not configured")
        return None

    try:
        client = create_client(supabase_url, supabase_key)
        if use_service_role:
            _supabase_admin_client = client
            logger.info("Supabase admin client initialized")
            return _supabase_admin_client
        _supabase_client = client
        logger.info("Supabase anon client initialized")
        return _supabase_client
    except Exception as exc:
        logger.error("Failed to initialize Supabase client", extra={"error": str(exc)})
        return None


async def sync_analysis_history(user_id: str, records: List[Dict[str, Any]]) -> bool:
    client = get_supabase_client(use_service_role=True)
    if client is None:
        logger.warning("Supabase unavailable, skipping analysis history sync")
        return False

    try:
        prepared = [{**record, "user_id": user_id} for record in records]
        if prepared:
            client.table("numeris_analysis_history").upsert(prepared).execute()
        logger.info("Synced analysis history", extra={"user_id": user_id, "count": len(prepared)})
        return True
    except Exception as exc:
        logger.error("Failed to sync analysis history", extra={"user_id": user_id, "error": str(exc)})
        return False


async def backup_user_data(user_id: str, data: Dict[str, Any]) -> bool:
    client = get_supabase_client(use_service_role=True)
    if client is None:
        logger.warning("Supabase unavailable, skipping user backup")
        return False

    try:
        client.table("numeris_user_backups").insert({"user_id": user_id, "data": data}).execute()
        return True
    except Exception as exc:
        logger.error("Failed to back up user data", extra={"user_id": user_id, "error": str(exc)})
        return False


async def fetch_shared_cache(symbol: str, data_type: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client(use_service_role=True)
    if client is None:
        return None

    try:
        response = (
            client.table("numeris_shared_cache")
            .select("data")
            .eq("symbol", symbol.upper())
            .eq("data_type", data_type)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0].get("data")
    except Exception as exc:
        logger.debug("Shared cache read failed", extra={"symbol": symbol, "data_type": data_type, "error": str(exc)})
    return None


async def store_shared_cache(symbol: str, data_type: str, data: Dict[str, Any]) -> bool:
    client = get_supabase_client(use_service_role=True)
    if client is None:
        return False

    try:
        client.table("numeris_shared_cache").insert(
            {"symbol": symbol.upper(), "data_type": data_type, "data": data}
        ).execute()
        return True
    except Exception as exc:
        logger.debug("Shared cache write failed", extra={"symbol": symbol, "data_type": data_type, "error": str(exc)})
        return False


async def get_manual_holdings(user_id: str) -> List[Dict[str, Any]]:
    client = get_supabase_client(use_service_role=True)
    if client is None:
        return list(_manual_portfolio_fallback.get(user_id, []))

    try:
        response = (
            client.table("numeris_manual_portfolio")
            .select("*")
            .eq("user_id", user_id)
            .order("symbol")
            .execute()
        )
        return response.data or []
    except Exception as exc:
        logger.error("Failed to fetch manual holdings", extra={"user_id": user_id, "error": str(exc)})
        return list(_manual_portfolio_fallback.get(user_id, []))


async def add_manual_holding(user_id: str, symbol: str, quantity: float, buy_price: float) -> bool:
    normalized_symbol = symbol.upper().strip()
    client = get_supabase_client(use_service_role=True)
    if client is None:
        holdings = _manual_portfolio_fallback.setdefault(user_id, [])
        holdings[:] = [row for row in holdings if row["symbol"] != normalized_symbol]
        holdings.append(
            {"user_id": user_id, "symbol": normalized_symbol, "quantity": quantity, "avg_price": buy_price}
        )
        return True

    try:
        client.table("numeris_manual_portfolio").upsert(
            {
                "user_id": user_id,
                "symbol": normalized_symbol,
                "quantity": quantity,
                "avg_price": buy_price,
            },
            on_conflict="user_id,symbol",
        ).execute()
        return True
    except Exception as exc:
        logger.error("Failed to add manual holding", extra={"user_id": user_id, "symbol": normalized_symbol, "error": str(exc)})
        return False


async def delete_manual_holding(user_id: str, symbol: str) -> bool:
    normalized_symbol = symbol.upper().strip()
    client = get_supabase_client(use_service_role=True)
    if client is None:
        holdings = _manual_portfolio_fallback.setdefault(user_id, [])
        holdings[:] = [row for row in holdings if row["symbol"] != normalized_symbol]
        return True

    try:
        client.table("numeris_manual_portfolio").delete().eq("user_id", user_id).eq("symbol", normalized_symbol).execute()
        return True
    except Exception as exc:
        logger.error("Failed to delete manual holding", extra={"user_id": user_id, "symbol": normalized_symbol, "error": str(exc)})
        return False
