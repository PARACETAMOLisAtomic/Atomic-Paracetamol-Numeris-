import time
import traceback
from typing import Dict, Any, List
from backend.core.model_router import ModelRouter
from backend.utils.logger import get_logger
from backend.db.chroma_init import get_chroma_client

logger = get_logger(__name__)

class BaseQuantAgent:
    def __init__(self, agent_name: str, model_router: ModelRouter, tools: List[Any] = None):
        self.agent_name = agent_name
        self.model_router = model_router
        self.tools = tools or []
        self.chroma_client = get_chroma_client()

    async def execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        result = {}
        try:
            logger.info(f"Agent {self.agent_name} starting execution.")
            result = await self._run(task, context)
            
            try:
                if self.chroma_client:
                    collection = self.chroma_client.get_or_create_collection("user_query_memory")
                    collection.add(
                        documents=[str(result)],
                        metadatas=[{"agent_name": self.agent_name, "task": task}],
                        ids=[f"{self.agent_name}_{int(time.time())}"]
                    )
            except Exception as mem_e:
                logger.warning(f"Failed to save to ChromaDB: {mem_e}")

        except Exception as e:
            logger.error(f"Error in {self.agent_name} execution: {traceback.format_exc()}")
            result = {"error": str(e)}
        finally:
            execution_time = time.time() - start_time
            result['execution_time_ms'] = int(execution_time * 1000)
            logger.info(f"Agent {self.agent_name} finished in {result['execution_time_ms']}ms.")
            
        return result

    async def _run(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement _run method.")

    async def get_memory(self, query: str, n_results: int = 5) -> List[str]:
        try:
            if not self.chroma_client:
                return []
            collection = self.chroma_client.get_collection("user_query_memory")
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"agent_name": self.agent_name}
            )
            return results['documents'][0] if results['documents'] else []
        except Exception as e:
            logger.warning(f"Failed to retrieve memory from ChromaDB: {e}")
            return []
