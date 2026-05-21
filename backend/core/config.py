"""
Pydantic settings for Numeris.
Loads environment variables from .env and provides validation.
Numeris v3.0
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    # -----------------------------------------------------------------------
    # Core AI model API keys (REQUIRED)
    # -----------------------------------------------------------------------
    GROQ_API_KEY: str
    MISTRAL_API_KEY: str
    DEEPSEEK_API_KEY: str

    # -----------------------------------------------------------------------
    # Financial & news data (REQUIRED)
    # -----------------------------------------------------------------------
    ALPHA_VANTAGE_KEY: str
    NEWS_API_KEY: str

    # -----------------------------------------------------------------------
    # Supabase (REQUIRED for cloud persistence; in-memory fallback exists)
    # -----------------------------------------------------------------------
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""   # needed by Supabase admin operations
    SUPABASE_JWT_SECRET: str = ""         # used to verify Supabase Auth access tokens

    # -----------------------------------------------------------------------
    # Security (REQUIRED)
    # -----------------------------------------------------------------------
    ENCRYPTION_SECRET_KEY: str
    APP_SECRET_KEY: str

    # -----------------------------------------------------------------------
    # Broker credentials (OPTIONAL – leave empty to skip broker connectivity)
    # -----------------------------------------------------------------------
    HUGGINGFACE_TOKEN: str = ""
    ZERODHA_API_KEY: str = ""
    ZERODHA_API_SECRET: str = ""
    ANGEL_ONE_KEY: str = ""
    ANGEL_ONE_SECRET: str = ""
    ICICI_DIRECT_KEY: str = ""
    ICICI_DIRECT_SECRET: str = ""

    # -----------------------------------------------------------------------
    # Reddit (OPTIONAL – used for sentiment analysis)
    # -----------------------------------------------------------------------
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "NumerisBot/1.0"

    # -----------------------------------------------------------------------
    # MiroFish (OPTIONAL)
    # -----------------------------------------------------------------------
    MIROFISH_LLM_API_KEY: str = ""
    MIROFISH_LLM_BASE_URL: str = "https://api.deepseek.com"
    MIROFISH_LLM_MODEL_NAME: str = "deepseek-chat"
    MIROFISH_ZEP_API_KEY: str = ""

    # -----------------------------------------------------------------------
    # WorldMonitor (OPTIONAL)
    # -----------------------------------------------------------------------
    WORLDMONITOR_GROQ_API_KEY: str = ""
    WORLDMONITOR_FINNHUB_API_KEY: str = ""
    WORLDMONITOR_FRED_API_KEY: str = ""
    WORLDMONITOR_EIA_API_KEY: str = ""

    # -----------------------------------------------------------------------
    # Infrastructure
    # -----------------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379"
    CHROMA_PERSIST_DIR: str = "./data_cache/chroma"
    SQLITE_DB_PATH: str = "./data_cache/numeris.db"
    PARQUET_CACHE_DIR: str = "./data_cache/parquet"
    LOCAL_MODEL_PATH: str = "./models/Phi-3-mini-4k-instruct-q4.gguf"

    # -----------------------------------------------------------------------
    # Application
    # -----------------------------------------------------------------------
    APP_ENV: str = "development"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    JWT_EXPIRE_HOURS: int = 24
    MAX_ANALYSES_PER_DAY: int = 100
    CHROMA_MAX_GB: float = 10.0
    PARQUET_MAX_GB: float = 8.0
    SQLITE_MAX_GB: float = 3.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",          # ignore unknown env vars (e.g. PATH, SYSTEMROOT)
    )

    # -----------------------------------------------------------------------
    # Validators — only truly required keys are checked
    # -----------------------------------------------------------------------
    @field_validator(
        'GROQ_API_KEY', 'MISTRAL_API_KEY', 'DEEPSEEK_API_KEY',
        'ALPHA_VANTAGE_KEY', 'NEWS_API_KEY',
        'ENCRYPTION_SECRET_KEY', 'APP_SECRET_KEY',
        mode='before',
    )
    @classmethod
    def not_empty_or_placeholder(cls, v, info):
        """Ensure truly critical fields are not empty or placeholder values."""
        if not v or str(v).strip() == "":
            raise ValueError(f"Required field cannot be empty")
        placeholders = {"your_key_here", "your_api_key", "changeme", "test", "none", "null"}
        if str(v).lower() in placeholders:
            raise ValueError(f"Field appears to be a placeholder value")
        return v

    # -----------------------------------------------------------------------
    # Convenience helpers
    # -----------------------------------------------------------------------
    def is_broker_configured(self, broker: str) -> bool:
        """Return True if a broker's key pair is fully configured."""
        pairs = {
            "zerodha":     (self.ZERODHA_API_KEY,    self.ZERODHA_API_SECRET),
            "angel_one":   (self.ANGEL_ONE_KEY,      self.ANGEL_ONE_SECRET),
            "icici_direct":(self.ICICI_DIRECT_KEY,   self.ICICI_DIRECT_SECRET),
        }
        k, s = pairs.get(broker, ("", ""))
        return bool(k and s)

    def is_reddit_configured(self) -> bool:
        return bool(self.REDDIT_CLIENT_ID and self.REDDIT_CLIENT_SECRET)

    def is_supabase_configured(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_ANON_KEY)

    def validate_critical_keys(self) -> None:
        """Validate that the hardest-required keys are present (called on startup)."""
        for key in ('GROQ_API_KEY', 'ENCRYPTION_SECRET_KEY', 'APP_SECRET_KEY'):
            value = getattr(self, key, None)
            if not value or str(value).strip() == "":
                raise ValueError(f"Critical key {key} is missing or empty")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
settings = Settings()

try:
    settings.validate_critical_keys()
except ValueError as e:
    import logging
    logging.warning(f"Numeris configuration warning: {e}")
