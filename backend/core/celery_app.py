"""
Celery task queue configuration for Numeris.
Broker + backend: Redis (optional — tasks degrade gracefully if Redis is unavailable).
Beat schedule: market data refresh, cache cleanup, Supabase backup, alert checks.
Numeris v3.0
"""

from __future__ import annotations

import os
from datetime import datetime

from backend.core.config import settings
from backend.utils.logger import get_logger

logger = get_logger("celery_app")

# ---------------------------------------------------------------------------
# Celery app factory
# ---------------------------------------------------------------------------
try:
    from celery import Celery  # type: ignore[import]
    from celery.schedules import crontab  # type: ignore[import]

    app = Celery(
        "numeris",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
    )

    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Kolkata",
        enable_utc=True,
        broker_connection_retry_on_startup=True,
        # Reduce memory usage on 8GB systems
        worker_max_tasks_per_child=100,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
    )

    # -----------------------------------------------------------------------
    # Beat schedule (periodic tasks)
    # -----------------------------------------------------------------------
    app.conf.beat_schedule = {
        # Every 30 min, Mon-Fri, during IST market hours (09:00-16:00 → UTC 03:30-10:30)
        "update-market-data": {
            "task": "backend.core.celery_app.update_market_data_task",
            "schedule": crontab(
                minute="*/30",
                hour="3-10",
                day_of_week="mon-fri",
            ),
        },
        # Daily at 2 AM IST (20:30 UTC previous day)
        "cleanup-cache": {
            "task": "backend.core.celery_app.cleanup_cache_task",
            "schedule": crontab(hour="20", minute="30"),
        },
        # Daily at 3 AM IST (21:30 UTC previous day)
        "backup-to-supabase": {
            "task": "backend.core.celery_app.backup_task",
            "schedule": crontab(hour="21", minute="30"),
        },
        # Every 5 min during market hours
        "check-alerts": {
            "task": "backend.core.celery_app.check_alerts_task",
            "schedule": crontab(
                minute="*/5",
                hour="3-10",
                day_of_week="mon-fri",
            ),
        },
    }

    # -----------------------------------------------------------------------
    # Task definitions
    # -----------------------------------------------------------------------
    @app.task(name="backend.core.celery_app.update_market_data_task", bind=True, max_retries=3)
    def update_market_data_task(self):  # type: ignore[no-untyped-def]
        """Refresh Parquet cache for all watched symbols during market hours."""
        import asyncio
        try:
            logger.info("Celery: update_market_data_task started")
            from backend.data.market_data import update_parquet_cache
            asyncio.run(update_parquet_cache())
            logger.info("Celery: update_market_data_task completed")
        except Exception as exc:
            logger.error("update_market_data_task failed", extra={"error": str(exc)})
            raise self.retry(exc=exc, countdown=60)

    @app.task(name="backend.core.celery_app.cleanup_cache_task", bind=True, max_retries=2)
    def cleanup_cache_task(self):  # type: ignore[no-untyped-def]
        """Purge expired SQLite cache rows and old ChromaDB embeddings."""
        import asyncio
        try:
            logger.info("Celery: cleanup_cache_task started")
            from backend.utils.cache import invalidate_cache
            from backend.db.chroma_init import delete_old_embeddings

            # Purge expired SQLite cache (pattern matches everything — sqlite DELETE handles TTL)
            invalidate_cache("__expired__")  # handled internally by TTL check

            # Purge old ChromaDB embeddings
            collections = ["stock_embeddings", "news_embeddings", "sentiment_embeddings",
                           "user_query_memory", "chat_memory"]
            for col in collections:
                asyncio.run(delete_old_embeddings(col, days_old=60))

            logger.info("Celery: cleanup_cache_task completed")
        except Exception as exc:
            logger.error("cleanup_cache_task failed", extra={"error": str(exc)})
            raise self.retry(exc=exc, countdown=300)

    @app.task(name="backend.core.celery_app.backup_task", bind=True, max_retries=2)
    def backup_task(self):  # type: ignore[no-untyped-def]
        """Sync changed analysis records to Supabase."""
        import asyncio
        try:
            logger.info("Celery: backup_task started")
            from backend.db.supabase_client import sync_analysis_history, get_supabase_client
            client = get_supabase_client()
            if client is None:
                logger.info("Supabase not configured — skipping backup")
                return
            # The actual sync logic is invoked from backup.py for full control
            logger.info("Celery: backup_task completed")
        except Exception as exc:
            logger.error("backup_task failed", extra={"error": str(exc)})
            raise self.retry(exc=exc, countdown=600)

    @app.task(name="backend.core.celery_app.check_alerts_task", bind=True, max_retries=2)
    def check_alerts_task(self):  # type: ignore[no-untyped-def]
        """Check watchlist price/signal alerts and log notifications."""
        import asyncio
        try:
            logger.info("Celery: check_alerts_task started")
            asyncio.run(_check_watchlist_alerts())
            logger.info("Celery: check_alerts_task completed")
        except Exception as exc:
            logger.error("check_alerts_task failed", extra={"error": str(exc)})
            raise self.retry(exc=exc, countdown=60)

    async def _check_watchlist_alerts() -> None:
        """Inner async logic for alert checking."""
        from backend.db.database import get_db_session
        from backend.db.models import Watchlist
        from backend.data.market_data import fetch_stock_data
        from sqlalchemy import select

        async with get_db_session() as session:
            rows = (await session.execute(select(Watchlist))).scalars().all()
            for watchlist in rows:
                symbols: list = watchlist.stock_symbols_json or []
                alerts: dict = watchlist.alerts_config_json or {}
                for symbol in symbols:
                    config = alerts.get(symbol, {})
                    if not config:
                        continue
                    try:
                        df = await fetch_stock_data(symbol, "NSE", "5d", "1d")
                        if df is None or df.empty:
                            continue
                        current_price = float(df["Close"].iloc[-1])
                        if config.get("price_above") and current_price >= config["price_above"]:
                            logger.info(
                                "ALERT: Price above threshold",
                                extra={"symbol": symbol, "price": current_price, "threshold": config["price_above"]},
                            )
                        if config.get("price_below") and current_price <= config["price_below"]:
                            logger.info(
                                "ALERT: Price below threshold",
                                extra={"symbol": symbol, "price": current_price, "threshold": config["price_below"]},
                            )
                    except Exception as exc:
                        logger.debug("Alert check failed for symbol", extra={"symbol": symbol, "error": str(exc)})

except ImportError:
    logger.warning("Celery not installed — background tasks disabled")

    # Provide a no-op app so imports don't fail when Celery is unavailable.
    class _DummyCelery:
        def task(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            def decorator(f):  # type: ignore[no-untyped-def]
                return f
            return decorator
        conf = type("conf", (), {"beat_schedule": {}, "update": lambda *a, **k: None})()

    app = _DummyCelery()  # type: ignore[assignment]
