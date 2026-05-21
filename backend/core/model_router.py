"""
Multi-LLM Model Router for Numeris.
Providers: Groq (Llama 3.1 70B), Mistral Large 2, DeepSeek V2, Local Phi-3-mini.
Features: routing table, health tracking, triple-validate, streaming, usage tracking.
Redis is optional — degrades gracefully when unavailable.
Numeris v3.0
"""

from __future__ import annotations

import asyncio
import time
from datetime import date, datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.core.config import settings
from backend.utils.logger import get_logger
from backend.utils.retry import async_retry_with_backoff

logger = get_logger("model_router")


# ---------------------------------------------------------------------------
# Provider: Groq (Llama 3.1 70B)
# ---------------------------------------------------------------------------
class GroqProvider:
    """Groq-hosted Llama 3.1 70B provider."""

    NAME = "groq"
    MODEL = "llama-3.1-70b-versatile"

    def __init__(self) -> None:
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from langchain_groq import ChatGroq  # type: ignore[import]
            self._client = ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model_name=self.MODEL,
                temperature=0.1,
                max_tokens=4096,
            )
        return self._client

    @async_retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def complete(self, prompt: str, system_prompt: str = "", max_tokens: int = 4096) -> str:
        """Return a completion string from Groq."""
        from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import]

        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: client.invoke(messages)
        )
        return str(response.content)

    async def stream(self, prompt: str, system_prompt: str = "") -> AsyncGenerator[str, None]:
        """Stream tokens from Groq."""
        from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import]

        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            for chunk in client.stream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        except Exception as exc:
            logger.error("Groq stream error", extra={"error": str(exc)})
            raise


# ---------------------------------------------------------------------------
# Provider: Mistral Large 2
# ---------------------------------------------------------------------------
class MistralProvider:
    """Mistral AI provider (max 1 req/sec enforced)."""

    NAME = "mistral"
    MODEL = "mistral-large-latest"
    _last_call: float = 0.0

    def __init__(self) -> None:
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from langchain_mistralai import ChatMistralAI  # type: ignore[import]
            self._client = ChatMistralAI(
                api_key=settings.MISTRAL_API_KEY,
                model=self.MODEL,
                temperature=0.1,
                max_tokens=4096,
            )
        return self._client

    @async_retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def complete(self, prompt: str, system_prompt: str = "", max_tokens: int = 4096) -> str:
        """Return a completion from Mistral (rate-limited to 1 req/sec)."""
        from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import]

        # Enforce 1 req/sec
        elapsed = time.time() - MistralProvider._last_call
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        MistralProvider._last_call = time.time()

        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: client.invoke(messages)
        )
        return str(response.content)

    async def stream(self, prompt: str, system_prompt: str = "") -> AsyncGenerator[str, None]:
        """Stream tokens from Mistral."""
        from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import]

        elapsed = time.time() - MistralProvider._last_call
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
        MistralProvider._last_call = time.time()

        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            for chunk in client.stream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        except Exception as exc:
            logger.error("Mistral stream error", extra={"error": str(exc)})
            raise


# ---------------------------------------------------------------------------
# Provider: DeepSeek V2
# ---------------------------------------------------------------------------
class DeepSeekProvider:
    """DeepSeek provider via OpenAI-compatible API."""

    NAME = "deepseek"
    MODEL = "deepseek-chat"
    BASE_URL = "https://api.deepseek.com"

    def __init__(self) -> None:
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from langchain_community.chat_models import ChatOpenAI  # type: ignore[import]
            self._client = ChatOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=self.BASE_URL,
                model_name=self.MODEL,
                temperature=0.1,
                max_tokens=4096,
            )
        return self._client

    @async_retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
    async def complete(self, prompt: str, system_prompt: str = "", max_tokens: int = 4096) -> str:
        """Return a completion from DeepSeek."""
        from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import]

        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: client.invoke(messages)
        )
        return str(response.content)

    async def stream(self, prompt: str, system_prompt: str = "") -> AsyncGenerator[str, None]:
        """Stream tokens from DeepSeek."""
        from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import]

        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            for chunk in client.stream(messages):
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
        except Exception as exc:
            logger.error("DeepSeek stream error", extra={"error": str(exc)})
            raise


