import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.utils.logger import get_logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.core.limiter import limiter

from backend.api.auth_routes import router as auth_router
from backend.api.analysis_routes import router as analysis_router
from backend.api.chat_routes import router as chat_router
from backend.api.portfolio_routes import router as portfolio_router
from backend.api.market_routes import router as market_router
from backend.api.voice_routes import router as voice_router
from backend.api.numeris_routes import router as numeris_router

logger = get_logger(__name__)

async def bootstrap_access_system():
    from backend.db.supabase_client import get_supabase_client
    import asyncio
    client = get_supabase_client(use_service_role=True)
    if client is None:
        logger.info("Supabase not configured, skipping access code system bootstrap")
        return

    try:
        def check_empty():
            return client.table("numeris_access_codes").select("*").limit(1).execute()
        response = await asyncio.to_thread(check_empty)
        if not response.data:
            from backend.api.auth_routes import generate_random_code
            admin_code = generate_random_code("admin")
            def insert_code():
                return client.table("numeris_access_codes").insert({
                    "code": admin_code,
                    "is_active": True,
                    "role": "admin"
                }).execute()
            await asyncio.to_thread(insert_code)
            logger.warning("=" * 60)
            logger.warning(f"🔑 BOOTSTRAP: Created first Admin Invite Code: {admin_code}")
            logger.warning("Use this code to register your admin account on first login.")
            logger.warning("=" * 60)
    except Exception as exc:
        logger.warning(f"Failed to bootstrap access codes: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    logger.info("Starting up Numeris backend...")
    os.makedirs("./data_cache", exist_ok=True)
    
    # Initialize SQLite database
    try:
        from backend.db.database import init_db
        await init_db()
    except Exception as exc:
        logger.error(f"Failed to initialize SQLite database: {exc}")
        
    # Bootstrap private access system
    await bootstrap_access_system()
    
    # Start periodic tasks scheduler
    scheduler_task = asyncio.create_task(run_periodic_tasks())
    
    yield
    logger.info("Shutting down Numeris backend...")
    scheduler_task.cancel()

app = FastAPI(title="Numeris API", version="3.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins = list(settings.CORS_ORIGINS) + [
    "http://localhost:5173",   # Vite dev server (Frontend 2.0)
    "http://localhost:4173",   # Vite preview
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    duration = int((time.time() - start_time) * 1000)
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration}ms")
    
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if "x-powered-by" in response.headers:
        del response.headers["x-powered-by"]
        
    return response

app.include_router(auth_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(portfolio_router, prefix="/api")
app.include_router(market_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(numeris_router, prefix="/api")

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "platform": "Numeris",
        "services": {
            "db": "connected",
            "chroma": "connected",
            "model_router": "connected"
        }
    }

@app.get("/api/status")
async def api_status():
    return {"status": "ok", "platform": "Numeris", "api_usage": {}}

async def run_periodic_tasks():
    import asyncio
    from backend.data.market_data import update_parquet_cache
    from backend.utils.cache import invalidate_cache
    from backend.db.chroma_init import delete_old_embeddings
    
    async def run_market_data_update():
        try:
            logger.info("Scheduled task: update_market_data starting")
            await update_parquet_cache()
            logger.info("Scheduled task: update_market_data completed")
        except Exception as e:
            logger.error(f"Scheduled task update_market_data failed: {e}")

    async def run_cleanup():
        try:
            logger.info("Scheduled task: cleanup_cache starting")
            # Run sync cache purge in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: invalidate_cache("__expired__"))
            
            collections = ["stock_embeddings", "news_embeddings", "sentiment_embeddings",
                           "user_query_memory", "chat_memory"]
            for col in collections:
                await delete_old_embeddings(col, days_old=60)
            logger.info("Scheduled task: cleanup_cache completed")
        except Exception as e:
            logger.error(f"Scheduled task cleanup_cache failed: {e}")

    async def run_check_alerts():
        try:
            logger.info("Scheduled task: check_alerts starting")
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
                            logger.debug(f"Alert check failed for symbol {symbol}: {exc}")
            logger.info("Scheduled task: check_alerts completed")
        except Exception as e:
            logger.error(f"Scheduled task check_alerts failed: {e}")

    logger.info("Background periodic tasks scheduler started")
    count = 0
    while True:
        try:
            # Check alerts every 5 minutes
            if count % 5 == 0:
                asyncio.create_task(run_check_alerts())
            # Update market data every 30 minutes
            if count % 30 == 0:
                asyncio.create_task(run_market_data_update())
            # Clean up cache every 24 hours (1440 minutes)
            if count % 1440 == 0:
                asyncio.create_task(run_cleanup())
                
            count += 1
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic task scheduler loop: {e}")
            await asyncio.sleep(60)
