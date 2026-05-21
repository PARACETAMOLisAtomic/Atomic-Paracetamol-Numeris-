"""
SQLAlchemy ORM models for Numeris.
All 8 tables: users, portfolios, watchlists, analysis_history,
market_data_cache, sentiment_cache, chat_sessions, api_usage.
Numeris v3.0
"""

from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import Any, Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, Float, ForeignKey,
    Index, Integer, JSON, String, Text, UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from backend.db.database import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _new_uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------
class User(Base):
    """Registered users of Numeris."""

    __tablename__ = "users"

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    username: str = Column(String(50), unique=True, nullable=False, index=True)
    email: str = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password: str = Column(String(255), nullable=False)
    risk_profile: str = Column(
        Enum("conservative", "moderate", "aggressive", name="risk_profile_enum"),
        default="moderate",
        nullable=False,
    )
    created_at: datetime = Column(DateTime, default=_now, nullable=False)
    last_login: Optional[datetime] = Column(DateTime, nullable=True)
    preferences_json: Optional[dict] = Column(JSON, nullable=True)
    is_active: bool = Column(Boolean, default=True, nullable=False)

    # Relation
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    analysis_history = relationship("AnalysisHistory", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "risk_profile": self.risk_profile,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "preferences_json": self.preferences_json,
            "is_active": self.is_active,
        }


# ---------------------------------------------------------------------------
# portfolios
# ---------------------------------------------------------------------------
class Portfolio(Base):
    """User's investment portfolios linked to brokers."""

    __tablename__ = "portfolios"

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    user_id: str = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    broker: str = Column(
        Enum("zerodha", "angel_one", "icici_direct", "manual", name="broker_enum"),
        nullable=False,
    )
    holdings_encrypted: str = Column(Text, nullable=False)  # Fernet encrypted JSON
    last_synced: Optional[datetime] = Column(DateTime, nullable=True)
    is_connected: bool = Column(Boolean, default=False, nullable=False)
    connection_error: Optional[str] = Column(String(500), nullable=True)

    # Relation
    user = relationship("User", back_populates="portfolios")

    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, user_id={self.user_id}, broker={self.broker})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "broker": self.broker,
            "holdings_encrypted": self.holdings_encrypted,
            "last_synced": self.last_synced.isoformat() if self.last_synced else None,
            "is_connected": self.is_connected,
            "connection_error": self.connection_error,
        }


# ---------------------------------------------------------------------------
# watchlists
# ---------------------------------------------------------------------------
class Watchlist(Base):
    """User's watchlists of stocks."""

    __tablename__ = "watchlists"

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    user_id: str = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: str = Column(String(100), nullable=False)
    stock_symbols_json: str = Column(JSON, nullable=False)  # list of symbol strings
    alerts_config_json: str = Column(JSON, nullable=False)  # dict of {symbol: {price_above, price_below, signal_change}}
    created_at: datetime = Column(DateTime, default=_now, nullable=False)
    updated_at: datetime = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    # Relation
    user = relationship("User", back_populates="watchlists")

    def __repr__(self) -> str:
        return f"<Watchlist(id={self.id}, user_id={self.user_id}, name={self.name})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "stock_symbols_json": self.stock_symbols_json,
            "alerts_config_json": self.alerts_config_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ---------------------------------------------------------------------------
# analysis_history
# ---------------------------------------------------------------------------
class AnalysisHistory(Base):
    """History of user's stock analyses."""

    __tablename__ = "analysis_history"

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    user_id: str = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    query: str = Column(Text, nullable=False)
    symbol: Optional[str] = Column(String(20), nullable=True)
    response_summary: Optional[str] = Column(Text, nullable=True)
    agents_used: str = Column(JSON, nullable=False)  # list of agent names
    confidence_score: Optional[float] = Column(Float, nullable=True)
    recommendation: Optional[str] = Column(Enum("BUY", "SELL", "HOLD", name="recommendation_enum"), nullable=True)
    full_response_path: Optional[str] = Column(String(500), nullable=True)  # path to JSON file with full response
    processing_time_ms: Optional[int] = Column(Integer, nullable=True)
    created_at: datetime = Column(DateTime, default=_now, nullable=False)

    # Relation
    user = relationship("User", back_populates="analysis_history")

    def __repr__(self) -> str:
        return f"<AnalysisHistory(id={self.id}, user_id={self.user_id}, symbol={self.symbol})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "query": self.query,
            "symbol": self.symbol,
            "response_summary": self.response_summary,
            "agents_used": self.agents_used,
            "confidence_score": self.confidence_score,
            "recommendation": self.recommendation,
            "full_response_path": self.full_response_path,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# market_data_cache
