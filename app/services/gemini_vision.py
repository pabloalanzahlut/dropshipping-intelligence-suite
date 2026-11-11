"""
Gemini Vision — Análisis de imágenes de producto para GEM OS.

Usa Gemini Flash (multimodal) para extraer specs técnicas desde fotos del proveedor.
Elimina la necesidad de copiar manualmente dimensiones, materiales y colores.

API: Google AI Studio → https://aistudio.google.com → API Keys
Variable de entorno: GOOGLE_AI_API_KEY
Alternativa: vía OpenRouter con model "google/gemini-2.5-flash"
"""

import os
import base64
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def analyze_product_image(
    image_url: str,
    task: str = "extract_specs",
) -> Optional[dict]:
    """
    Analiza una imagen de producto y extrae información estructurada.

    Args:
        image_url: URL pública de la imagen del proveedor
        task: "extract_specs" | "detect_category" | "check_restrictions"

    Returns:
        dict con la información extraída, o None si falla.
    """
    prompts = {
        "extract_specs": (
            "Analyze this product image and extract in JSON: "
            "{ 'product_name': str, 'material': str, 'dimensions_estimate': str, "
            "'weight_estimate_kg': float, 'color_variants': list, "
            "'has_loose_lithium_battery': bool, 'category': str, "
            "'wow_factor': str, 'target_audience': str }"
            "Be precise. If unsure, say null not invented values."
        ),
        "detect_category": (
            "What product category is this? Return JSON: "
            "{ 'category': str, 'niche': str, 'dropshipping_viable': bool, 'reason': str }"
        ),
        "check_restrictions": (
            "Check this product for dropshipping restrictions. Return JSON: "
            "{ 'has_loose_lithium_battery': bool, 'is_fragile': bool, "
            "'requires_certification': bool, 'estimated_weight_kg': float, "
            "'shipping_risk': 'low|medium|high', 'notes': str }"
        ),
    }

    prompt = prompts.get(task, prompts["extract_specs"])

    # Preferir OpenRouter si está disponible (ya configurado en el proyecto)
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        return _analyze_via_openrouter(image_url, prompt, openrouter_key)

    # Fallback: Google AI directo
    google_key = os.getenv("GOOGLE_AI_API_KEY")
    if google_key:
        return _analyze_via_google(image_url, prompt, google_key)

    logger.error("[GEMINI_VISION] Configura OPENROUTER_API_KEY o GOOGLE_AI_API_KEY en .env")
    return None


def _analyze_via_openrouter(image_url: str, prompt: str, api_key: str) -> Optional[dict]:
    """Llama a Gemini Flash vía OpenRouter (reutiliza la clave ya configurada)."""
    import json

    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt},
            ],
        }],
        "max_tokens": 512,
        "temperature": 0.0,
    }

    try:
        resp = requests.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://gem-os.dropshipping",
                "X-Title": "GEM OS Vision",
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()

        # Extraer JSON de la respuesta
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        result = json.loads(raw)
        logger.info(f"[GEMINI_VISION] Análisis completado vía OpenRouter")
        return result

    except Exception as e:
        logger.error(f"[GEMINI_VISION] Error OpenRouter: {e}")
        return None


def _analyze_via_google(image_url: str, prompt: str, api_key: str) -> Optional[dict]:
    """Llama a Gemini Flash directamente vía Google AI API."""
    import json

    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": _url_to_base64(image_url)}},
                {"text": prompt},
            ]
        }],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 512},
    }

    try:
        resp = requests.post(
            f"{GEMINI_BASE}/models/gemini-1.5-flash:generateContent?key={api_key}",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        result = json.loads(raw)
        logger.info(f"[GEMINI_VISION] Análisis completado vía Google AI")
        return result
    except Exception as e:
        logger.error(f"[GEMINI_VISION] Error Google AI: {e}")
        return None


def _url_to_base64(url: str) -> str:
    resp = requests.get(url, timeout=15)
    return base64.b64encode(resp.content).decode("utf-8")
