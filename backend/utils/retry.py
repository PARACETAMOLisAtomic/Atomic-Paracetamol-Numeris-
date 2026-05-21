import asyncio
import functools
import random
import time
from typing import Callable, Type, Tuple, Any
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,)
):
    """
    Decorator that implements exponential backoff with jitter for retrying functions.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_delay: Maximum delay in seconds between retries
        exceptions: Tuple of exception types to catch and retry on

    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_retries:
                            logger.error(
                                f"Function {func.__name__} failed after {max_retries} retries",
                                extra={"exception": str(e), "attempt": attempt + 1}
                            )
                            raise

                        # Calculate delay with exponential backoff and jitter
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = random.uniform(0, delay * 0.1)
                        total_delay = delay + jitter

                        logger.warning(
                            f"Function {func.__name__} failed on attempt {attempt + 1}, "
                            f"retrying in {total_delay:.2f}s",
                            extra={"exception": str(e), "attempt": attempt + 1, "delay": total_delay}
                        )
                        await asyncio.sleep(total_delay)

                # This should never be reached, but just in case
                raise last_exception
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_retries:
                            logger.error(
                                f"Function {func.__name__} failed after {max_retries} retries",
                                extra={"exception": str(e), "attempt": attempt + 1}
                            )
                            raise

                        # Calculate delay with exponential backoff and jitter
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = random.uniform(0, delay * 0.1)
                        total_delay = delay + jitter

                        logger.warning(
                            f"Function {func.__name__} failed on attempt {attempt + 1}, "
                            f"retrying in {total_delay:.2f}s",
                            extra={"exception": str(e), "attempt": attempt + 1, "delay": total_delay}
                        )
                        time.sleep(total_delay)

                # This should never be reached, but just in case
                raise last_exception
            return sync_wrapper
    return decorator


def async_retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,)
):
    """
    Async decorator that implements exponential backoff with jitter for retrying async functions.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_delay: Maximum delay in seconds between retries
        exceptions: Tuple of exception types to catch and retry on

    Returns:
        Decorated async function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(
                            f"Async function {func.__name__} failed after {max_retries} retries",
                            extra={"exception": str(e), "attempt": attempt + 1}
                        )
                        raise

                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.1)
                    total_delay = delay + jitter

                    logger.warning(
                        f"Async function {func.__name__} failed on attempt {attempt + 1}, "
                        f"retrying in {total_delay:.2f}s",
                        extra={"exception": str(e), "attempt": attempt + 1, "delay": total_delay}
                    )
                    await asyncio.sleep(total_delay)

            # This should never be reached, but just in case
            raise last_exception
        return wrapper
    return decorator