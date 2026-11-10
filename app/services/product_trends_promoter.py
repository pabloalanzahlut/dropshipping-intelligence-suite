"""
product_trends_promoter — promueve candidatos de `product_trends` (lo que el monitor de
YouTube detecta) al catálogo de productos (`productos`, el pipeline de CLAUDE.md).

Sustituye a `autonomous_scheduler.job_classify_products`, que consultaba columnas que no
existen en `product_trends` (titulo, transcripcion_limpia, clasificacion) — las reales son
`product_name, niche, wow_factor, competitor_weaknesses` — y por eso nunca llegó a funcionar.

La "clasificación" real (HOT/WARM/COLD/DISCARD) depende del multiplicador sobre coste
landed, que no existe todavía para un candidato recién detectado (no tiene coste ni PVP).
Por eso este job no clasifica: decide si el candidato merece entrar al pipeline como
«candidato» (`product_catalog.crear`, que ya trae su propio gate — "nunca saltar un paso")
o si se descarta antes de llegar ahí.

Este módulo no importa `schedule`, así que `dashboard_server.py` puede importarlo en el
arranque del servidor sin arriesgar el proceso completo si esa librería no está instalada.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional

from app.services import product_catalog
from app.services.llm_router import chat

logger = logging.getLogger(__name__)

# Sentinela: -1 nunca es un id real de `productos` (AUTOINCREMENT empieza en 1).
# NULL en `promovido_a_producto_id` = todavía sin evaluar; -1 = evaluado y descartado;
# > 0 = promovido a ese producto.
_DESCARTADO = -1

SYSTEM_PROMPT = """Eres un scout de productos de dropshipping para GEM OS.

Recibes un candidato detectado en un vídeo de YouTube de un mentor de ecommerce: nombre,
nicho, "wow factor" declarado, margen estimado y debilidades de la competencia.

Decide si merece entrar al pipeline de validación (candidato) o descartarse ya, antes de
invertir tiempo en buscar proveedor y coste real.

Responde EXCLUSIVAMENTE con JSON, sin texto antes ni después:
{"veredicto": "promover" | "descartar", "motivo": "una frase, basada solo en los datos recibidos"}

No inventes datos de coste, margen real ni demanda que no te he dado — con lo que tienes
basta para decidir si vale la pena seguir investigando, no para clasificar HOT/WARM/COLD
(eso se calcula más adelante con coste y PVP reales, con reglas deterministas, no por IA)."""


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def candidatos_pendientes(db_path: str, limite: int = 10) -> List[Dict[str, Any]]:
    """Filas de `product_trends` que todavía no se evaluaron para promoción."""
    with _db(db_path) as conn:
        try:
            filas = conn.execute(
                "SELECT id, video_id, product_name, niche, wow_factor, estimated_margin, "
                "competitor_weaknesses FROM product_trends "
                "WHERE promovido_a_producto_id IS NULL LIMIT ?", (limite,)
            ).fetchall()
        except sqlite3.OperationalError:
            # La columna `promovido_a_producto_id` llega con la migración 22; si una BD
            # antigua todavía no migró, no hay nada pendiente que podamos distinguir.
            return []
        return [dict(f) for f in filas]


def _evaluar(fila: Dict[str, Any]) -> Dict[str, str]:
    contexto = {k: fila.get(k) for k in
                ("product_name", "niche", "wow_factor", "estimated_margin", "competitor_weaknesses")}
    texto = chat(task="clasificar_producto", system_prompt=SYSTEM_PROMPT,
                 user_message=json.dumps(contexto, ensure_ascii=False), max_tokens=300, temperature=0.0)
    if not texto:
        return {"veredicto": "sin_respuesta", "motivo": ""}
    try:
        inicio, fin = texto.find("{"), texto.rfind("}")
        datos = json.loads(texto[inicio:fin + 1]) if inicio != -1 and fin != -1 else {}
    except (ValueError, json.JSONDecodeError):
        return {"veredicto": "sin_respuesta", "motivo": texto[:200]}
    veredicto = str(datos.get("veredicto", "")).strip().lower()
    if veredicto not in ("promover", "descartar"):
        veredicto = "sin_respuesta"
    return {"veredicto": veredicto, "motivo": str(datos.get("motivo", ""))[:500]}


def _marcar(db_path: str, trend_id: int, producto_id: Optional[int]) -> None:
    with _db(db_path) as conn:
        conn.execute("UPDATE product_trends SET promovido_a_producto_id = ? WHERE id = ?",
                     (producto_id, trend_id))
        conn.commit()


def job_classify_products(db_path: Optional[str] = None, limite: int = 10) -> Dict[str, Any]:
    """Evalúa hasta `limite` candidatos pendientes; promueve, descarta o deja para el próximo ciclo."""
    if db_path is None:
        from app.config.path_manager import PathManager
        db_path = str(PathManager.get_paths()["db"])

    candidatos = candidatos_pendientes(db_path, limite)
    if not candidatos:
        logger.info("[PRODUCT_TRENDS_PROMOTER] Sin candidatos pendientes.")
        return {"evaluados": 0, "promovidos": 0, "descartados": 0, "sin_respuesta": 0}

    promovidos = descartados = sin_respuesta = 0
    for fila in candidatos:
        resultado = _evaluar(fila)
        if resultado["veredicto"] == "promover":
            try:
                producto = product_catalog.crear(db_path, {
                    "nombre": fila["product_name"],
                    "categoria": fila.get("niche") or "",
                    "origen_video_id": fila.get("video_id") or "",
                    "notas": (f"Promovido automáticamente desde product_trends #{fila['id']}. "
                              f"{resultado['motivo']}")[:2000],
                })
                _marcar(db_path, fila["id"], producto["id"])
                promovidos += 1
            except ValueError as exc:
                logger.warning(f"[PRODUCT_TRENDS_PROMOTER] No se pudo crear el candidato: {exc}")
                sin_respuesta += 1
        elif resultado["veredicto"] == "descartar":
            _marcar(db_path, fila["id"], _DESCARTADO)
            descartados += 1
        else:
            sin_respuesta += 1   # se queda NULL: se reintenta en el próximo ciclo

    logger.info(f"[PRODUCT_TRENDS_PROMOTER] {promovidos} promovidos, {descartados} descartados, "
                f"{sin_respuesta} sin respuesta (de {len(candidatos)}).")
    return {"evaluados": len(candidatos), "promovidos": promovidos,
            "descartados": descartados, "sin_respuesta": sin_respuesta}
