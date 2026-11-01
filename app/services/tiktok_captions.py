"""
TikTok Captions & Hashtags — Generador de Subtítulos y Hashtags para TikTok
=============================================================================
GEM OS Suite — Genera captions optimizados y hashtags trending para videos TikTok.
"""

import logging
from typing import Dict, List, Optional
from app.core.ollama_pool import HybridInferencePool

logger = logging.getLogger(__name__)

# Hashtags base por categoría
HASHTAGS_BASE = {
    "general": [
        "#dropshipping", "#ecommerce", "#shopify", "#tiktokshop",
        "#emprendimiento", "#negociosonline", "#ventasonline",
    ],
    "moda": [
        "#moda", "#outfit", "#style", "#tendencias", "#lookdeldia",
    ],
    "belleza": [
        "#belleza", "#skincare", "#maquillaje", "#cosmetica", "#rutinadebelleza",
    ],
    "hogar": [
        "#hogar", "#decoracion", "#organizacion", "#hogarinteligente",
    ],
    "tecnologia": [
        "#tecnologia", "#gadgets", "#innovacion", "#smartphone",
    ],
    "fitness": [
        "#fitness", "#salud", "#ejercicio", "#vidassaludable", "#bienestar",
    ],
}

# Hashtags de tendencia general (actualizados periódicamente)
HASHTAGS_TRENDING = [
    "#parati", "#fyp", "#viral", "#tendencia",
    "#emprendedor", "#tips", "#aprendecontiktok",
]


def generar_caption(
    producto_nombre: str,
    categoria: str,
    hook: str = "",
    pool: Optional[HybridInferencePool] = None,
) -> str:
    """
    Genera un caption optimizado para TikTok usando el pool híbrido.

    Args:
        producto_nombre: Nombre del producto
        categoria: Categoría
        hook: Hook del guión (opcional)
        pool: Pool híbrido

    Returns:
        Caption generado
    """
    if pool is None:
        pool = HybridInferencePool()

    system_prompt = (
        "Eres un Community Manager experto en TikTok especializado en e-commerce.\n"
        "Genera un caption corto (máximo 150 caracteres) que:\n"
        "1. Enganche en la primera línea\n"
        "2. Incluya el beneficio principal\n"
        "3. Termine con un CTA claro\n"
        "4. Use emojis con moderación\n"
        "NO uses superlativos vacíos. Sé directo y persuasivo."
    )

    user_prompt = (
        f"Genera un caption para TikTok sobre:\n"
        f"Producto: {producto_nombre}\n"
        f"Categoría: {categoria}\n"
    )
    if hook:
        user_prompt += f"Hook: {hook}\n"
    user_prompt += "\nCaption (máx 150 caracteres):"

    try:
        texto = pool.execute_hybrid_query(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.4,
            max_tokens=200,
            operation_type="consulta_general",
        )
        return (texto or "").strip()[:200]
    except Exception as e:
        logger.warning(f"[CAPTIONS] Error generando caption: {e}")
        return f"Descubre {producto_nombre} - tu solución en {categoria}"


def generar_hashtags(
    categoria: str,
    producto_nombre: str = "",
    max_tags: int = 5,
) -> List[str]:
    """
    Genera hashtags relevantes para un producto/categoría.

    Args:
        categoria: Categoría del producto
        producto_nombre: Nombre del producto (opcional)
        max_tags: Número máximo de hashtags

    Returns:
        Lista de hashtags
    """
    import random

    # Normalizar categoría
    cat = categoria.lower().strip()
    hashtags = list(HASHTAGS_BASE.get("general"))

    # Agregar hashtags específicos de categoría
    for key, tags in HASHTAGS_BASE.items():
        if key in cat or cat in key:
            hashtags.extend(tags)

    # Agregar hashtags de tendencia
    hashtags.extend(HASHTAGS_TRENDING)

    # Agregar hashtag personalizado si hay nombre
    if producto_nombre:
        nombre_tag = f"#{producto_nombre.replace(' ', '').lower()[:20]}"
        hashtags.append(nombre_tag)

    # Quitar duplicados manteniendo orden
    seen = set()
    unique = []
    for tag in hashtags:
        if tag not in seen:
            seen.add(tag)
            unique.append(tag)

    # Seleccionar aleatoriamente
    random.shuffle(unique)
    return unique[:max_tags]


def generar_caption_con_hashtags(
    producto_nombre: str,
    categoria: str,
    hook: str = "",
    pool: Optional[HybridInferencePool] = None,
) -> Dict:
    """
    Genera caption + hashtags completos para un video TikTok.

    Returns:
        Dict con 'caption' y 'hashtags'
    """
    caption = generar_caption(producto_nombre, categoria, hook, pool)
    hashtags = generar_hashtags(categoria, producto_nombre)

    return {
        "caption": caption,
        "hashtags": hashtags,
        "hashtags_text": " ".join(hashtags),
        "publicacion": f"{caption}\n\n{' '.join(hashtags)}",
    }