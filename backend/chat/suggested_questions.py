import datetime
from typing import List
from backend.utils.cache import redis_cache

@redis_cache(ttl_seconds=900, key_prefix="suggested_questions")
async def get_suggested_questions(user_id: str) -> List[str]:
    today = datetime.date.today().isoformat()
    return [
        f"What is the market sentiment today ({today})?",
        "Analyze RELIANCE for potential breakout.",
        "How is the IT sector performing this week?",
        "What are the key resistance levels for HDFCBANK?",
        "Summarize the latest RBI policy updates."
    ]
