"""
Model Quality A/B — ¿el modelo barato está costando dinero?

EL PROBLEMA
-----------
En Project Vend, Anthropic puso agentes a comerciar: unos con Opus, otros con
Haiku. Los de Haiku vendieron el mismo artículo por $2,68 menos de media. Los 69
empleados que participaron **no notaron la diferencia**.

GEM OS enruta las fichas de Shopify y los borradores de guiones a DeepSeek
porque es 21× más barato. No existe ninguna medición de si esas salidas
convierten peor. El ahorro es visible; la pérdida, no.

QUÉ HACE ESTE MÓDULO
--------------------
Genera la misma pieza con dos modelos, la pasa por el gate determinista y
registra ambas para comparar conversión real más tarde. No decide por su cuenta:
produce la evidencia para que una persona decida.
"""

import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.services.llm_router import chat, MODEL_ROUTING
from app.services.deterministic_gate import verificar_copy

logger = logging.getLogger(__name__)

REGISTRO = "ai_workspace/knowledge_base/model_ab_tests.json"


def generar_variantes(
    task: str,
    system_prompt: str,
    user_message: str,
    modelo_barato: Optional[str] = None,
    modelo_premium: Optional[str] = None,
) -> Dict:
    """
    Genera la misma pieza con ambos modelos y las pasa por el gate.

    Returns:
        dict con ambas variantes, sus violaciones de gate y metadatos.
    """
    modelo_barato = modelo_barato or MODEL_ROUTING["default_volume"]
    modelo_premium = modelo_premium or MODEL_ROUTING["default_critical"]

    resultado = {
        "task": task,
        "input_hash": hash(user_message) & 0xFFFFFFFF,
        "generado_at": datetime.now(timezone.utc).isoformat(),
        "variantes": {},
    }

    for etiqueta, modelo in (("barato", modelo_barato), ("premium", modelo_premium)):
        texto = _chat_con_modelo(modelo, system_prompt, user_message)
        if texto is None:
            resultado["variantes"][etiqueta] = {"modelo": modelo, "error": "sin respuesta"}
            continue

        gate = verificar_copy(texto)
        resultado["variantes"][etiqueta] = {
            "modelo": modelo,
            "texto": texto,
            "longitud": len(texto),
            "gate_passed": gate["passed"],
            "violaciones": gate["violations"],
        }

    _anotar_diferencias(resultado)
    return resultado


def _chat_con_modelo(modelo: str, system_prompt: str, user_message: str) -> Optional[str]:
    """Llama a un modelo concreto saltándose la tabla de routing."""
    import requests

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("[AB] OPENROUTER_API_KEY no configurada")
        return None

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://gem-os.dropshipping",
                "X-Title": "GEM OS A/B",
            },
            json={
                "model": modelo,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 1024,
                "temperature": 0.2,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"[AB] Error con {modelo}: {e}")
        return None


def _anotar_diferencias(resultado: Dict) -> None:
    """
    Señala diferencias objetivas entre variantes.

    No juzga cuál es "mejor" — eso solo lo dice la conversión real. Marca lo
    que es comprobable sin opinión: violaciones de gate y diferencia de longitud.
    """
    barato = resultado["variantes"].get("barato", {})
    premium = resultado["variantes"].get("premium", {})

    señales = []
    if barato.get("gate_passed") is False and premium.get("gate_passed") is True:
        señales.append(
            f"El modelo barato falló el gate ({len(barato.get('violaciones', []))} "
            f"violaciones) y el premium lo pasó"
        )
    if barato.get("longitud") and premium.get("longitud"):
        ratio = barato["longitud"] / premium["longitud"]
        if ratio < 0.6:
            señales.append(f"El barato produjo {ratio:.0%} del texto del premium")

    resultado["señales"] = señales
    resultado["requiere_revision"] = bool(señales)


def registrar(resultado: Dict) -> None:
    """Acumula el test en el registro histórico para análisis posterior."""
    historico: List[Dict] = []
    if os.path.exists(REGISTRO):
        try:
            with open(REGISTRO, encoding="utf-8") as f:
                historico = json.load(f)
        except Exception:
            logger.warning("[AB] Registro corrupto, se empieza uno nuevo")

    historico.append(resultado)
    os.makedirs(os.path.dirname(REGISTRO), exist_ok=True)
    with open(REGISTRO, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


def informe() -> Dict:
    """
    Resume el histórico: cuántas veces el modelo barato falló donde el premium no.

    Si la tasa es alta, el ahorro de routing a DeepSeek no compensa.
    """
    if not os.path.exists(REGISTRO):
        return {"tests": 0, "mensaje": "Sin tests registrados todavía"}

    with open(REGISTRO, encoding="utf-8") as f:
        historico = json.load(f)

    total = len(historico)
    con_señales = [t for t in historico if t.get("requiere_revision")]
    fallos_barato = [
        t for t in historico
        if t.get("variantes", {}).get("barato", {}).get("gate_passed") is False
    ]

    return {
        "tests": total,
        "con_diferencias_detectadas": len(con_señales),
        "fallos_gate_modelo_barato": len(fallos_barato),
        "tasa_fallo_barato": round(len(fallos_barato) / total, 4) if total else None,
        "recomendacion": (
            "Revisar el routing: el modelo barato falla con frecuencia"
            if total and len(fallos_barato) / total > 0.15
            else "El modelo barato se comporta dentro de lo aceptable"
        ),
    }
