import hashlib
import json
import os
import sqlite3
import time
import random
from functools import wraps
from typing import Any, Callable, Optional, TypeVar
import redis.asyncio as redis
from backend.utils.logger import get_logger

logger = get_logger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def sqlite_cache(ttl_seconds: int = 3600, table: str = "market_data_cache", key_prefix: str = "") -> Callable[[F], F]:
    """
    Create a sqlite_cache decorator:
    @sqlite_cache(ttl_seconds=3600, table="market_data_cache", key_prefix="")
    Generates cache key from function name + arguments (use hashlib.md5)
    Checks SQLite market_data_cache table before calling the function
    Stores result as JSON with expiry timestamp
    Auto-purges expired entries on each cache miss (max 100 purges per hour to avoid spam)
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name + arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            key_string = "|".join(key_parts)
            cache_key = hashlib.md5(key_string.encode()).hexdigest()

            # Auto-purge expired entries (max 100 purges per hour)
            if not hasattr(wrapper, '_purge_count'):
                wrapper._purge_count = 0
                wrapper._last_purge = time.time()

            now = time.time()
            if now - wrapper._last_purge > 3600:  # Reset hourly
                wrapper._purge_count = 0
                wrapper._last_purge = now

            if wrapper._purge_count < 100:  # Max 100 purges per hour
                try:
                    _purge_expired_cache(table)
                    wrapper._purge_count += 1
                except Exception:
                    pass  # Continue even if purge fails

            # Check SQLite cache
            try:
                db_path = os.getenv("SQLITE_DB_PATH", "./data_cache/numeris.db")
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Create table if not exists
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        cache_key TEXT PRIMARY KEY,
                        symbol TEXT,
                        exchange TEXT,
                        interval TEXT,
                        data_json TEXT NOT NULL,
                        expires_at REAL NOT NULL,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """)

                # Check if valid cache entry exists
                cursor.execute(
                    f"SELECT data_json FROM {table} WHERE cache_key = ? AND expires_at > ?",
                    (cache_key, time.time())
                )
                row = cursor.fetchone()
                if row:
                    data_json = row[0]
                    logger.debug(f"SQLite cache hit for {func.__name__}")
                    return json.loads(data_json)

                conn.close()
            except Exception as e:
                logger.warning(f"SQLite cache error for {func.__name__}: {e}")
                # Continue to function call if cache fails

            # Call the function
            result = func(*args, **kwargs)

            # Store result in cache
            try:
                db_path = os.getenv("SQLITE_DB_PATH", "./data_cache/numeris.db")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                data_json = json.dumps(result, default=str)
                expires_at = time.time() + ttl_seconds

                cursor.execute(
                    f"""
                    INSERT OR REPLACE INTO {table}
                    (cache_key, symbol, exchange, interval, data_json, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cache_key,
                        kwargs.get('symbol', None),
                        kwargs.get('exchange', None),
                        kwargs.get('interval', None),
                        data_json,
                        expires_at
                    )
                )
                conn.commit()
                conn.close()

                logger.debug(f"Stored in SQLite cache for {func.__name__}")
            except Exception as e:
                logger.warning(f"Failed to store in SQLite cache for {func.__name__}: {e}")

            return result
        return wrapper  # type: ignore
    return decorator


def async_sqlite_cache(ttl_seconds: int = 3600, table: str = "market_data_cache", key_prefix: str = "") -> Callable[[F], F]:
    """
    Create async_sqlite_cache for async functions
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name + arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            key_string = "|".join(key_parts)
            cache_key = hashlib.md5(key_string.encode()).hexdigest()

            # Auto-purge expired entries (max 100 purges per hour)
            if not hasattr(wrapper, '_purge_count'):
                wrapper._purge_count = 0
                wrapper._last_purge = time.time()

            now = time.time()
            if now - wrapper._last_purge > 3600:  # Reset hourly
                wrapper._purge_count = 0
                wrapper._last_purge = now

            if wrapper._purge_count < 100:  # Max 100 purges per hour
                try:
                    _purge_expired_cache(table)
                    wrapper._purge_count += 1
                except Exception:
                    pass  # Continue even if purge fails

            # Check SQLite cache
            try:
                db_path = os.getenv("SQLITE_DB_PATH", "./data_cache/numeris.db")
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Create table if not exists
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        cache_key TEXT PRIMARY KEY,
                        symbol TEXT,
                        exchange TEXT,
                        interval TEXT,
                        data_json TEXT NOT NULL,
                        expires_at REAL NOT NULL,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                """)

                # Check if valid cache entry exists
                cursor.execute(
                    f"SELECT data_json FROM {table} WHERE cache_key = ? AND expires_at > ?",
                    (cache_key, time.time())
                )
                row = cursor.fetchone()
                if row:
                    data_json = row[0]
                    logger.debug(f"Async SQLite cache hit for {func.__name__}")
                    return json.loads(data_json)

                conn.close()
            except Exception as e:
                logger.warning(f"Async SQLite cache error for {func.__name__}: {e}")
                # Continue to function call if cache fails

            # Call the function
            result = await func(*args, **kwargs)

            # Store result in cache
            try:
                db_path = os.getenv("SQLITE_DB_PATH", "./data_cache/numeris.db")
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                data_json = json.dumps(result, default=str)
                expires_at = time.time() + ttl_seconds

                cursor.execute(
                    f"""
                    INSERT OR REPLACE INTO {table}
                    (cache_key, symbol, exchange, interval, data_json, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        cache_key,
                        kwargs.get('symbol', None),
                        kwargs.get('exchange', None),
                        kwargs.get('interval', None),
                        data_json,
                        expires_at
                    )
                )
                conn.commit()
                conn.close()

                logger.debug(f"Stored in async SQLite cache for {func.__name__}")
            except Exception as e:
                logger.warning(f"Failed to store in async SQLite cache for {func.__name__}: {e}")

            return result
        return wrapper  # type: ignore
    return decorator


