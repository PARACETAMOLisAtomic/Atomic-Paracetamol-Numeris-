"""
Security utilities for Numeris.
- Fernet AES-256 encryption/decryption for broker credentials
- Supabase Auth JWT validation
- Per-user rate limiting (Redis-optional, SQLite fallback)
- FastAPI dependency: get_current_user
Numeris v3.0
"""

from __future__ import annotations

import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from backend.core.config import settings
from backend.utils.logger import get_logger

logger = get_logger("security")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/supabase", auto_error=False)


# ---------------------------------------------------------------------------
# SecurityManager
# ---------------------------------------------------------------------------
class SecurityManager:
    """Central security utilities: encryption, hashing, JWT, rate limiting."""

    def __init__(self) -> None:
        self._fernet: Any = None
        self._fernet_key: Optional[bytes] = None

    # ------------------------------------------------------------------
    # Fernet encryption
    # ------------------------------------------------------------------
    def _get_fernet(self) -> Any:
        if self._fernet is not None:
            return self._fernet
        try:
            from cryptography.fernet import Fernet  # type: ignore[import]
            key_str = settings.ENCRYPTION_SECRET_KEY
            if not key_str:
                raise ValueError("ENCRYPTION_SECRET_KEY is not set")
            # Accept raw key or base64-encoded key
            key_bytes = key_str.encode() if isinstance(key_str, str) else key_str
            self._fernet = Fernet(key_bytes)
            return self._fernet
        except Exception as exc:
            logger.error("Fernet init failed", extra={"error": str(exc)})
            raise

    def encrypt(self, data: str) -> str:
        """Encrypt *data* using Fernet (AES-256-CBC + HMAC).

        Parameters
        ----------
        data:
            Plaintext string to encrypt.

        Returns
        -------
        str
            URL-safe base64-encoded ciphertext.
        """
        fernet = self._get_fernet()
        return fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        """Decrypt a Fernet *token* back to plaintext.

        Parameters
        ----------
        token:
            Fernet-encrypted ciphertext string.

        Returns
        -------
        str
            Decrypted plaintext.

        Raises
        ------
        ValueError
            If the token is invalid or the key is wrong.
        """
        try:
            fernet = self._get_fernet()
            return fernet.decrypt(token.encode()).decode()
        except Exception as exc:
            logger.warning("Fernet decryption failed", extra={"error": str(exc)})
            raise ValueError("Invalid encrypted token") from exc

    # ------------------------------------------------------------------
    # Password hashing (bcrypt)
    # ------------------------------------------------------------------
    def hash_password(self, password: str) -> str:
        """Hash *password* with bcrypt (12 rounds).

        Parameters
        ----------
        password:
            Plaintext password.

        Returns
        -------
        str
            bcrypt hash string.
        """
        from passlib.context import CryptContext  # type: ignore[import]
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
        return ctx.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verify *plain* against a stored bcrypt *hashed* value.

        Parameters
        ----------
        plain:
            Plaintext password provided by the user.
        hashed:
            Stored bcrypt hash.

        Returns
        -------
        bool
            ``True`` if the password matches.
        """
        try:
            from passlib.context import CryptContext  # type: ignore[import]
            ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return ctx.verify(plain, hashed)
        except Exception as exc:
            logger.warning("Password verify error", extra={"error": str(exc)})
            return False

    # ------------------------------------------------------------------
    # Supabase Auth JWT
    # ------------------------------------------------------------------
    def _jwt_encode(self, payload: Dict[str, Any]) -> str:
        from jose import jwt  # type: ignore[import]
        return jwt.encode(payload, settings.APP_SECRET_KEY, algorithm="HS256")

    def _jwt_decode(self, token: str) -> Dict[str, Any]:
        from jose import jwt, JWTError  # type: ignore[import]
        try:
            return jwt.decode(token, settings.APP_SECRET_KEY, algorithms=["HS256"])
        except JWTError as exc:
            raise ValueError(f"Invalid JWT: {exc}") from exc

    def create_jwt(self, user_id: str, username: str) -> str:
        """Create a JWT access token with 24-hour expiry.

        Parameters
        ----------
        user_id:
            UUID of the authenticated user.
        username:
            Username for display purposes.

        Returns
        -------
        str
            Signed JWT string.
        """
        expire = datetime.now(tz=timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
        payload = {
            "sub": user_id,
            "username": username,
            "exp": expire,
            "iat": datetime.now(tz=timezone.utc),
            "type": "access",
        }
        return self._jwt_encode(payload)

    def verify_jwt(self, token: str) -> Dict[str, Any]:
        """Decode and validate a JWT access token.

        Parameters
        ----------
        token:
            JWT string from the Authorization header.

        Returns
        -------
        dict
            Decoded payload containing ``sub`` (user_id) and ``username``.

        Raises
        ------
        HTTPException
            401 if the token is invalid or expired.
        """
        try:
            payload = self._jwt_decode(token)
            if payload.get("type") != "access":
                raise ValueError("Not an access token")
            return payload
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    async def verify_supabase_jwt(self, token: str) -> Dict[str, Any]:
        """Validate a Supabase Auth access token and normalize the user payload."""
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            if settings.SUPABASE_JWT_SECRET:
                from jose import jwt  # type: ignore[import]

                payload = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
                subject = payload.get("sub")
                if not subject:
                    raise ValueError("Supabase token missing subject")
                return {
                    "sub": subject,
                    "email": payload.get("email"),
                    "role": payload.get("role", "authenticated"),
                    "provider": "supabase",
                    "raw": payload,
                }

            from backend.db.supabase_client import get_supabase_client

            client = get_supabase_client(use_service_role=False)
            if client is None:
                raise ValueError("Supabase auth is not configured")
            user_response = await asyncio.to_thread(lambda: client.auth.get_user(token))
            user = getattr(user_response, "user", None)
            if user is None:
                raise ValueError("Supabase user not found")
            return {
                "sub": str(user.id),
                "email": getattr(user, "email", None),
                "role": "authenticated",
                "provider": "supabase",
                "raw": user_response,
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Supabase JWT validation failed", extra={"error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired Supabase token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

    def create_refresh_token(self, user_id: str) -> str:
        """Create a JWT refresh token with 30-day expiry.

        Parameters
        ----------
        user_id:
            UUID of the authenticated user.

        Returns
        -------
        str
            Signed refresh JWT string.
        """
        expire = datetime.now(tz=timezone.utc) + timedelta(days=30)
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.now(tz=timezone.utc),
            "type": "refresh",
        }
        return self._jwt_encode(payload)

    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """Validate a refresh token and return its payload.

        Parameters
        ----------
        token:
            Refresh JWT string.

        Returns
        -------
        dict
            Decoded payload with ``sub`` (user_id).

        Raises
        ------
        HTTPException
            401 if the token is invalid or expired.
        """
        try:
            payload = self._jwt_decode(token)
            if payload.get("type") != "refresh":
                raise ValueError("Not a refresh token")
            return payload
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
security = SecurityManager()


# ---------------------------------------------------------------------------
# Rate limiting (Redis-optional, SQLite fallback)
# ---------------------------------------------------------------------------
async def check_rate_limit(user_id: str) -> bool:
    """Check and increment the daily analysis counter for *user_id*.

    Uses Redis if available, otherwise falls back to an in-memory dict
    (resets on app restart — acceptable for single-user local deployments).

    Parameters
    ----------
    user_id:
        UUID of the user making the request.

    Returns
    -------
    bool
        ``True`` if the user is within limits, ``False`` if they have exceeded
        ``settings.MAX_ANALYSES_PER_DAY``.
    """
    from datetime import date

    key = f"rate_limit:{user_id}:{date.today()}"

    # ------------------------------------------------------------------
    # Try Redis first
    # ------------------------------------------------------------------
    try:
        import redis.asyncio as aioredis  # type: ignore[import]
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, 86400)
        await client.aclose()
        return count <= settings.MAX_ANALYSES_PER_DAY
    except Exception:
        pass  # Redis not available — use in-memory fallback

    # ------------------------------------------------------------------
    # In-memory fallback
    # ------------------------------------------------------------------
    _counts = _get_in_memory_counts()
    today_str = str(date.today())
    bucket = f"{user_id}:{today_str}"
    _counts[bucket] = _counts.get(bucket, 0) + 1
    return _counts[bucket] <= settings.MAX_ANALYSES_PER_DAY


# In-memory counter store (module-level, survives for the process lifetime)
_in_memory_counts: Dict[str, int] = {}


def _get_in_memory_counts() -> Dict[str, int]:
    return _in_memory_counts


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """FastAPI dependency: extract and validate the current user from the JWT."""
    return await security.verify_supabase_jwt(token or "")


async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[Dict[str, Any]]:
    """Like :func:`get_current_user` but returns ``None`` if no/invalid token."""
    if not token:
        return None
    try:
        return await security.verify_supabase_jwt(token)
    except HTTPException:
        return None


async def verify_access_unlocked(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """FastAPI dependency: ensure user has validated their private access code."""
    from backend.db.supabase_client import get_supabase_client
    client = get_supabase_client(use_service_role=True)
    if client is None:
        # Offline or local dev fallback (e.g. if Supabase is unconfigured)
        current_user["role"] = "admin"
        return current_user

    user_id = current_user["sub"]
    try:
        def check_access():
            return client.table("numeris_user_access").select("*").eq("user_id", user_id).execute()

        response = await asyncio.to_thread(check_access)
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access code required. Platform is locked.",
            )

        user_access = response.data[0]
        current_user["role"] = user_access.get("role", "standard_user")
        current_user["code"] = user_access.get("code")
        return current_user
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error checking user access for {user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database verification failure.",
        )


async def verify_admin_role(current_user: Dict[str, Any] = Depends(verify_access_unlocked)) -> Dict[str, Any]:
    """FastAPI dependency: ensure user has admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user
