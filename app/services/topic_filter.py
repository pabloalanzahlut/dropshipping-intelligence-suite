"""
topic_filter — decide si un vídeo es de ecommerce / dropshipping / Shopify.

Se aplica solo a los canales con `"filtro_tema": true` en youtube_channels.json
(hoy: Adrián Sáenz, que también habla de IA, mentalidad, numerología, etc.).
Los canales complementarios, dedicados solo a dropshipping, NO se filtran.

Reglas (Python puro, sin IA, deterministas):
  1. El título menciona el tema                      -> es del tema.
  2. Si no, el texto debe mencionarlo de verdad:
     al menos MIN_MENCIONES veces Y al menos MIN_DENSIDAD por cada 1000 palabras.

Calibrado con los últimos vídeos de Adrián Sáenz (nov-2026): los de tema tenían
34–44 menciones (6,6–9,2 por 1000 palabras); los demás, 0–2 (≤0,2 por 1000).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Tuple

MIN_MENCIONES = 5
MIN_DENSIDAD = 2.0   # menciones por cada 1000 palabras

_TEMA = re.compile(
    r"\b(?:e-?commerce|ecom|dropshipping|drop shipping|dropshippers?|shopify|"
    r"tiendas? online|tienda virtual|tienda en linea|comercio electronico)\b"
)


def _normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar sin depender de tildes."""
    sin_tildes = unicodedata.normalize("NFD", texto or "").encode("ascii", "ignore").decode()
    return sin_tildes.lower()


def contar_menciones(texto: str) -> int:
    return len(_TEMA.findall(_normalizar(texto)))


def evaluar(titulo: str, texto: str) -> Tuple[bool, str]:
    """Devuelve (es_del_tema, motivo). El motivo queda registrado en los logs."""
    if contar_menciones(titulo):
        return True, "el título menciona el tema"

    norm = _normalizar(texto)
    palabras = max(len(norm.split()), 1)
    menciones = len(_TEMA.findall(norm))
    densidad = menciones / palabras * 1000
    if menciones >= MIN_MENCIONES and densidad >= MIN_DENSIDAD:
        return True, f"{menciones} menciones ({densidad:.1f} por 1000 palabras)"
    return False, f"solo {menciones} menciones ({densidad:.1f} por 1000 palabras)"