# ---------------------------------------------------------------------------
# Provider: Local Phi-3-mini (llama-cpp-python)
# ---------------------------------------------------------------------------
class LocalProvider:
    """CPU-only local Phi-3-mini via llama-cpp-python."""

    NAME = "local"
    _model: Any = None
    _load_attempted: bool = False

    def _get_model(self) -> Any:
        if self._load_attempted:
            return self._model
        self._load_attempted = True

        import os
        model_path = settings.LOCAL_MODEL_PATH
        if not os.path.exists(model_path):
            logger.warning("Local model not found", extra={"path": model_path})
            return None

        try:
            from llama_cpp import Llama  # type: ignore[import]
            logger.info("Loading local Phi-3-mini model (this may take ~30 seconds)...")
            self._model = Llama(
                model_path=model_path,
                n_ctx=4096,
                n_threads=4,
                verbose=False,
            )
            logger.info("Local model loaded successfully")
        except ImportError:
            logger.warning("llama-cpp-python not installed — local provider unavailable")
            self._model = None
        except Exception as exc:
            logger.error("Failed to load local model", extra={"error": str(exc)})
            self._model = None

        return self._model

    async def complete(self, prompt: str, system_prompt: str = "", max_tokens: int = 2048) -> str:
        """Return a completion from the local Phi-3-mini model."""
        def _infer() -> str:
            model = self._get_model()
            if model is None:
                return "Local model unavailable. Please check that the Phi-3-mini GGUF file exists at the configured path."

            full_prompt = f"<|system|>{system_prompt}<|end|><|user|>{prompt}<|end|><|assistant|>" if system_prompt else f"<|user|>{prompt}<|end|><|assistant|>"
            output = model(full_prompt, max_tokens=max_tokens, stop=["<|end|>", "<|user|>"])
            return output["choices"][0]["text"].strip()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _infer)

    async def stream(self, prompt: str, system_prompt: str = "") -> AsyncGenerator[str, None]:
        """Stream tokens from the local model (simulated streaming via full completion)."""
        result = await self.complete(prompt, system_prompt)
        # Simulate streaming by yielding words
        for word in result.split():
            yield word + " "
            await asyncio.sleep(0.01)


