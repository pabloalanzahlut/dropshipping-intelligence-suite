"""
Higgsfield AI Client — Generación de videos TikTok/Reels sin filmar.

Higgsfield genera videos realistas de producto desde imagen + prompt de texto.
Uso en GEM OS: pasar imagen del proveedor + script guión → video listo para TikTok Ads.

API: https://higgsfield.ai  → Dashboard → API Keys
Variable de entorno: HIGGSFIELD_API_KEY
"""

import os
import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

HIGGSFIELD_BASE = "https://api.higgsfield.ai/v1"


def _headers() -> dict:
    key = os.getenv("HIGGSFIELD_API_KEY")
    if not key:
        raise EnvironmentError("[HIGGSFIELD] HIGGSFIELD_API_KEY no configurada en .env")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def generate_product_video(
    image_url: str,
    motion_prompt: str,
    duration_seconds: int = 5,
    aspect_ratio: str = "9:16",   # vertical para TikTok
) -> Optional[str]:
    """
    Genera un video de producto animado desde una imagen y un prompt de movimiento.

    Args:
        image_url: URL pública de la imagen del producto (proveedor/Shopify CDN)
        motion_prompt: Descripción del movimiento deseado en inglés.
                       Ejemplo: "product rotating slowly, hands demonstrating use,
                                 close-up macro shot, clean white background"
        duration_seconds: Duración del video (5 o 10 segundos)
        aspect_ratio: "9:16" (TikTok vertical) | "1:1" (cuadrado) | "16:9" (horizontal)

    Returns:
        URL del video generado, o None si falla.
    """
    payload = {
        "image_url": image_url,
        "prompt": motion_prompt,
        "duration": duration_seconds,
        "aspect_ratio": aspect_ratio,
        "style": "product_ad",
    }

    try:
        resp = requests.post(
            f"{HIGGSFIELD_BASE}/generate",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        job_id = resp.json().get("job_id")
        logger.info(f"[HIGGSFIELD] Job iniciado: {job_id}")
        return _poll_job(job_id)

    except EnvironmentError as e:
        logger.error(str(e))
        return None
    except requests.HTTPError as e:
        logger.error(f"[HIGGSFIELD] Error HTTP {resp.status_code}: {e}")
        return None
    except Exception as e:
        logger.error(f"[HIGGSFIELD] Error inesperado: {e}")
        return None


def _poll_job(job_id: str, max_wait: int = 180) -> Optional[str]:
    """Espera hasta que el job termine y devuelve la URL del video."""
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            resp = requests.get(
                f"{HIGGSFIELD_BASE}/jobs/{job_id}",
                headers=_headers(),
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")

            if status == "completed":
                video_url = data.get("output_url")
                logger.info(f"[HIGGSFIELD] Video listo: {video_url}")
                return video_url

            if status == "failed":
                logger.error(f"[HIGGSFIELD] Job falló: {data.get('error')}")
                return None

            logger.debug(f"[HIGGSFIELD] Estado: {status} — esperando...")
            time.sleep(10)

        except Exception as e:
            logger.error(f"[HIGGSFIELD] Error polling: {e}")
            return None

    logger.error(f"[HIGGSFIELD] Timeout esperando job {job_id}")
    return None


def build_motion_prompt(producto: str, hook_visual: str, idioma: str = "es") -> str:
    """
    Construye el prompt de movimiento óptimo para un producto dropshipping.
    Higgsfield funciona mejor con prompts en inglés — se traduce internamente.

    Args:
        producto: Nombre del producto
        hook_visual: El hook visual del guión (primeros 3 segundos)
        idioma: Idioma del input (se convierte a inglés para Higgsfield)
    """
    # Higgsfield requiere prompts en inglés
    template = (
        f"Product advertisement video for {producto}. "
        f"Opening shot: {hook_visual}. "
        "Smooth cinematic movement, close-up macro shots showing product details, "
        "clean minimal background, professional product photography style, "
        "vertical format 9:16 optimized for TikTok, "
        "high quality, no text overlays."
    )
    return template
