import asyncio
import functools
import logging

logger = logging.getLogger(__name__)


def with_retry(retryable_exceptions: tuple, max_attempts: int = 3, base_delay: float = 0.5):
    """Retry an async connector method with exponential backoff.

    Only retries transient failures (network drops, rate limits) — anything
    else (bad symbol, insufficient funds, auth error) should fail immediately
    instead of being retried 3 times for no benefit.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                        func.__qualname__, attempt, max_attempts, exc, delay,
                    )
                    await asyncio.sleep(delay)
            raise last_exc

        return wrapper

    return decorator
