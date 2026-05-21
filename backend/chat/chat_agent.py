import json
import uuid
import time
from typing import Dict, Any, List, AsyncGenerator
from backend.core.model_router import ModelRouter
from backend.db.chroma_init import get_chroma_client
from backend.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are Numeris, a highly analytical, objective, and precise financial expert AI. 
Provide concise, data-driven answers. Never give financial advice. 
When providing a stock analysis summary, include the pattern: [STOCK_ANALYSIS:{symbol}:{recommendation}:{confidence}]"""

class ChatAgent:
    def __init__(self, model_router: ModelRouter):
        self.model_router = model_router
        self.chroma_client = get_chroma_client()

    async def classify_intent(self, message: str) -> str:
        prompt = f"Classify this message into exactly one category: stock_analysis, market_news, portfolio_help, education, app_help, casual. Message: {message}. Reply with only the category name."
        try:
            category = await self.model_router.route("chat", prompt, "You are an intent classifier.")
            return category.strip().lower()
        except Exception:
            return "casual"

    async def chat(self, user_id: str, session_id: str, message: str) -> Dict[str, Any]:
        intent = await self.classify_intent(message)
        
        history = await self.get_history(user_id, session_id)
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-5:]])
        
        full_prompt = f"History:\n{history_text}\n\nUser: {message}"
        response = await self.model_router.route("chat", full_prompt, SYSTEM_PROMPT)
        
        if self.chroma_client:
            try:
                collection = self.chroma_client.get_or_create_collection("chat_memory")
                timestamp = int(time.time())
                collection.add(
                    documents=[message, response],
                    metadatas=[
                        {"user_id": user_id, "session_id": session_id, "role": "user", "intent_tag": intent, "timestamp": timestamp},
                        {"user_id": user_id, "session_id": session_id, "role": "assistant", "intent_tag": intent, "timestamp": timestamp + 1}
                    ],
                    ids=[str(uuid.uuid4()), str(uuid.uuid4())]
                )
            except Exception as e:
                logger.error(f"Failed to store chat memory: {e}")
                
        return {"response": response, "intent": intent}

    async def chat_stream(self, user_id: str, session_id: str, message: str) -> AsyncGenerator[str, None]:
        intent = await self.classify_intent(message)
        history = await self.get_history(user_id, session_id)
        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-5:]])
        full_prompt = f"History:\n{history_text}\n\nUser: {message}"
        
        full_response = ""
        async for chunk in self.model_router.route_stream("chat", full_prompt, SYSTEM_PROMPT):
            full_response += chunk
            yield chunk
            
        if self.chroma_client:
            try:
                collection = self.chroma_client.get_or_create_collection("chat_memory")
                timestamp = int(time.time())
                collection.add(
                    documents=[message, full_response],
                    metadatas=[
                        {"user_id": user_id, "session_id": session_id, "role": "user", "intent_tag": intent, "timestamp": timestamp},
                        {"user_id": user_id, "session_id": session_id, "role": "assistant", "intent_tag": intent, "timestamp": timestamp + 1}
                    ],
                    ids=[str(uuid.uuid4()), str(uuid.uuid4())]
                )
            except Exception as e:
                logger.error(f"Failed to store chat memory: {e}")

    async def get_history(self, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        if not self.chroma_client:
            return []
        try:
            collection = self.chroma_client.get_collection("chat_memory")
            results = collection.get(
                where={"$and": [{"user_id": user_id}, {"session_id": session_id}]}
            )
            if not results['documents']:
                return []
            
            history = []
            for doc, meta in zip(results['documents'], results['metadatas']):
                history.append({"role": meta['role'], "content": doc, "timestamp": meta['timestamp']})
            history.sort(key=lambda x: x['timestamp'])
            return history
        except Exception:
            return []

    async def new_session(self, user_id: str) -> str:
        return str(uuid.uuid4())
        
    async def delete_session(self, user_id: str, session_id: str) -> bool:
        if not self.chroma_client: return False
        try:
            collection = self.chroma_client.get_collection("chat_memory")
            collection.delete(where={"$and": [{"user_id": user_id}, {"session_id": session_id}]})
            return True
        except:
            return False
            
    async def search_past_conversations(self, user_id: str, query: str) -> List[str]:
        if not self.chroma_client: return []
        try:
            collection = self.chroma_client.get_collection("chat_memory")
            results = collection.query(
                query_texts=[query],
                n_results=5,
                where={"user_id": user_id}
            )
            return results['documents'][0] if results['documents'] else []
        except:
            return []
