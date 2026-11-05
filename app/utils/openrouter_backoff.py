"""
openrouter_backoff.py — Wrapper con exponential backoff para llamadas a OpenRouter.

Reintentos solo en errores transitorios (429, 500, 502, 503, 504).
Falla inmediatamente en errores del cliente (400, 401, 403, 404, 422).
"""
import time
import logging

import requests

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def call_openrouter_with_backoff(
    url: str,
    headers: dict,
    payload: dict,
    max_retries: int = 4,
    base_delay: float = 1.0,
    timeout: int = 60,
) -> str:
    """
    POST a OpenRouter con exponential backoff.

    Returns:
        El texto generado (choices[0].message.content).

    Raises:
        RuntimeError: Si se agotan los reintentos en un error 429/5xx.
        requests.HTTPError: Para errores no retryables (4xx excepto 429).
    """
    delay = base_delay
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()

        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)

            if status not in _RETRYABLE_STATUS:
                raise  # error del cliente → no reintentar

            last_exc = exc
            logger.warning(
                "OpenRouter HTTP %s — intento %d/%d, reintentando en %.1fs",
                status, attempt, max_retries, delay,
            )

        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            logger.warning(
                "OpenRouter conexión/timeout — intento %d/%d, reintentando en %.1fs",
                attempt, max_retries, delay,
            )

        if attempt < max_retries:
            time.sleep(delay)
            delay *= 2

    raise RuntimeError(
        f"OpenRouter no respondió tras {max_retries} intentos. "
        f"Último error: {last_exc} "
        f"(429/5xx: reintentos agotados)"
    )