# ---------------------------------------------------------------------------
class MarketDataCache(Base):
    """Cached market data (OHLCV, etc.)"""

    __tablename__ = "market_data_cache"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    cache_key: str = Column(String(255), unique=True, nullable=False, index=True)
    symbol: Optional[str] = Column(String(20), nullable=True, index=True)
    exchange: Optional[str] = Column(String(10), nullable=True, index=True)
    interval: Optional[str] = Column(String(10), nullable=True, index=True)
    data_json: str = Column(Text, nullable=False)
    expires_at: datetime = Column(DateTime, nullable=False, index=True)
    created_at: datetime = Column(DateTime, default=_now, nullable=False)

    def __repr__(self) -> str:
        return f"<MarketDataCache(id={self.id}, cache_key={self.cache_key}, symbol={self.symbol})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cache_key": self.cache_key,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "interval": self.interval,
            "data_json": self.data_json,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# sentiment_cache
# ---------------------------------------------------------------------------
class SentimentCache(Base):
    """Cached sentiment data"""

    __tablename__ = "sentiment_cache"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    source: str = Column(String(50), nullable=False, index=True)
    topic: str = Column(String(100), nullable=False, index=True)
    score: float = Column(Float, nullable=False)
    themes_json: Optional[str] = Column(JSON, nullable=True)
    raw_data_path: Optional[str] = Column(String(500), nullable=True)
    created_at: datetime = Column(DateTime, default=_now, nullable=False)
    expires_at: datetime = Column(DateTime, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<SentimentCache(id={self.id}, source={self.source}, topic={self.topic}, score={self.score})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "topic": self.topic,
            "score": self.score,
            "themes_json": self.themes_json,
            "raw_data_path": self.raw_data_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


# ---------------------------------------------------------------------------
# chat_sessions
# ---------------------------------------------------------------------------
class ChatSession(Base):
    """User's chat sessions"""

    __tablename__ = "chat_sessions"

    id: str = Column(String(36), primary_key=True, default=_new_uuid)
    user_id: str = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_name: Optional[str] = Column(String(200), nullable=True)
    created_at: datetime = Column(DateTime, default=_now, nullable=False)
    last_active: datetime = Column(DateTime, default=_now, onupdate=_now, nullable=False)
    message_count: int = Column(Integer, default=0, nullable=False)
    metadata_json: Optional[str] = Column(JSON, nullable=True)

    # Relation
    user = relationship("User", back_populates="chat_sessions")

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, session_name={self.session_name})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_name": self.session_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "message_count": self.message_count,
            "metadata_json": self.metadata_json,
        }


# ---------------------------------------------------------------------------
# api_usage
# ---------------------------------------------------------------------------
class ApiUsage(Base):
    """Track API usage per provider per day"""

    __tablename__ = "api_usage"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    provider: str = Column(String(50), nullable=False, index=True)
    date: date = Column(Date, nullable=False, index=True)
    call_count: int = Column(Integer, default=0, nullable=False)
    token_count: int = Column(Integer, default=0, nullable=False)
    error_count: int = Column(Integer, default=0, nullable=False)

    __table_args__ = (UniqueConstraint('provider', 'date', name='_provider_date_uc'),)

    def __repr__(self) -> str:
        return f"<ApiUsage(id={self.id}, provider={self.provider}, date={self.date}, call_count={self.call_count})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "date": self.date.isoformat() if self.date else None,
            "call_count": self.call_count,
            "token_count": self.token_count,
            "error_count": self.error_count,
        }


# ---------------------------------------------------------------------------
# Indexes for query performance (in addition to those defined above)
# ---------------------------------------------------------------------------
# Note: Some indexes are already defined via index=True in Columns.
# Additional composite indexes can be added here if needed.
# For example:
# Index('idx_user_symbol', AnalysisHistory.user_id, AnalysisHistory.symbol)
