"""
LLM Router — Enrutamiento inteligente de modelos para GEM OS.

Regla: tareas críticas (validación financiera, clasificación) → Claude vía OpenRouter.
       tareas de volumen (fichas, copy, traducciones) → modelos baratos vía OpenRouter.
Sin costo de API externa adicional: todo pasa por la OPENROUTER_API_KEY ya configurada.
"""

import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

# ── Routing table ──────────────────────────────────────────────────────────────
# Tareas críticas: precisión > costo
CRITICAL_TASKS = {
    "validar_financiero",
    "clasificar_producto",
    "regla_3x",
    "revisar_specs",
}

MODEL_ROUTING = {
    # Críticas → Claude Sonnet via OpenRouter (sin necesitar ANTHROPIC_API_KEY)
    "default_critical": "anthropic/claude-sonnet-5-5",
    # Volumen alto → DeepSeek V3 (calidad excelente, ~21x más barato que Sonnet)
    "default_volume":   "deepseek/deepseek-chat-v3-0324",
    # Traducción / multilenguaje rápido
    "translate":        "google/gemini-flash-1.5",
    # Razonamiento complejo (specs técnicas difíciles)
    "reasoning":        "deepseek/deepseek-r1",
    # Fallback gratuito (tier básico OpenRouter)
    "free_fallback":    "meta-llama/llama-3.3-70b-instruct:free",
}

TASK_MODEL_MAP = {
    # ── Críticas: precisión máxima → Claude Sonnet ──────────────────────────
    "validar_financiero":    MODEL_ROUTING["default_critical"],
    "clasificar_producto":   MODEL_ROUTING["default_critical"],
    "regla_3x":              MODEL_ROUTING["default_critical"],
    "revisar_specs":         MODEL_ROUTING["default_critical"],
    # ── Volumen: texto rápido y barato → DeepSeek V3 ────────────────────────
    "limpiar_transcripcion": MODEL_ROUTING["default_volume"],
    "generar_ficha_shopify": MODEL_ROUTING["default_volume"],
    "generar_script_tiktok": MODEL_ROUTING["default_volume"],
    "aida_copy":             MODEL_ROUTING["default_volume"],
    "analizar_tendencia":    MODEL_ROUTING["default_volume"],
    "hook_matrix":           MODEL_ROUTING["default_volume"],
    "redactar_anuncio_meta": MODEL_ROUTING["default_volume"],
    # ── Multimodal: imagen → texto → Gemini Flash ───────────────────────────
    "analizar_imagen":       MODEL_ROUTING["translate"],   # gemini-flash-1.5 multimodal
    "extraer_specs_imagen":  MODEL_ROUTING["translate"],
    "detectar_categoria":    MODEL_ROUTING["translate"],
    # ── Traducción / multilenguaje ───────────────────────────────────────────
    "traducir_listing":      MODEL_ROUTING["translate"],
    "traducir_copy":         MODEL_ROUTING["translate"],
    # ── Razonamiento complejo ────────────────────────────────────────────────
    "investigar_nicho":      MODEL_ROUTING["reasoning"],
    "analizar_competencia":  MODEL_ROUTING["reasoning"],
}


def get_model(task: str) -> str:
    """Devuelve el model_id óptimo para la tarea dada."""
    return TASK_MODEL_MAP.get(task, MODEL_ROUTING["default_volume"])


def chat(
    task: str,
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> Optional[str]:
    """
    Llama al LLM correcto para la tarea vía OpenRouter.
    Usa OPENROUTER_API_KEY del .env — sin costos adicionales.

    Returns:
        Texto de la respuesta, o None si falla tras reintentos.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.error("[LLM_ROUTER] OPENROUTER_API_KEY no configurada")
        return None

    model = get_model(task)
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://gem-os.dropshipping",
        "X-Title": "GEM OS",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    for attempt in range(3):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            logger.info(f"[LLM_ROUTER] task={task} model={model} tokens={resp.json().get('usage', {})}")
            return content
        except requests.HTTPError as e:
            if resp.status_code == 429:
                import time; time.sleep(2 ** attempt)
            else:
                logger.error(f"[LLM_ROUTER] HTTP {resp.status_code} en intento {attempt+1}: {e}")
                break
        except Exception as e:
            logger.error(f"[LLM_ROUTER] Error intento {attempt+1}: {e}")
            if attempt == 2:
                # Último recurso: modelo free
                payload["model"] = MODEL_ROUTING["free_fallback"]

    return None