def redis_cache(ttl_seconds: int = 3600, key_prefix: str = "") -> Callable[[F], F]:
    """
    Create redis_cache decorator that uses Redis for hot data (TTL in seconds)
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name + arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            key_string = "|".join(key_parts)
            cache_key = hashlib.md5(key_string.encode()).hexdigest()

            # Try to get from Redis
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                r = redis.from_url(redis_url)
                cached = r.get(cache_key)
                if cached is not None:
                    logger.debug(f"Redis cache hit for {func.__name__}")
                    return json.loads(cached)

                r.close()
            except Exception as e:
                logger.warning(f"Redis unavailable for {func.__name__}: {e}")
                # Continue to function call if Redis fails

            # Call the function
            result = func(*args, **kwargs)

            # Store in Redis
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                r = redis.from_url(redis_url)
                data_json = json.dumps(result, default=str)
                r.setex(cache_key, ttl_seconds, data_json)
                r.close()
                logger.debug(f"Stored in Redis cache for {func.__name__}")
            except Exception as e:
                logger.warning(f"Failed to store in Redis cache for {func.__name__}: {e}")

            return result
        return wrapper  # type: ignore
    return decorator


def invalidate_cache(key_pattern: str, table: str = "market_data_cache") -> None:
    """
    Create invalidate_cache(key_pattern: str) to clear matching cache entries
    """
    try:
        db_path = os.getenv("SQLITE_DB_PATH", "./data_cache/numeris.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Delete matching cache entries
        cursor.execute(f"DELETE FROM {table} WHERE cache_key LIKE ?", (f"%{key_pattern}%",))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Invalidated {deleted} cache entries matching pattern '{key_pattern}' from {table}")
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")


def _purge_expired_cache(table: str = "market_data_cache") -> None:
    """
    Internal function to purge expired entries from cache table
    """
    try:
        db_path = os.getenv("SQLITE_DB_PATH", "./data_cache/numeris.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(f"DELETE FROM {table} WHERE expires_at < ?", (time.time(),))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        if deleted > 0:
            logger.debug(f"Purged {deleted} expired entries from {table}")
    except Exception as e:
        logger.warning(f"Error purging expired cache: {e}")
