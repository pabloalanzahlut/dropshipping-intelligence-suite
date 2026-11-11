"""
Endpoints de la pantalla «Importación masiva»: previsualiza y crea borradores en Shopify desde URLs.

Montar en la app principal con: app.include_router(importacion_router)
La sesión (GEM_OS_PASSWORD) la exige el middleware de la app.
"""
import asyncio
import logging
import os
import sqlite3
import threading
from contextlib import closing
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config.path_manager import PathManager
from app.database.connection import DatabaseConnection
from app.services.bulk_url_importer import BulkUrlImporter, MAX_PRODUCTOS_POR_LOTE, parsear_lineas
from app.services.shopify_client import ShopifyError, estado_credenciales

importacion_router = APIRouter(prefix="/api/importacion", tags=["importacion"])
log = logging.getLogger(__name__)

DB_PATH = str(PathManager.get_paths()["db"])
_LOCK = threading.Lock()


class Peticion(BaseModel):
    texto: str = Field(..., max_length=20000)
    moneda_costo: str = Field("USD", pattern=r"^[A-Za-z]{3}$")
    precio_psicologico: bool = True
    etiqueta_lote: str = Field("", max_length=40, pattern=r"^[\w\-]*$")
    sincronizar_hoja: bool = True


def _crear_importador() -> BulkUrlImporter:
    return BulkUrlImporter(DatabaseConnection(DB_PATH))


def _hoja_configurada() -> bool:
    sid = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    ruta = os.getenv("GOOGLE_CREDENTIALS_PATH", "ai_workspace/config/google_credentials.json")
    return bool(sid) and sid != "PENDIENTE" and os.path.exists(ruta)


def _fila(r: Dict[str, Any]) -> Dict[str, Any]:
    v = r.get("validacion") or {}
    return {"url": r["url"], "plataforma": r["plataforma"], "product_id": r.get("product_id", ""),
            "status": r["status"], "error": r.get("error"), "shopify_draft_id": r.get("shopify_draft_id"),
            "pvp": r.get("pvp"), "multiplicador": v.get("multiplicador"), "costo_landed": v.get("costo_landed"),
            "advertencias": v.get("advertencias", []), "titulo": r.get("titulo"),
            "imagenes": r.get("imagenes", 0), "variantes": r.get("variantes", 1), "hoja": r.get("hoja")}


def _items(p: Peticion) -> List[Dict[str, Any]]:
    items = parsear_lineas(p.texto)
    if not items:
        raise HTTPException(status_code=422, detail="Pega al menos una línea con una URL de producto.")
    if len(items) > MAX_PRODUCTOS_POR_LOTE:
        raise HTTPException(status_code=422, detail=f"Máximo {MAX_PRODUCTOS_POR_LOTE} productos por lote.")
    return items


def _exigir_shopify() -> None:
    est = estado_credenciales()
    if not est["configurada"]:
        raise HTTPException(status_code=422, detail=est["aviso"] or ("Faltan en .env: " + ", ".join(est["faltan"])))


async def _ejecutar(trabajo) -> List[Dict[str, Any]]:
    try:
        resultados = await asyncio.get_running_loop().run_in_executor(None, trabajo)
    except (ShopifyError, EnvironmentError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return [_fila(r) for r in resultados]


@importacion_router.get("/estado")
async def api_estado() -> Dict[str, Any]:
    """Qué hace falta para importar (sin claves)."""
    return {"shopify": estado_credenciales(), "hoja_configurada": _hoja_configurada(),
            "max_productos": MAX_PRODUCTOS_POR_LOTE}


@importacion_router.post("/previsualizar")
async def api_previsualizar(p: Peticion) -> Dict[str, Any]:
    """Calcula precio y comprueba reglas de cada línea sin crear nada."""
    items = _items(p)
    _exigir_shopify()
    filas = await _ejecutar(lambda: _crear_importador().previsualizar(items, p.moneda_costo.upper(),
                                                                       p.precio_psicologico))
    return {"resultados": filas}


@importacion_router.post("/importar", status_code=201)
async def api_importar(p: Peticion) -> Dict[str, Any]:
    """Crea los borradores en Shopify (uno por línea válida)."""
    items = _items(p)
    _exigir_shopify()
    if not _LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Ya hay una importación en curso.")
    try:
        filas = await _ejecutar(lambda: _crear_importador().importar_lote(
            items, p.moneda_costo.upper(), p.etiqueta_lote, p.precio_psicologico, p.sincronizar_hoja))
    finally:
        _LOCK.release()
    return {"resultados": filas, "creados": sum(1 for f in filas if f["status"] == "success")}


@importacion_router.get("/historial")
async def api_historial(limite: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        filas = conn.execute(
            "SELECT url_origen, plataforma, status, shopify_draft_id, error_msg, creada_at "
            "FROM importaciones_masivas ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return {"historial": [dict(f) for f in filas]}
