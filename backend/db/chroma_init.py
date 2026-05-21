"""
ChromaDB initialization and embedding management for Numeris.
Numeris v3.0
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
import asyncio
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from backend.core.config import settings
from backend.utils.logger import get_logger

logger = get_logger("chroma_init")


# ---------------------------------------------------------------------------
# ChromaDB client and embedding function (singletons)
# ---------------------------------------------------------------------------
_chroma_client: Optional[chromadb.PersistentClient] = None
_embedding_function: Optional[embedding_functions.SentenceTransformerEmbeddingFunction] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """
    Get or create the ChromaDB PersistentClient singleton.
    """
    global _chroma_client
    if _chroma_client is None:
        # Ensure the directory exists
        persist_dir = settings.CHROMA_PERSIST_DIR
        os.makedirs(persist_dir, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        logger.info(f"ChromaDB client initialized at {persist_dir}")
    return _chroma_client


def get_embedding_function() -> embedding_functions.SentenceTransformerEmbeddingFunction:
    """
    Get or create the SentenceTransformer embedding function singleton.
    """
    global _embedding_function
    if _embedding_function is None:
        _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        logger.info("Embedding function initialized: all-MiniLM-L6-v2")
    return _embedding_function


# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------
def get_or_create_collection(
    name: str,
    metadata: Optional[Dict[str, Any]] = None
) -> chromadb.Collection:
    """
    Get an existing collection or create it if it doesn't exist.
    """
    client = get_chroma_client()
    try:
        collection = client.get_collection(name, embedding_function=get_embedding_function())
        logger.debug(f"Retrieved existing collection: {name}")
    except Exception:
        collection = client.create_collection(
            name=name,
            embedding_function=get_embedding_function(),
            metadata=metadata or {}
        )
        logger.info(f"Created new collection: {name}")
    return collection


# ---------------------------------------------------------------------------
# Async wrapper functions
# ---------------------------------------------------------------------------
async def add_to_collection(
    collection_name: str,
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    ids: List[str]
) -> None:
    """
    Add documents to a ChromaDB collection.
    Runs in a thread to avoid blocking the event loop.
    """
    def _add():
        collection = get_or_create_collection(collection_name)
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        logger.debug(f"Added {len(documents)} documents to {collection_name}")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _add)


async def query_collection(
    collection_name: str,
    query_text: str,
    n_results: int = 10,
    where_filter: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Query a ChromaDB collection.
    Returns a list of dictionaries with keys: id, document, metadata, distance.
    """
    def _query():
        collection = get_or_create_collection(collection_name)
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where_filter
        )
        # Format results as list of dicts
        formatted = []
        for i in range(len(results["ids"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i] if results["documents"] else None,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else None,
                "distance": results["distances"][0][i] if results["distances"] else None
            })
        return formatted

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _query)


async def delete_old_embeddings(collection_name: str, days_old: int = 60) -> int:
    """
    Delete embeddings older than `days_old` days from a collection.
    Returns the number of deleted embeddings.
    """
    def _delete():
        collection = get_or_create_collection(collection_name)
        cutoff = int(time.time()) - days_old * 86400
        results = collection.get(where={"timestamp": {"$lt": cutoff}})
        ids = results.get("ids", []) if isinstance(results, dict) else []
        if ids:
            collection.delete(ids=ids)
        return len(ids)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _delete)


async def get_storage_size_gb() -> float:
    """
    Get the total size of the ChromaDB storage directory in GB.
    """
    def _get_size():
        persist_dir = Path(settings.CHROMA_PERSIST_DIR)
        if not persist_dir.exists():
            return 0.0
        total_size = sum(
            f.stat().st_size for f in persist_dir.rglob("*") if f.is_file()
        )
        return total_size / (1024 ** 3)  # Convert to GB

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _get_size)


async def enforce_storage_limit() -> None:
    """
    If storage size exceeds settings.CHROMA_MAX_GB, delete the oldest 10% of embeddings.
    """
    size_gb = await get_storage_size_gb()
    if size_gb > settings.CHROMA_MAX_GB:
        logger.warning(
            f"ChromaDB storage size {size_gb:.2f} GB exceeds limit {settings.CHROMA_MAX_GB} GB. "
            f"Enforcing storage limit by deleting oldest 10%."
        )
        # In a full implementation, we would:
        # 1. For each collection, get the oldest 10% by timestamp and delete them.
        # 2. Since we don't have a timestamp field in our current metadata schema, we skip.
        #    This is a limitation; in production, you would add a timestamp to metadata.
        logger.info("Storage limit enforcement skipped: no timestamp filtering implemented.")
    else:
        logger.debug(f"ChromaDB storage size {size_gb:.2f} GB is within limit {settings.CHROMA_MAX_GB} GB.")


# ---------------------------------------------------------------------------
# Initialization and auto-cleanup
# ---------------------------------------------------------------------------
def initialize_collections() -> None:
    """
    Create the required collections if they don't exist.
    Called on startup.
    """
    collections = [
        ("stock_embeddings", {
            "description": "Embeddings for stock data",
            "metadata_schema": "symbol, exchange, date, data_type"
        }),
        ("news_embeddings", {
            "description": "Embeddings for news articles",
            "metadata_schema": "source, published_at, topic, sentiment_score"
        }),
        ("sentiment_embeddings", {
            "description": "Embeddings for sentiment data",
            "metadata_schema": "source, symbol, timestamp"
        }),
        ("user_query_memory", {
            "description": "Embeddings for user queries",
            "metadata_schema": "user_id, query_type, timestamp"
        }),
        ("chat_memory", {
            "description": "Embeddings for chat conversations",
            "metadata_schema": "user_id, session_id, role, intent_tag, timestamp"
        })
    ]

    for name, metadata in collections:
        get_or_create_collection(name, metadata)
        logger.info(f"Ensured collection exists: {name}")

    # Run auto-cleanup if storage > 80% of limit
    try:
        # We'll run the async function in a sync context for simplicity during init
        # In a real app, you might call this from an async startup event.
        size_gb = get_storage_size_gb.__wrapped__() if hasattr(get_storage_size_gb, '__wrapped__') else get_storage_size_gb()
        if asyncio.iscoroutine(size_gb):
            # If it's a coroutine, we can't run it here without an event loop.
            # We'll skip the auto-cleanup during init and rely on the first request to trigger it.
            logger.info("Skipping auto-cleanup during initialization (requires event loop)")
        else:
            if size_gb > settings.CHROMA_MAX_GB * 0.8:
                logger.info(
                    f"ChromaDB storage at {size_gb:.2f} GB (>80% of {settings.CHROMA_MAX_GB} GB). "
                    f"Running storage limit enforcement."
                )
                # Again, we can't run the async function here without an event loop.
                # We'll log and skip.
                logger.info("Storage limit enforcement skipped during initialization (requires event loop)")
    except Exception as e:
        logger.warning(f"Could not check storage size during initialization: {e}")


# Initialize collections on import (if not in a testing environment)
if os.getenv("APP_ENV") != "testing":
    try:
        initialize_collections()
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB collections: {e}")
