"""
FX Rates — Tipo de cambio en tiempo real vía Frankfurter.

GEM OS mezcla costes en USD (AliExpress, CJ, Temu) con PVP en EUR. Con un tipo
de cambio fijo el multiplicador queda falseado: una variación del 5% EUR/USD
mueve el margen lo suficiente para cruzar el umbral 2x sin que nadie lo note.

Frankfurter es gratuito y no necesita clave (datos del Banco Central Europeo).
Método tomado de Adrián Sáenz (KXKzgeHOr7A, hack 3).

Caché en memoria de 6 horas: el BCE publica una vez al día.
"""

import time
import logging
import requests
from typing import Optional, Dict

logger = logging.getLogger(__name__)

FRANKFURTER_BASE = "https://api.frankfurter.app"
CACHE_TTL_SECONDS = 6 * 3600

# Tipo de respaldo si la API no responde. Deliberadamente conservador:
# sobreestima el coste en EUR para no aprobar productos al límite.
FALLBACK_RATES = {
    ("USD", "EUR"): 0.92,
    ("EUR", "USD"): 1.09,
}

_cache: Dict[tuple, tuple] = {}  # (from, to) -> (rate, timestamp)


def get_rate(from_currency: str = "USD", to_currency: str = "EUR") -> float:
    """
    Devuelve el tipo de cambio actual. Usa caché de 6h y respaldo si falla.

    El respaldo nunca es silencioso: queda registrado como WARNING para que
    una validación hecha con tipo estimado sea rastreable.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return 1.0

    key = (from_currency, to_currency)
    cached = _cache.get(key)
    if cached and (time.time() - cached[1]) < CACHE_TTL_SECONDS:
        return cached[0]

    try:
        resp = requests.get(
            f"{FRANKFURTER_BASE}/latest",
            params={"from": from_currency, "to": to_currency},
            timeout=10,
        )
        resp.raise_for_status()
        rate = resp.json()["rates"][to_currency]
        _cache[key] = (rate, time.time())
        logger.info(f"[FX] {from_currency}/{to_currency} = {rate}")
        return rate

    except Exception as e:
        fallback = FALLBACK_RATES.get(key)
        if fallback is None:
            raise RuntimeError(
                f"[FX] No se pudo obtener {from_currency}/{to_currency} y no hay respaldo: {e}"
            )
        logger.warning(
            f"[FX] Frankfurter no responde ({e}). Usando respaldo conservador "
            f"{from_currency}/{to_currency} = {fallback}. La validación queda marcada como estimada."
        )
        return fallback


def convert(amount: float, from_currency: str, to_currency: str) -> float:
    """Convierte un importe entre divisas al tipo actual."""
    return round(amount * get_rate(from_currency, to_currency), 4)


def is_rate_live(from_currency: str = "USD", to_currency: str = "EUR") -> bool:
    """
    Indica si el último tipo usado vino de la API o del respaldo.
    Útil para marcar una validación financiera como estimada.
    """
    key = (from_currency.upper(), to_currency.upper())
    cached = _cache.get(key)
    return bool(cached and (time.time() - cached[1]) < CACHE_TTL_SECONDS)
