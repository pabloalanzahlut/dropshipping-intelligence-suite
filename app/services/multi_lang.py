"""
Multi-language Support — Soporte Multi-Idioma EN/PT/ES
========================================================
GEM OS Suite — Traducción de copys y guiones a múltiples idiomas.
"""

import logging
from typing import Dict, Optional
from app.core.ollama_pool import HybridInferencePool

logger = logging.getLogger(__name__)

# Mapa de idiomas soportados
IDIOMAS = {
    "es": {
        "nombre": "Español",
        "flag": "🇪🇸",
        "prompt_instruction": "Escribe el copy en ESPAÑOL neutro.",
        "aida_labels": {
            "attention": "Atención",
            "interest": "Interés",
            "decision": "Decisión",
            "action": "Acción",
        },
    },
    "en": {
        "nombre": "English",
        "flag": "🇬🇧",
        "prompt_instruction": "Write the copy in ENGLISH.",
        "aida_labels": {
            "attention": "Attention",
            "interest": "Interest",
            "decision": "Decision",
            "action": "Action",
        },
    },
    "pt": {
        "nombre": "Português",
        "flag": "🇧🇷",
        "prompt_instruction": "Escreva o copy em PORTUGUÊS (neutro).",
        "aida_labels": {
            "attention": "Atenção",
            "interest": "Interesse",
            "decision": "Decisão",
            "action": "Ação",
        },
    },
}


def traducir_copy(
    copy_data: Dict,
    idioma_destino: str,
    pool: Optional[HybridInferencePool] = None,
) -> Optional[Dict]:
    """
    Traduce un copy AIDA a otro idioma usando el pool híbrido.

    Args:
        copy_data: Dict con 'titulo' y 'descripcion'
        idioma_destino: Código ISO ('en', 'pt', 'es')
        pool: Pool híbrido (opcional, se crea uno nuevo si no se provee)

    Returns:
        Dict con copy traducido, o None si falla
    """
    if idioma_destino not in IDIOMAS:
        logger.warning(f"[I18N] Idioma no soportado: {idioma_destino}")
        return None

    lang = IDIOMAS[idioma_destino]
    titulo_orig = copy_data.get("titulo", "")
    desc_orig = copy_data.get("descripcion", "")

    if not titulo_orig and not desc_orig:
        logger.warning("[I18N] Copy vacío, no se puede traducir.")
        return None

    if pool is None:
        pool = HybridInferencePool()

    system_prompt = (
        "Eres un traductor profesional especializado en e-commerce y dropshipping.\n"
        f"{lang['prompt_instruction']}\n"
        "Conserva el formato Markdown, emojis y estructura AIDA.\n"
        "NO añadas ni elimines información técnica (precios, pesos, márgenes).\n"
        "Devuelve SOLO el texto traducido, sin explicaciones."
    )

    user_prompt = (
        f"Traduce el siguiente copy de ventas:\n\n"
        f"TÍTULO: {titulo_orig}\n\n"
        f"DESCRIPCIÓN:\n{desc_orig}\n\n"
        f"Idioma destino: {lang['nombre']} ({lang['flag']})"
    )

    try:
        texto = pool.execute_hybrid_query(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=2048,
            operation_type="consulta_general",
        )
        if not texto:
            return None

        # Separar título de descripción
        lineas = texto.split("\n")
        nuevo_titulo = titulo_orig
        nueva_desc = texto

        for linea in lineas:
            if linea.startswith("TÍTULO:") or linea.startswith("TITULO:"):
                nuevo_titulo = linea.split(":", 1)[1].strip()
                nueva_desc = "\n".join(
                    l for l in lineas if not l.startswith("TÍTULO:") and not l.startswith("TITULO:")
                ).strip()
                break

        return {
            "titulo": nuevo_titulo,
            "descripcion": nueva_desc,
            "idioma": idioma_destino,
            "idioma_nombre": lang["nombre"],
            "original": copy_data,
        }
    except Exception as e:
        logger.error(f"[I18N] Error traduciendo copy: {e}")
        return None


def obtener_idiomas_disponibles() -> Dict[str, str]:
    """Retorna dict con {codigo: nombre} de idiomas disponibles."""
    return {k: f"{v['flag']} {v['nombre']}" for k, v in IDIOMAS.items()}