# ---------------------------------------------------------------------------
# Model Router
# ---------------------------------------------------------------------------
class ModelRouter:
    """Routes LLM tasks to the appropriate provider with failover and health tracking."""

    ROUTING_TABLE: Dict[str, List[str]] = {
        "quantitative": ["deepseek", "groq", "mistral", "local"],
        "risk_analysis": ["mistral", "groq", "deepseek", "local"],
        "general_analysis": ["groq", "mistral", "deepseek", "local"],
        "chat": ["groq", "mistral", "local"],
        "offline": ["local"],
    }

    def __init__(self) -> None:
        self._providers: Dict[str, Any] = {
            "groq": GroqProvider(),
            "mistral": MistralProvider(),
            "deepseek": DeepSeekProvider(),
            "local": LocalProvider(),
        }
        # Health stats per provider
        self._health: Dict[str, Dict[str, Any]] = {
            name: {
                "total": 0,
                "success": 0,
                "failed": 0,
                "avg_latency_ms": 0.0,
                "degraded": False,
                "last_check": 0.0,
            }
            for name in self._providers
        }

    # ------------------------------------------------------------------
    # Core routing
    # ------------------------------------------------------------------
    async def route(
        self,
        task_type: str,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 4096,
    ) -> str:
        """Route a prompt to the best available provider.

        Parameters
        ----------
        task_type:
            One of ``"quantitative"``, ``"risk_analysis"``, ``"general_analysis"``,
            ``"chat"``, ``"offline"``.
        prompt:
            The user/task prompt.
        system_prompt:
            Optional system prompt.
        max_tokens:
            Maximum tokens to generate.

        Returns
        -------
        str
            The model's response text.

        Raises
        ------
        RuntimeError
            If all providers in the routing table fail.
        """
        providers = self.ROUTING_TABLE.get(task_type, self.ROUTING_TABLE["general_analysis"])
        last_error: Optional[Exception] = None

        for provider_name in providers:
            provider = self._providers.get(provider_name)
            if provider is None:
                continue
            h = self._health[provider_name]
            if h["degraded"] and time.time() - h["last_check"] < 300:
                logger.debug("Skipping degraded provider", extra={"provider": provider_name})
                continue

            start = time.perf_counter()
            try:
                result = await provider.complete(prompt, system_prompt, max_tokens)
                elapsed_ms = (time.perf_counter() - start) * 1000
                await self._record_success(provider_name, elapsed_ms)
                await self.track_usage(provider_name, len(result.split()) * 2, success=True)
                logger.debug("Provider succeeded", extra={"provider": provider_name, "task": task_type})
                return result
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                last_error = exc
                logger.warning(
                    "Provider failed — trying next",
                    extra={"provider": provider_name, "error": str(exc), "task": task_type},
                )
                await self._record_failure(provider_name)
                await self.track_usage(provider_name, 0, success=False)

        raise RuntimeError(
            f"All providers failed for task_type={task_type!r}. Last error: {last_error}"
        )

    async def route_stream(
        self,
        task_type: str,
        prompt: str,
        system_prompt: str = "",
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from the best available provider.

        Parameters
        ----------
        task_type:
            Task routing category.
        prompt:
            The prompt to send.
        system_prompt:
            Optional system-level instruction.

        Yields
        ------
        str
            Individual token chunks as they arrive.
        """
        providers = self.ROUTING_TABLE.get(task_type, self.ROUTING_TABLE["chat"])

        for provider_name in providers:
            provider = self._providers.get(provider_name)
            if provider is None:
                continue
            h = self._health[provider_name]
            if h["degraded"] and time.time() - h["last_check"] < 300:
                continue

            try:
                async for token in provider.stream(prompt, system_prompt):
                    yield token
                return  # success — stop after first working provider
            except Exception as exc:
                logger.warning(
                    "Stream provider failed — trying next",
                    extra={"provider": provider_name, "error": str(exc)},
                )
                await self._record_failure(provider_name)

        # Fallback: non-streaming
        result = await self.route(task_type, prompt, system_prompt)
        yield result

    # ------------------------------------------------------------------
    # Triple validation
    # ------------------------------------------------------------------
    async def triple_validate(
        self,
        analysis_prompt: str,
        primary_result: str,
    ) -> Dict[str, Any]:
        """Run Mistral and DeepSeek reviews on a primary Groq result.

        Parameters
        ----------
        analysis_prompt:
            The original analysis prompt (for context).
        primary_result:
            The primary LLM's answer to review.

        Returns
        -------
        dict with keys:
            ``final_response`` (str), ``confidence_score`` (int 0-100),
            ``model_contributions`` (dict), ``warnings`` (list[str]).
        """
        confidence = 70
        warnings: List[str] = []
        contributions: Dict[str, str] = {"groq": "primary"}

        risk_review_prompt = (
            f"You are a financial risk reviewer. A primary AI analysis was produced:\n\n"
            f"ORIGINAL QUESTION:\n{analysis_prompt}\n\n"
            f"PRIMARY ANSWER:\n{primary_result}\n\n"
            f"Review this for: factual errors, missed risks, overconfident statements, "
            f"or contradictions. Reply with:\n"
            f"VERDICT: AGREE or DISAGREE\n"
            f"ISSUES: (list any problems, or 'None')\n"
            f"ADDITIONS: (anything important missed)"
        )

        quant_review_prompt = (
            f"You are a quantitative analyst. Review this financial analysis:\n\n"
            f"QUESTION: {analysis_prompt}\n\nANALYSIS: {primary_result}\n\n"
            f"Verify: calculations, indicator values, mathematical claims. Reply:\n"
            f"VERDICT: AGREE or DISAGREE\n"
            f"CORRECTIONS: (specific corrections, or 'None')"
        )

        mistral_result = ""
        deepseek_result = ""

        # Run reviews in parallel
        try:
            results = await asyncio.gather(
                self._providers["mistral"].complete(risk_review_prompt),
                self._providers["deepseek"].complete(quant_review_prompt),
                return_exceptions=True,
            )
            mistral_result = results[0] if isinstance(results[0], str) else ""
            deepseek_result = results[1] if isinstance(results[1], str) else ""
        except Exception as exc:
            logger.warning("triple_validate review calls failed", extra={"error": str(exc)})

        # Score
        if mistral_result:
            contributions["mistral"] = "risk_review"
            if "AGREE" in mistral_result.upper():
                confidence += 15
            else:
                confidence -= 20
                warnings.append(f"Mistral risk review flagged issues: {mistral_result[:200]}")

        if deepseek_result:
            contributions["deepseek"] = "quant_verification"
            if "AGREE" in deepseek_result.upper():
                confidence += 15
            else:
                confidence -= 20
                warnings.append(f"DeepSeek quant review flagged issues: {deepseek_result[:200]}")

        confidence = max(0, min(100, confidence))

        # Build enhanced final response
        final = primary_result
        if warnings:
            final += "\n\n⚠️ **Reviewer Notes:**\n" + "\n".join(f"- {w}" for w in warnings)

        return {
            "final_response": final,
            "confidence_score": confidence,
            "model_contributions": contributions,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Health monitoring
    # ------------------------------------------------------------------
    async def health_check(self) -> Dict[str, Any]:
        """Return health status of all providers.

        Returns
        -------
        dict
            ``{provider_name: {status, total, success, failed, avg_latency_ms, degraded}}``.
        """
        status: Dict[str, Any] = {}
        for name, h in self._health.items():
            total = h["total"]
            fail_rate = h["failed"] / total if total > 0 else 0.0
            status[name] = {
                "status": "degraded" if h["degraded"] else ("healthy" if fail_rate < 0.2 else "warning"),
                "total_calls": total,
                "success": h["success"],
                "failed": h["failed"],
                "avg_latency_ms": round(h["avg_latency_ms"], 1),
                "degraded": h["degraded"],
            }
        return status

    async def track_usage(self, provider: str, tokens_used: int, success: bool) -> None:
        """Log API usage to SQLite (non-blocking; failures are swallowed)."""
        try:
            from backend.db.database import get_db_session
            from backend.db.models import ApiUsage
            from sqlalchemy import select

            today = date.today()
            async with get_db_session() as session:
                stmt = select(ApiUsage).where(
                    ApiUsage.provider == provider,
                    ApiUsage.date == today,
                )
                row = (await session.execute(stmt)).scalar_one_or_none()
                if row is None:
                    row = ApiUsage(provider=provider, date=today)
                    session.add(row)
                row.call_count = (row.call_count or 0) + 1
                row.token_count = (row.token_count or 0) + tokens_used
                if not success:
                    row.error_count = (row.error_count or 0) + 1

                # Warn approaching free-tier limits
                limits = {"groq": 6000, "mistral": 18_000_000, "deepseek": 9_000_000}
                if provider in limits and row.call_count >= limits[provider]:
                    logger.warning(
                        "Approaching API daily limit",
                        extra={"provider": provider, "calls": row.call_count},
                    )
        except Exception as exc:
            logger.debug("track_usage failed (non-critical)", extra={"error": str(exc)})

    # ------------------------------------------------------------------
    # Internal health helpers
    # ------------------------------------------------------------------
    async def _record_success(self, provider: str, latency_ms: float) -> None:
        h = self._health[provider]
        h["total"] += 1
        h["success"] += 1
        # Rolling average latency
        n = h["success"]
        h["avg_latency_ms"] = (h["avg_latency_ms"] * (n - 1) + latency_ms) / n
        # Recovery from degraded state
        if h["degraded"]:
            h["degraded"] = False
            logger.info("Provider recovered", extra={"provider": provider})

    async def _record_failure(self, provider: str) -> None:
        h = self._health[provider]
        h["total"] += 1
        h["failed"] += 1
        total = h["total"]
        fail_rate = h["failed"] / total if total >= 10 else 0.0
        if fail_rate > 0.2 and not h["degraded"]:
            self._mark_degraded(provider)

    def _mark_degraded(self, provider: str) -> None:
        self._health[provider]["degraded"] = True
        self._health[provider]["last_check"] = time.time()
        logger.warning("Provider marked degraded", extra={"provider": provider})
        asyncio.create_task(self._check_recovery(provider))

    async def _check_recovery(self, provider: str) -> None:
        """Re-test a degraded provider after 5 minutes."""
        await asyncio.sleep(300)
        try:
            p = self._providers[provider]
            await p.complete("Reply with: OK", "You are a health check.")
            self._health[provider]["degraded"] = False
            self._health[provider]["last_check"] = time.time()
            logger.info("Provider recovered after check", extra={"provider": provider})
        except Exception:
            self._health[provider]["last_check"] = time.time()
            asyncio.create_task(self._check_recovery(provider))


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """Return (or create) the singleton ModelRouter instance."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
