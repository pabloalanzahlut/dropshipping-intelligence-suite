"""
RetryDecorator — Exponential Backoff con Jitter para Resiliencia de Red
========================================================================
Algoritmo: delay = min(base_delay * (2^attempt) + jitter, max_delay)
           jitter = random.uniform(-jitter_factor, +jitter_factor) * delay

Cubre: HTTP 429, 5xx, ConnectionError, Timeout, OSError.

Uso:
    @with_retry(max_retries=3, base_delay=1.0)
    def mi_funcion(url):
        return requests.get(url)
"""

import asyncio
import functools
import logging
import random
import time
from typing import Callable, Optional, Type, Tuple

import requests

logger = logging.getLogger(__name__)

DEFAULT_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.HTTPError,
    requests.exceptions.ChunkedEncodingError,
    ConnectionError,
    TimeoutError,
    OSError,
)


def is_429_or_5xx(exc: Exception) -> bool:
    """Determina si una excepción HTTP contiene código 429 o 5xx."""
    if hasattr(exc, "response") and exc.response is not None:
        status = getattr(exc.response, "status_code", 0)
        return status == 429 or 500 <= status < 600
    if hasattr(exc, "status_code"):
        return exc.status_code == 429 or 500 <= exc.status_code < 600
    for arg in getattr(exc, "args", []):
        if isinstance(arg, int) and (arg == 429 or 500 <= arg < 600):
            return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# DECORADOR SINCRÓNICO
# ═══════════════════════════════════════════════════════════════════════════

def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter_factor: float = 0.25,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
):
    """
    Decorador: envuelve función con Exponential Backoff + Jitter.

    Args:
        max_retries: Número máximo de reintentos (default: 3).
        base_delay: Retraso base en segundos (default: 1.0).
        max_delay: Retraso máximo en segundos (default: 60.0).
        jitter_factor: Factor de jitter como fracción (default: 0.25 = ±25%).
        retryable_exceptions: Tupla de excepciones capturables.
        on_retry: Callback opcional: on_retry(exc, attempt, delay).
    """
    if retryable_exceptions is None:
        retryable_exceptions = DEFAULT_RETRYABLE_EXCEPTIONS

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    if not is_429_or_5xx(exc) and not isinstance(
                        exc, (ConnectionError, TimeoutError, OSError)
                    ):
                        if hasattr(exc, "response") and exc.response is not None:
                            if exc.response.status_code < 500 and exc.response.status_code != 429:
                                raise
                        else:
                            raise
                except Exception:
                    raise

                if attempt < max_retries:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(
                        -jitter_factor * delay, +jitter_factor * delay
                    )
                    sleep_time = max(0.1, delay + jitter)

                    logger.warning(
                        "[RETRY] Intento %d/%d falló: %s. Reintentando en %.2fs...",
                        attempt + 1, max_retries, last_exc, sleep_time,
                    )
                    if on_retry:
                        on_retry(last_exc, attempt + 1, sleep_time)
                    time.sleep(sleep_time)

            logger.error("[RETRY] Agotados %d reintentos para %s. Último error: %s",
                         max_retries, func.__name__, last_exc)
            raise last_exc
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════
# DECORADOR ASÍNCRONO
# ═══════════════════════════════════════════════════════════════════════════

def with_async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter_factor: float = 0.25,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None,
):
    """Versión asíncrona del decorador with_retry."""
    if retryable_exceptions is None:
        retryable_exceptions = DEFAULT_RETRYABLE_EXCEPTIONS

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as exc:
                    last_exc = exc
                    if not is_429_or_5xx(exc) and not isinstance(
                        exc, (ConnectionError, TimeoutError, OSError)
                    ):
                        if hasattr(exc, "response") and exc.response is not None:
                            if exc.response.status_code < 500 and exc.response.status_code != 429:
                                raise
                        else:
                            raise
                except Exception:
                    raise

                if attempt < max_retries:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(-jitter_factor * delay, +jitter_factor * delay)
                    sleep_time = max(0.1, delay + jitter)
                    logger.warning("[RETRY-ASYNC] Intento %d/%d falló: %s. Reintentando en %.2fs...",
                                   attempt + 1, max_retries, last_exc, sleep_time)
                    if on_retry:
                        on_retry(last_exc, attempt + 1, sleep_time)
                    await asyncio.sleep(sleep_time)

            logger.error("[RETRY-ASYNC] Agotados %d reintentos para %s. Último error: %s",
                         max_retries, func.__name__, last_exc)
            raise last_exc
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════
# FUNCIÓN HELPER (no decorador)
# ═══════════════════════════════════════════════════════════════════════════

def retry_call(
    func: Callable,
    args: tuple = (),
    kwargs: Optional[dict] = None,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> any:
    """Versión funcional de retry (no decorador).
    Ejemplo: resultado = retry_call(requests.get, args=(url,), max_retries=5)
    """
    wrapped = with_retry(max_retries=max_retries, base_delay=base_delay)(func)
    return wrapped(*args, **(kwargs or {}))