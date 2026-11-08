"""
Endpoints de la pantalla «Tienda»: conexión con Shopify, importación de AutoDS, estadísticas y el
contexto que recibe el agente IA.

Montar en la app principal con: app.include_router(tienda_router)
La sesión (GEM_OS_PASSWORD) la exige el middleware de la app; aquí no se devuelve nunca una clave.
"""
import asyncio
import logging
import threading
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile

from app.config.path_manager import PathManager
from app.services import autods_import, store_context, tienda_store
from app.services.shopify_client import ShopifyClient, ShopifyError, estado_credenciales

tienda_router = APIRouter(prefix="/api/tienda", tags=["tienda"])
log = logging.getLogger(__name__)

DB_PATH = str(PathManager.get_paths()["db"])
_SYNC: Dict[str, Any] = {"mensaje": "", "error": None, "resultado": None}
_SYNC_LOCK = threading.Lock()


def _ejecutar_sync(dias: int) -> None:
    def progreso(m: str) -> None:
        with _SYNC_LOCK:
            _SYNC["mensaje"] = m
    try:
        res = tienda_store.sincronizar_shopify(DB_PATH, ShopifyClient(), dias, progreso)
        with _SYNC_LOCK:
            _SYNC.update(resultado={k: res[k] for k in ("pedidos", "variantes", "dias", "avisos", "metricas_diarias")},
                         error=None, mensaje="Sincronización terminada.")
    except (ShopifyError, EnvironmentError, RuntimeError) as exc:
        log.warning("[TIENDA] Sincronización manual falló: %s", exc)
        with _SYNC_LOCK:
            _SYNC.update(error=str(exc), resultado=None, mensaje="")
    except Exception as exc:                                   # no tumbar el hilo sin dejar rastro
        log.exception("[TIENDA] Error inesperado sincronizando")
        with _SYNC_LOCK:
            _SYNC.update(error=f"Error inesperado: {exc}", resultado=None, mensaje="")


@tienda_router.get("/estado")
async def api_estado() -> Dict[str, Any]:
    """Estado de las conexiones (sin claves) y de la última sincronización."""
    est = tienda_store.estado(DB_PATH)
    with _SYNC_LOCK:
        est["sync"] = {**_SYNC, "corriendo": tienda_store.SYNC_LOCK.locked()}
    return est


@tienda_router.post("/probar")
async def api_probar() -> Dict[str, Any]:
    """Comprueba credenciales, tienda y permisos de Shopify sin guardar nada."""
    return await asyncio.get_running_loop().run_in_executor(None, tienda_store.probar_conexion)


@tienda_router.post("/sincronizar", status_code=202)
async def api_sincronizar(background_tasks: BackgroundTasks,
                          dias: int = Query(tienda_store.DIAS_SYNC_COMPLETA, ge=1, le=3650)) -> Dict[str, Any]:
    """Descarga pedidos y catálogo de Shopify en segundo plano."""
    est = estado_credenciales()
    if not est["configurada"]:
        raise HTTPException(status_code=422, detail=est["aviso"] or ("Faltan en .env: " + ", ".join(est["faltan"])))
    if tienda_store.SYNC_LOCK.locked():
        raise HTTPException(status_code=409, detail="Ya hay una sincronización en curso.")
    with _SYNC_LOCK:
        _SYNC.update(mensaje="Iniciando…", error=None, resultado=None)
    background_tasks.add_task(_ejecutar_sync, dias)
    return {"status": "started", "dias": dias}


@tienda_router.get("/resumen")
async def api_resumen(dias: int = Query(30, ge=1, le=365)) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    return {"tienda": await loop.run_in_executor(None, lambda: tienda_store.resumen(DB_PATH, dias)),
            "autods": await loop.run_in_executor(None, lambda: autods_import.resumen(DB_PATH, max(dias, 90)))}


@tienda_router.get("/contexto")
async def api_contexto(dias: int = Query(30, ge=1, le=365)) -> Dict[str, Any]:
    """Exactamente lo que recibe el agente IA como CONTEXTO TIENDA (transparencia)."""
    c = await asyncio.get_running_loop().run_in_executor(None, lambda: store_context.construir(DB_PATH, dias))
    return {"texto": c["texto"], "conectada": c["conectada"], "obsoleto": c["obsoleto"],
            "instruccion": store_context.INSTRUCCION}


async def _leer(archivo: UploadFile, tipo: str, coste_por_unidad: bool, formato_fecha: str) -> Dict[str, Any]:
    datos = await archivo.read(autods_import.MAX_BYTES + 1)
    if len(datos) > autods_import.MAX_BYTES:
        raise HTTPException(status_code=413, detail="El archivo pasa de 10 MB: exporta un periodo más corto.")
    if formato_fecha not in ("auto", "mdy"):
        raise HTTPException(status_code=422, detail="formato_fecha debe ser «auto» o «mdy».")
    try:
        return autods_import.parsear(datos, archivo.filename or "", tipo, coste_por_unidad, formato_fecha)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@tienda_router.post("/autods/previsualizar")
async def api_autods_previsualizar(archivo: UploadFile = File(...), tipo: str = Form("auto"),
                                   coste_por_unidad: bool = Form(False),
                                   formato_fecha: str = Form("auto")) -> Dict[str, Any]:
    """Lee el export de AutoDS y dice qué haría, sin escribir nada."""
    parsed = await _leer(archivo, tipo, coste_por_unidad, formato_fecha)
    return autods_import.previsualizar(DB_PATH, parsed)


@tienda_router.post("/autods/importar", status_code=201)
async def api_autods_importar(archivo: UploadFile = File(...), tipo: str = Form("auto"),
                              coste_por_unidad: bool = Form(False),
                              formato_fecha: str = Form("auto")) -> Dict[str, Any]:
    parsed = await _leer(archivo, tipo, coste_por_unidad, formato_fecha)
    return await asyncio.get_running_loop().run_in_executor(None, lambda: autods_import.aplicar(DB_PATH, parsed))
