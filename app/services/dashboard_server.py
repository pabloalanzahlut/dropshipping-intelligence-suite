"""
GEM OS Dashboard — Backend Principal Web (FastAPI)
===================================================
Servidor único listo para VPS Linux.
Puerto 8050 — configurable con DASHBOARD_PORT env var.

FASE 2 — Transformación Desktop → Plataforma Web:
- Elimina el hilo daemon de Tkinter; ahora es el proceso principal.
- Lifespan gestiona init BD + APScheduler para ingesta autónoma.
- Endpoints REST completos para todas las funciones del negocio.
- Jinja2 + Tailwind CDN para las 6 pestañas web.
"""
import asyncio
import json
import logging
import os
import re
import sqlite3
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import uvicorn
import jinja2
from urllib.parse import quote

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config.path_manager import PathManager
from app.database.connection import DatabaseConnection
from app.services import insights_service
from app.services import (agent_chat, agent_router, alerts, business_metrics, channel_store, daily_brief,
                          exports, log_viewer, mantenimiento, metrics_import, notifier,
                          product_catalog, store_context, tienda_store, transcript_store, web_auth)

log = logging.getLogger(__name__)
log_viewer.configurar_log_servidor(PathManager.get_paths()["logs"] / "servidor.log")

# ── Constantes ───────────────────────────────────────────────────────────────
_GEM_PATHS = PathManager.get_paths()
DB_PATH = str(_GEM_PATHS["db"])
QUEUE_STATE_PATH = str(_GEM_PATHS["queue"])
CHANNELS_JSON_PATH = str(_GEM_PATHS["config"])
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "47821"))
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
IMG_DIR = _GEM_PATHS["data"] / "imagenes_producto"

# ── Bus SSE de logs en tiempo real ──────────────────────────────────────────────
# Circular buffer compartido: el engine escribe, los clientes SSE leen
_LOG_BUS: deque = deque(maxlen=200)
_LOG_BUS_LOCK = threading.Lock()

# Estado actual del pipeline (canal procesando ahora)
_PIPELINE_STATE: Dict[str, Any] = {
    "active": False,
    "current_channel": None,
    "current_video": None,
    "processed": 0,
    "total": 0,
    "started_at": None,
}
_PIPELINE_LOCK = threading.Lock()


def push_log(msg: str, level: str = "INFO") -> None:
    """Escribe una línea en el bus SSE. Llamar desde el engine o cualquier servicio."""
    entry = {"ts": time.strftime("%H:%M:%S"), "level": level, "msg": msg}
    with _LOG_BUS_LOCK:
        _LOG_BUS.append(entry)


def set_pipeline_state(**kwargs) -> None:
    """Actualiza el estado del pipeline en tiempo real."""
    with _PIPELINE_LOCK:
        _PIPELINE_STATE.update(kwargs)


# Una sola ingesta de KB a la vez (botón web, scheduler horario o escritorio)
_INGEST_LOCK = threading.Lock()

# Estado de la sincronización de transcripciones (YouTubeChannelMonitor)
_TRANS_SYNC: Dict[str, Any] = {"running": False, "msg": "", "result": None, "error": None}
_TRANS_SYNC_LOCK = threading.Lock()
_trans_monitor = None  # monitor en curso (para cancelar)


# Inyectar push_log en el engine para que emita eventos sin importar circular
os.environ.setdefault("GEM_PUSH_LOG", "1")

# Regex de validación de URLs de canal YouTube (misma fuente de verdad que el engine)
_YOUTUBE_CHANNEL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/"
    r"(?:@[A-Za-z0-9._-]+|channel/UC[A-Za-z0-9_-]+|c/[A-Za-z0-9_.-]+|user/[A-Za-z0-9_.-]+)"
    r"/?$"
)

# ── Lazy engine singleton ────────────────────────────────────────────────────
_engine = None
_engine_lock = threading.Lock()


def _engine_log_adapter(msg: str) -> None:
    """Callback del engine: vuelca sus mensajes al bus SSE y deduce el paso actual."""
    text = str(msg)
    level = "ERROR" if text.startswith("❌") else "WARNING" if text.startswith("⚠") else "INFO"
    push_log(text, level)

    if "Escaneando" in text and ":" in text:
        set_pipeline_state(current_channel=text.split(":", 1)[1].strip())
    elif "Extrayendo valor" in text and ":" in text:
        set_pipeline_state(current_video=text.split(":", 1)[1].strip())
    elif "Guardado en KB" in text:
        with _PIPELINE_LOCK:
            _PIPELINE_STATE["processed"] = _PIPELINE_STATE.get("processed", 0) + 1


def _get_engine():
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                try:
                    from app.services.provider_monitor_engine import ProviderMonitorEngine
                    _engine = ProviderMonitorEngine()
                    _engine.log_callback = _engine_log_adapter
                except Exception as exc:
                    log.warning(f"[SERVER] ProviderMonitorEngine no disponible: {exc}")
    return _engine


# ── APScheduler ──────────────────────────────────────────────────────────────
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    _scheduler: Optional[Any] = AsyncIOScheduler()
    _scheduler_available = True
except ImportError:
    _scheduler = None
    _scheduler_available = False


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa BD, engine y scheduler al arrancar el servidor web."""
    try:
        DatabaseConnection(DB_PATH)
        log.info("[SERVER] Base de datos inicializada (schema + migrations).")
    except Exception as exc:
        log.error(f"[SERVER] Error al inicializar BD: {exc}")

    if os.getenv("GEM_OS_HOST", "127.0.0.1") not in ("127.0.0.1", "localhost") and not web_auth.activa():
        log.warning("[SERVER] El servidor está accesible desde la red SIN contraseña: define GEM_OS_PASSWORD en .env.")
    engine = _get_engine()

    # Sincronizar kb_index.json al arrancar (en background, no bloquea)
    try:
        import asyncio
        from app.services.kb_index_sync import KBIndexSync
        loop = asyncio.get_event_loop()

        def _initial_kb_sync():
            try:
                KBIndexSync(db_path=DB_PATH).sync()
                log.info("[SERVER] kb_index.json sincronizado al arrancar.")
            except Exception as _e:
                log.warning(f"[SERVER] KBIndexSync al arrancar: {_e}")

        loop.run_in_executor(None, _initial_kb_sync)
    except Exception:
        pass

    def _scheduled_ingest() -> None:
        # Si ya hay una ingesta en curso (p. ej. lanzada a mano), se salta este ciclo
        if _TRANS_SYNC["running"]:
            log.info("[SERVER] Ingesta KB omitida: hay una sincronización de transcripciones "
                     "(comparten el límite de YouTube).")
            return
        if not _INGEST_LOCK.acquire(blocking=False):
            log.info("[SERVER] Ingesta programada omitida: ya hay una en curso.")
            return
        try:
            engine.run_global_ingestion()
        finally:
            _INGEST_LOCK.release()

    def _scheduled_transcripts() -> None:
        """Lote automático de transcripciones. Se salta si la ingesta KB está trabajando
        (misma IP, mismo límite de YouTube); el monitor respeta además el enfriamiento tras un 429."""
        if _INGEST_LOCK.locked():
            log.info("[SERVER] Sync de transcripciones omitida: ingesta KB en curso.")
            return
        if _reservar_sync_transcripciones("automática"):
            _ejecutar_sync_transcripciones()

    def _scheduled_backup() -> None:
        """Copia diaria de la base de datos; conserva las 14 últimas."""
        try:
            from app.services import kb_maintenance
            ruta = kb_maintenance.backup_db(DB_PATH, "auto")
            copias = sorted(Path(ruta).parent.glob(f"{Path(DB_PATH).stem}_auto_*.db"))
            for vieja in copias[:-14]:
                vieja.unlink(missing_ok=True)
            log.info(f"[SERVER] Copia de seguridad automática: {ruta}")
        except Exception as exc:
            log.warning(f"[SERVER] Copia de seguridad automática falló: {exc}")

    def _scheduled_alertas() -> None:
        """Revisión automática (caja, ROAS, canales, sincronización, copias, IA) y aviso fuera de la app."""
        try:
            r = alerts.evaluar(DB_PATH, CHANNELS_JSON_PATH)
            log.info(f"[SERVER] Alertas revisadas: {r['vigentes']} vigentes, {r['nuevas']} nuevas.")
        except Exception as exc:
            log.warning(f"[SERVER] Revisión de alertas falló: {exc}")
            return
        try:
            notifier.enviar_pendientes(DB_PATH)
        except Exception as exc:
            log.warning(f"[SERVER] Avisos externos fallaron: {exc}")

    def _scheduled_resumen() -> None:
        """Resumen del día (08:00)."""
        try:
            alerts.evaluar(DB_PATH, CHANNELS_JSON_PATH)
            daily_brief.generar(DB_PATH, CHANNELS_JSON_PATH)
            log.info("[SERVER] Resumen diario generado.")
        except Exception as exc:
            log.warning(f"[SERVER] Resumen diario falló: {exc}")

    def _scheduled_mantenimiento() -> None:
        """Domingo 04:00 (tras la copia de las 03:30): integridad, optimización, temporales, canales."""
        try:
            r = mantenimiento.ejecutar(DB_PATH, CHANNELS_JSON_PATH)
            log.info(f"[SERVER] Mantenimiento semanal: integridad_ok={r.get('integridad_ok')} "
                     f"errores={len(r.get('errores', []))} ({r.get('duracion_s')} s)")
            alerts.evaluar(DB_PATH, CHANNELS_JSON_PATH)
        except Exception as exc:
            log.warning(f"[SERVER] Mantenimiento semanal falló: {exc}")

    def _scheduled_classify_products() -> None:
        """Cada 6h: promueve candidatos prometedores de product_trends al catálogo de
        productos, o los descarta. Sustituye a autonomous_scheduler.py, que nunca llegó a
        arrancar solo y además consultaba columnas que no existen (ver product_trends_promoter.py)."""
        try:
            from app.services import product_trends_promoter
            r = product_trends_promoter.job_classify_products(DB_PATH)
            log.info(f"[SERVER] Clasificación automática: {r}")
        except Exception as exc:
            log.warning(f"[SERVER] Clasificación automática falló: {exc}")

    def _scheduled_self_improve() -> None:
        """03:00: propone ajustes a partir de métricas reales (nunca los aplica)."""
        try:
            from app.services import self_improve
            r = self_improve.analizar_y_proponer(dias=21, db_path=DB_PATH)
            if r.get("propuestas_generadas"):
                log.info(f"[SERVER] Self-improve: nueva propuesta #{r.get('propuesta_id')} pendiente de revisión.")
            else:
                log.info(f"[SERVER] Self-improve: sin propuestas ({r.get('motivo')}).")
        except Exception as exc:
            log.warning(f"[SERVER] Self-improve falló: {exc}")

    if _scheduler_available and _scheduler is not None and engine is not None:
        _scheduler.add_job(_scheduled_mantenimiento, "cron", day_of_week="sun", hour=4, minute=0,
                           id="mantenimiento_semanal", replace_existing=True, misfire_grace_time=24 * 3600,
                           coalesce=True)
        _scheduler.add_job(_scheduled_alertas, "interval", minutes=15, id="alertas_auto", max_instances=1,
                           misfire_grace_time=600, replace_existing=True,
                           next_run_time=datetime.now() + timedelta(seconds=45))
        _scheduler.add_job(_scheduled_resumen, "cron", hour=8, minute=0, id="resumen_diario",
                           replace_existing=True, misfire_grace_time=6 * 3600, coalesce=True)
        _scheduler.add_job(
            _scheduled_ingest,
            "interval",
            hours=1,
            id="auto_ingest",
            max_instances=1,
            misfire_grace_time=300,
            replace_existing=True,
        )
        # Transcripciones: lotes de 15 cada 45 min (YouTube corta a ~15-20 seguidas).
        # GEM_OS_AUTO_TRANSCRIPTS_MIN=0 la desactiva.
        minutos = int(os.getenv("GEM_OS_AUTO_TRANSCRIPTS_MIN", "45") or 0)
        if minutos > 0:
            _scheduler.add_job(
                _scheduled_transcripts, "interval", minutes=minutos, id="transcripts_auto",
                max_instances=1, misfire_grace_time=600, replace_existing=True,
                next_run_time=datetime.now() + timedelta(minutes=2),
            )
        # Shopify → SQLite cada hora (no hace nada si Shopify no está configurado). GEM_OS_AUTO_SHOPIFY_MIN=0 la desactiva.
        min_shopify = int(os.getenv("GEM_OS_AUTO_SHOPIFY_MIN", "60") or 0)
        if min_shopify > 0:
            _scheduler.add_job(
                lambda: tienda_store.sync_si_configurada(DB_PATH), "interval", minutes=min_shopify,
                id="shopify_sync", max_instances=1, misfire_grace_time=600, replace_existing=True,
                next_run_time=datetime.now() + timedelta(minutes=3),
            )
        # Candidatos de product_trends → catálogo de productos, cada 6h.
        _scheduler.add_job(_scheduled_classify_products, "interval", hours=6, id="classify_products_auto",
                           max_instances=1, misfire_grace_time=1800, replace_existing=True,
                           next_run_time=datetime.now() + timedelta(minutes=5))
        # Self-improve: propuestas de ajuste a las 03:00 (nunca aplica nada).
        _scheduler.add_job(_scheduled_self_improve, "cron", hour=3, minute=0, id="self_improve_auto",
                           replace_existing=True, misfire_grace_time=3 * 3600, coalesce=True)
        # Copia de seguridad diaria (03:30) y una al arrancar si la última tiene más de 24 h
        _scheduler.add_job(_scheduled_backup, "cron", hour=3, minute=30, id="backup_auto",
                           replace_existing=True, misfire_grace_time=3600)
        ultimas = sorted((Path(DB_PATH).resolve().parent.parent / "backups").glob(
            f"{Path(DB_PATH).stem}_auto_*.db"))
        if not ultimas or time.time() - ultimas[-1].stat().st_mtime > 86400:
            # misfire_grace_time: al arrancar el servidor está ocupado y, con el margen por
            # defecto (1 s), APScheduler descartaba esta tarea por "llegar tarde".
            _scheduler.add_job(_scheduled_backup, "date", id="backup_inicial",
                               run_date=datetime.now() + timedelta(seconds=30), replace_existing=True,
                               misfire_grace_time=3600)
        _scheduler.start()
        log.info("[SERVER] APScheduler iniciado — ingesta KB 1h, transcripciones "
                 f"{minutos or 'desactivadas'} min, copia de seguridad diaria.")

    yield

    if _scheduler_available and _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("[SERVER] Scheduler detenido.")


# ── App FastAPI ───────────────────────────────────────────────────────────────
app = FastAPI(title="GEM OS Dashboard", version="3.7.2", lifespan=lifespan)

# Static files
_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Webhooks Shopify
try:
    from app.routes.webhooks import webhooks_router
    app.include_router(webhooks_router)
    log.info("[SERVER] Webhooks Shopify montados en /webhooks")
except Exception as _wh_err:
    log.warning(f"[SERVER] Webhooks no disponibles: {_wh_err}")

# Tienda: Shopify (API) + AutoDS (importación) → estadísticas y contexto del agente
try:
    from app.routes.tienda import tienda_router
    app.include_router(tienda_router)
    log.info("[SERVER] API de la tienda montada en /api/tienda")
except Exception as _tienda_err:
    log.warning(f"[SERVER] API de la tienda no disponible: {_tienda_err}")

# ── Jinja2 Templates ─────────────────────────────────────────────────────────
_jinja_env: Optional[jinja2.Environment] = (
    jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
        cache_size=0,
        auto_reload=True,
    )
    if TEMPLATES_DIR.exists()
    else None
)


def _render(request: Request, template: str, ctx: Dict[str, Any] = None):
    if _jinja_env is None:
        return HTMLResponse(content=_FALLBACK_HTML)
    try:
        tmpl = _jinja_env.get_template(template)
        content = tmpl.render(request=request, auth_activa=web_auth.activa(), **(ctx or {}))
        return HTMLResponse(content=content)
    except jinja2.TemplateNotFound:
        return HTMLResponse(content=_FALLBACK_HTML)


# ── Pydantic Models ───────────────────────────────────────────────────────────
class ChannelIn(BaseModel):
    url: str
    nombre: str
    tags: str = ""
    idioma: str = "es"
    prioridad: int = 5
    max_videos_scan: int = 30


class ValidarIn(BaseModel):
    sku: str
    costo_origen: float
    costo_envio: float = 0.0      # el multiplicador se mide sobre coste landed = producto + envío
    peso_kg: float = 0.0
    pvp_sugerido: Optional[float] = None


class CopyIn(BaseModel):
    nombre_producto: str
    categoria: str
    costo_origen: float
    pvp: float
    peso_kg: float = 0.0


class TikTokIn(BaseModel):
    nombre_producto: str
    categoria: str
    patron_hook: str = "story-telling"
    duracion_segundos: int = 60


class KBQueryIn(BaseModel):
    pregunta: str
    agente: str = "auto"      # "auto" = el router elige según el tipo de pregunta
    proyecto: str = "kb_consulta"


class ChatTurnoIn(BaseModel):
    rol: str = "user"         # "user" o "agente"
    texto: str = ""


class ChatIn(BaseModel):
    """Una vuelta de conversación: la pregunta y los turnos anteriores que le dan contexto."""
    pregunta: str = ""
    agente: str = "auto"
    historial: List[ChatTurnoIn] = []


class PublicarTikTokIn(BaseModel):
    producto: str
    categoria: str
    hook: str
    cuerpo: str
    cta: str
    patron_hook: str = ""
    duracion_segundos: int = 0


# ── Helpers ───────────────────────────────────────────────────────────────────
def _get_db() -> DatabaseConnection:
    return DatabaseConnection(DB_PATH)


def _load_queue_state() -> Dict[str, Any]:
    path = Path(QUEUE_STATE_PATH)
    if not path.exists():
        return {"channels": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"channels": []}


def _load_channels_json() -> List[Dict[str, Any]]:
    path = Path(CHANNELS_JSON_PATH)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_channels_json(channels: List[Dict[str, Any]]) -> None:
    """Escritura atómica: archivo temporal + reemplazo (no deja el JSON a medias)."""
    path = Path(CHANNELS_JSON_PATH)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(channels, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _get_kb_count() -> int:
    try:
        db = _get_db()
        with db.get_connection() as conn:
            cur = conn.cursor()
            total = 0
            for table in ("product_trends", "conversion_formulas", "operations_traffic"):
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                total += cur.fetchone()[0]
        return total
    except sqlite3.Error:
        return 0


def _get_total_videos() -> int:
    try:
        db = _get_db()
        with db.get_connection() as conn:
            cur = conn.cursor()
            # Vídeos con conocimiento extraído por IA (no las transcripciones sueltas)
            cur.execute("SELECT COUNT(*) FROM video_sources WHERE platform NOT IN (?, 'fuera_de_tema')",
                        (transcript_store.TRANSCRIPT_PLATFORM,))
            return cur.fetchone()[0]
    except sqlite3.Error:
        return 0


def _get_latest_insights(limit: int = 5) -> List[Dict[str, Any]]:
    try:
        db = _get_db()
        with db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT t.product_name, t.niche, t.wow_factor,
                       v.channel_name, t.validated_at
                FROM product_trends t
                LEFT JOIN video_sources v ON t.video_id = v.video_id
                ORDER BY t.validated_at DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cur.fetchall()]
    except sqlite3.Error:
        return []


# La lógica de insights vive en app/services/insights_service.py (la comparten la web y el escritorio).
# Estos envoltorios conservan los nombres de siempre y fijan la base de datos del servidor.
_INSIGHTS_UNION = insights_service.INSIGHTS_UNION
_INSIGHT_TIPOS = insights_service.INSIGHT_TIPOS
_STOPWORDS_BUSQUEDA = insights_service.STOPWORDS_BUSQUEDA
_TIPO_PREFERIDO = insights_service.TIPO_PREFERIDO


def _like_escape(term: str) -> str:
    return insights_service.like_escape(term)


def _limpiar_preview(texto: Any, max_chars: int) -> str:
    return insights_service.limpiar_preview(texto, max_chars)


def _query_insights(tipo: str = "", buscar: str = "", canal: str = "",
                    limite: int = 50, offset: int = 0,
                    preview_chars: int = 220) -> Dict[str, Any]:
    """Insights de las 3 tablas KB con filtros y paginación. Devuelve {items, total}."""
    return insights_service.query_insights(DB_PATH, tipo, buscar, canal, limite, offset, preview_chars)


def _insights_resumen() -> Dict[str, Any]:
    """Totales por tipo y por canal (los contadores de la página Insights)."""
    return insights_service.insights_resumen(DB_PATH)


def _get_kb_insights_combined(limit: int = 50) -> List[Dict[str, Any]]:
    """Muestra equilibrada de las 3 tablas (para el contexto del agente KB)."""
    return insights_service.kb_insights_combined(DB_PATH, limit)


def _terminos_busqueda(pregunta: str) -> List[str]:
    return insights_service.terminos_busqueda(pregunta)


def _insights_relevantes(pregunta: str, tipo_pregunta: str = "general",
                         limite: int = 24) -> List[Dict[str, Any]]:
    """Los insights de la KB que más se parecen a la pregunta."""
    return insights_service.insights_relevantes(DB_PATH, pregunta, tipo_pregunta, limite)


def _contexto_kb_para(pregunta: str, tipo_pregunta: str = "general", limite: int = 24):
    """(texto de contexto numerado, lista de fuentes) para inyectar al agente."""
    return insights_service.contexto_kb_para(DB_PATH, pregunta, tipo_pregunta, limite)


def _fuentes_citadas(respuesta: str, fuentes: List[Dict[str, Any]], minimo: int = 4) -> List[Dict[str, Any]]:
    """Fuentes que el agente citó con [n]; si no citó ninguna, las más relevantes."""
    return insights_service.fuentes_citadas(respuesta, fuentes, minimo)


_INSTRUCCION_FUENTES = (
    "Responde SOLO con lo que aparece en el CONTEXTO KB. Cita cada dato con su número entre "
    "corchetes, por ejemplo [3], y menciona el canal de origen. Si el contexto no tiene la "
    "respuesta, dilo en vez de inventar."
)


# ═══════════════════════════════════════════════════════════════════════════════
# PESTAÑAS WEB (Fase 3 — Jinja2 Templates)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return _render(request, "dashboard.html")


@app.get("/validador", response_class=HTMLResponse)
async def validador_page(request: Request):
    return _render(request, "validador.html")


@app.get("/youtube", response_class=HTMLResponse)
async def youtube_page(request: Request):
    return _render(request, "youtube.html")


@app.get("/copys", response_class=HTMLResponse)
async def copys_page(request: Request):
    return _render(request, "copys.html")


@app.get("/tiktok", response_class=HTMLResponse)
async def tiktok_page(request: Request):
    return _render(request, "tiktok.html")


@app.get("/imagenes", response_class=HTMLResponse)
async def imagenes_page(request: Request):
    return _render(request, "imagenes.html")


@app.get("/insights", response_class=HTMLResponse)
async def insights_page(request: Request):
    return _render(request, "insights.html")


@app.get("/agente", response_class=HTMLResponse)
async def agente_page(request: Request):
    return _render(request, "agente.html")


@app.get("/historial", response_class=HTMLResponse)
async def historial_page(request: Request):
    return _render(request, "historial.html")


@app.get("/productos", response_class=HTMLResponse)
async def productos_page(request: Request):
    return _render(request, "productos.html")


@app.get("/negocio", response_class=HTMLResponse)
async def negocio_page(request: Request):
    return _render(request, "negocio.html")


@app.get("/tienda", response_class=HTMLResponse)
async def tienda_page(request: Request):
    return _render(request, "tienda.html")


@app.get("/transcripciones", response_class=HTMLResponse)
async def transcripciones_page(request: Request):
    return _render(request, "transcripciones.html")


@app.get("/gobernanza", response_class=HTMLResponse)
async def gobernanza_page(request: Request):
    return _render(request, "gobernanza.html")


@app.get("/enrutador", response_class=HTMLResponse)
async def enrutador_page(request: Request):
    return _render(request, "enrutador.html")


@app.get("/configuracion", response_class=HTMLResponse)
async def configuracion_page(request: Request):
    return _render(request, "configuracion.html")


# ═══════════════════════════════════════════════════════════════════════════════
# API — MÉTRICAS Y ESTADO
# ═══════════════════════════════════════════════════════════════════════════════

def _get_canales_favoritos() -> List[Dict[str, Any]]:
    """Lee canales desde v_resumen_canales para el dashboard."""
    try:
        import sqlite3 as _sq
        with _sq.connect(DB_PATH) as conn:
            conn.row_factory = _sq.Row
            rows = conn.execute(
                "SELECT nombre, handle, tags, idioma, prioridad, videos_descargados, ultimo_video_procesado FROM v_resumen_canales ORDER BY prioridad, nombre"
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []

def _get_videos_favoritos_count() -> int:
    try:
        import sqlite3 as _sq
        with _sq.connect(DB_PATH) as conn:
            return conn.execute("SELECT COUNT(*) FROM videos_favoritos").fetchone()[0]
    except Exception:
        return 0


@app.get("/api/metrics")
async def api_metrics() -> Dict[str, Any]:
    queue = _load_queue_state()
    queue_channels = queue.get("channels", [])
    tasks_pending = sum(1 for ch in queue_channels if ch.get("status") != "completed")
    tasks_done    = sum(1 for ch in queue_channels if ch.get("status") == "completed")
    canales = _get_canales_favoritos()
    return {
        "total_videos":       _get_total_videos(),
        "videos_favoritos":   _get_videos_favoritos_count(),
        "tasks_pending":      tasks_pending,
        "tasks_done":         tasks_done,
        "kb_count":           _get_kb_count(),
        "canales_count":      len(canales),
        "channels":           canales,
        "insights":           _get_latest_insights(5),
    }


@app.get("/api/status")
async def api_status() -> Dict[str, Any]:
    engine = _get_engine()
    engine_status = {}
    if engine is not None and hasattr(engine, "get_engine_status"):
        try:
            engine_status = engine.get_engine_status()
        except Exception:
            pass
    scheduler_jobs = []
    if _scheduler_available and _scheduler and _scheduler.running:
        scheduler_jobs = [
            {"id": j.id, "next_run": str(j.next_run_time)}
            for j in _scheduler.get_jobs()
        ]
    return {
        "engine": engine_status if engine else "unavailable",
        "scheduler": {
            "running": bool(_scheduler_available and _scheduler and _scheduler.running),
            "jobs": scheduler_jobs,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# API — CANALES YOUTUBE
# ═══════════════════════════════════════════════════════════════════════════════

class CanalPatchIn(BaseModel):
    url: str
    nombre: Optional[str] = None
    activo: Optional[bool] = None
    prioridad: Optional[int] = None
    idioma: Optional[str] = None
    tags: Optional[str] = None
    filtro_tema: Optional[bool] = None
    max_videos_scan: Optional[int] = None


class CanalUrlIn(BaseModel):
    url: str


@app.get("/api/channels")
async def get_channels() -> List[Dict[str, Any]]:
    """Todos los canales (mentores del JSON + favoritos de la BD) como UNA lista, con su
    estado, filtro de tema y número de transcripciones."""
    return channel_store.listar(CHANNELS_JSON_PATH, DB_PATH)


@app.post("/api/channels", status_code=201)
async def add_channel(channel: ChannelIn) -> Dict[str, Any]:
    try:
        return channel_store.agregar(
            CHANNELS_JSON_PATH, DB_PATH, channel.url, channel.nombre, channel.tags,
            channel.idioma, channel.prioridad, channel.max_videos_scan)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.patch("/api/channels")
async def patch_channel(cambios: CanalPatchIn) -> Dict[str, Any]:
    """Activa/desactiva, renombra, cambia prioridad, idioma, etiquetas o el filtro de tema."""
    try:
        return channel_store.actualizar(
            CHANNELS_JSON_PATH, DB_PATH, cambios.url,
            cambios.model_dump(exclude={"url"}, exclude_none=True))
    except KeyError:
        raise HTTPException(status_code=404, detail="Canal no encontrado.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.delete("/api/channels")
async def delete_channel(url: str = Query(..., max_length=300)) -> Dict[str, Any]:
    """Quita el canal de la lista. No borra sus transcripciones ni su KB."""
    if not channel_store.eliminar(CHANNELS_JSON_PATH, DB_PATH, url):
        raise HTTPException(status_code=404, detail="Canal no encontrado.")
    return {"status": "deleted", "url": url}


@app.post("/api/channels/verificar")
async def verify_channel(body: CanalUrlIn) -> Dict[str, Any]:
    """Comprueba que el canal existe (detecta URLs rotas, p. ej. un 404)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: channel_store.verificar(DB_PATH, body.url))


@app.get("/api/channels/favoritos")
async def get_canales_favoritos() -> List[Dict[str, Any]]:
    """Retorna canales_favoritos con metadata extendida desde la DB."""
    try:
        import sqlite3 as _sq
        with _sq.connect(DB_PATH) as conn:
            conn.row_factory = _sq.Row
            rows = conn.execute(
                """SELECT nombre, handle, url, idioma, especialidad, tags,
                          prioridad, activo, video_count, notas
                   FROM canales_favoritos ORDER BY prioridad, nombre"""
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/videos/favoritos")
async def get_videos_favoritos(limite: int = 100) -> List[Dict[str, Any]]:
    """Retorna videos_favoritos desde la DB."""
    try:
        import sqlite3 as _sq
        with _sq.connect(DB_PATH) as conn:
            conn.row_factory = _sq.Row
            rows = conn.execute(
                """SELECT video_id, titulo, canal, url, razon, tags,
                          transcripcion_procesada, guardado_at
                   FROM videos_favoritos ORDER BY guardado_at DESC LIMIT ?""",
                (limite,)
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/playlists")
async def get_playlists() -> List[Dict[str, Any]]:
    """Retorna playlists_favoritas desde la DB."""
    try:
        import sqlite3 as _sq
        with _sq.connect(DB_PATH) as conn:
            conn.row_factory = _sq.Row
            rows = conn.execute(
                """SELECT playlist_id, titulo, canal, url, es_privada,
                          tags, activa, video_count, agregada_at
                   FROM playlists_favoritas ORDER BY activa DESC, titulo"""
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/canales/resumen")
async def get_resumen_canales() -> List[Dict[str, Any]]:
    """Retorna la vista v_resumen_canales."""
    try:
        import sqlite3 as _sq
        with _sq.connect(DB_PATH) as conn:
            conn.row_factory = _sq.Row
            rows = conn.execute(
                "SELECT * FROM v_resumen_canales ORDER BY prioridad, nombre"
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# API — INGESTA Y PROCESAMIENTO
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/process")
async def trigger_process(background_tasks: BackgroundTasks) -> Dict[str, str]:
    engine = _get_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Motor de ingesta no disponible.")

    # Evita dos ingestas en paralelo (doble clic o choque con el scheduler)
    if not _INGEST_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Ya hay una ingesta en curso.")

    def _run_with_logs():
        try:
            set_pipeline_state(active=True, started_at=time.strftime("%H:%M:%S"),
                               processed=0, total=0, current_channel=None, current_video=None)
            push_log("🚀 Ingesta masiva iniciada", "INFO")
            try:
                engine.run_global_ingestion()
                push_log("✅ Ingesta finalizada", "INFO")
            except Exception as exc:
                push_log(f"❌ Error en ingesta: {exc}", "ERROR")
            finally:
                set_pipeline_state(active=False, current_channel=None, current_video=None)
        finally:
            _INGEST_LOCK.release()

    background_tasks.add_task(_run_with_logs)
    return {"status": "started", "message": "Ingesta masiva lanzada en segundo plano."}


@app.get("/api/logs/stream")
async def api_logs_stream(request: Request):
    """Server-Sent Events: emite logs del pipeline en tiempo real."""
    async def _generator() -> AsyncGenerator[str, None]:
        # Enviar historial reciente al conectar
        with _LOG_BUS_LOCK:
            snapshot = list(_LOG_BUS)
        for entry in snapshot[-50:]:
            yield f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"

        last_len = len(snapshot)
        while True:
            if await request.is_disconnected():
                break
            with _LOG_BUS_LOCK:
                current = list(_LOG_BUS)
            if len(current) > last_len:
                for entry in current[last_len:]:
                    yield f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"
                last_len = len(current)
            # keepalive cada 15s
            yield ": keepalive\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/pipeline/status")
async def api_pipeline_status() -> Dict[str, Any]:
    """Estado en tiempo real del pipeline (canal actual, progreso)."""
    with _PIPELINE_LOCK:
        return dict(_PIPELINE_STATE)


def _sse(evento: Dict[str, Any]) -> str:
    return f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"


def _chat_sse(request: Request, pregunta: str, agente: str,
              historial: List[Dict[str, Any]], proyecto: str = "kb_chat") -> StreamingResponse:
    """Una vuelta de conversación con el Agente IA, emitida como eventos SSE:

      {"route": …}   qué agente atiende y por qué (llega antes de que el modelo conteste)
      {"token": …}   la respuesta en TEXTO NATURAL, a trozos (nunca el JSON interno del motor)
      {"done": true, "texto", "fuentes", "datos", "confianza", "con_tienda", "rapida", "segundos"}
      {"error": …}   frase que explica qué ha pasado y qué hacer

    El motor contesta de una vez (no hay streaming real del proveedor); trocear el texto evita que una
    respuesta larga aparezca de golpe."""
    async def _generator() -> AsyncGenerator[str, None]:
        if not pregunta.strip():
            yield _sse({"error": "Escribe una pregunta para empezar."})
            return
        try:
            yield _sse({"route": agent_chat.elegir_ruta(pregunta, agente, historial)})
            loop = asyncio.get_running_loop()
            r = await loop.run_in_executor(
                None, lambda: agent_chat.responder(DB_PATH, pregunta, agente, historial, proyecto=proyecto))
            for trozo in agent_chat.trocear(r["texto"]):
                if await request.is_disconnected():
                    return
                yield _sse({"token": trozo})
                await asyncio.sleep(0.008 if r["rapida"] else 0.02)
            yield _sse({"done": True, **{k: r[k] for k in (
                "texto", "ruta", "fuentes", "datos", "confianza", "con_tienda", "rapida", "segundos")}})
        except agent_chat.AgenteNoDisponible as exc:
            yield _sse({"error": str(exc)})
        except Exception as exc:
            log.exception("[KB CHAT] Error en la conversación")
            yield _sse({"error": agent_chat.explicar_error(exc)})

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/kb/chat")
async def api_kb_chat(request: Request, body: ChatIn):
    """Chat con el Agente IA: la pregunta más los turnos anteriores (el agente recuerda la conversación)."""
    if len(body.pregunta) > agent_chat.MAX_PREGUNTA:
        raise HTTPException(status_code=422, detail=f"La pregunta supera los {agent_chat.MAX_PREGUNTA} caracteres.")
    historial = [t.model_dump() for t in body.historial[-agent_chat.MAX_TURNOS:]]
    return _chat_sse(request, body.pregunta, body.agente, historial)


@app.get("/api/kb/stream")
async def api_kb_stream(request: Request, pregunta: str = Query("", max_length=2000), agente: str = "auto"):
    """Igual que /api/kb/chat pero por GET y sin memoria de conversación (compatibilidad)."""
    return _chat_sse(request, pregunta, agente, [], proyecto="kb_stream")


# ═══════════════════════════════════════════════════════════════════════════════
# API — KNOWLEDGE BASE / INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/insights")
async def api_insights(
    response: Response,
    tipo: str = Query("", pattern="^(|product_trends|conversion_formulas|operations_traffic)$"),
    buscar: str = Query("", max_length=200),
    canal: str = Query("", max_length=200),
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> List[Dict[str, Any]]:
    """Insights de la KB con filtros por tipo, texto y canal. Total en X-Total-Count."""
    res = _query_insights(tipo=tipo, buscar=buscar, canal=canal, limite=limite, offset=offset)
    response.headers["X-Total-Count"] = str(res["total"])
    return res["items"]


@app.get("/api/insights/resumen")
async def api_insights_resumen() -> Dict[str, Any]:
    """Totales por tipo y por canal de toda la KB."""
    return _insights_resumen()


# ═══════════════════════════════════════════════════════════════════════════════
# API — TRANSCRIPCIONES
# ═══════════════════════════════════════════════════════════════════════════════

class IngestarIn(BaseModel):
    """Ingesta manual: o bien `url` de YouTube, o bien `titulo` + `texto`."""
    url: str = ""
    titulo: str = ""
    canal: str = ""
    texto: str = ""
    idioma: str = "es"


def _cleaner():
    from app.services.transcript_cleaner import TranscriptCleaner
    return TranscriptCleaner()


@app.get("/api/transcripciones")
async def api_transcripciones(
    response: Response,
    limite: int = Query(50, ge=1, le=transcript_store.MAX_LIMIT),
    offset: int = Query(0, ge=0),
    buscar: str = Query("", max_length=200),
    solo_procesadas: Optional[bool] = None,
    canal: str = Query("", max_length=200),
) -> List[Dict[str, Any]]:
    """Lista transcripciones (búsqueda en título, canal, texto limpio y original).
    El total sin paginar va en la cabecera X-Total-Count."""
    try:
        res = transcript_store.list_transcripts(
            DB_PATH, buscar=buscar, solo_procesadas=solo_procesadas,
            canal=canal, limite=limite, offset=offset)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {exc}")
    response.headers["X-Total-Count"] = str(res["total"])
    return res["items"]


@app.get("/api/transcripciones/stats/resumen")
async def api_transcripciones_stats() -> Dict[str, Any]:
    """Resumen estadístico de la tabla de transcripciones."""
    try:
        return transcript_store.stats(DB_PATH)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {exc}")


@app.post("/api/transcripciones/ingestar", status_code=201)
async def api_transcripcion_ingestar(body: IngestarIn, response: Response) -> Dict[str, Any]:
    """Guarda una transcripción nueva: descargándola de una URL de YouTube o a
    partir de texto pegado."""
    loop = asyncio.get_running_loop()
    try:
        if body.url.strip():
            res = await loop.run_in_executor(
                None, lambda: transcript_store.ingest_url(
                    DB_PATH, body.url, _cleaner(), body.idioma))
        elif body.texto.strip():
            if not body.titulo.strip():
                raise ValueError("Falta el título.")
            res = await loop.run_in_executor(
                None, lambda: transcript_store.ingest_text(
                    DB_PATH, body.titulo, body.canal, body.texto, _cleaner(), body.idioma))
        else:
            raise ValueError("Indica una URL de YouTube o pega el texto con su título.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {exc}")
    if res.get("duplicado"):
        response.status_code = 200
    return res


@app.get("/api/transcripciones/{transcripcion_id}")
async def api_transcripcion_detalle(transcripcion_id: int) -> Dict[str, Any]:
    """Retorna una transcripción completa (texto limpio y original) por su ID."""
    try:
        row = transcript_store.get_transcript(DB_PATH, transcripcion_id)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {exc}")
    if row is None:
        raise HTTPException(status_code=404, detail="Transcripción no encontrada.")
    return row


@app.get("/api/transcripciones/{transcripcion_id}/exportar")
async def api_transcripcion_exportar(
    transcripcion_id: int,
    version: str = Query("limpia", pattern="^(limpia|original)$"),
) -> Response:
    """Descarga la transcripción como archivo Markdown."""
    row = transcript_store.get_transcript(DB_PATH, transcripcion_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Transcripción no encontrada.")
    nombre = transcript_store.safe_filename(row.get("titulo"))
    return Response(
        content=transcript_store.to_markdown(row, limpia=(version == "limpia")),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nombre)}"},
    )


@app.delete("/api/transcripciones/{transcripcion_id}")
async def api_transcripcion_borrar(transcripcion_id: int) -> Dict[str, Any]:
    try:
        ok = transcript_store.delete_transcript(DB_PATH, transcripcion_id)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {exc}")
    if not ok:
        raise HTTPException(status_code=404, detail="Transcripción no encontrada.")
    return {"status": "deleted", "id": transcripcion_id}


def _reservar_sync_transcripciones(origen: str) -> bool:
    """Marca la sincronización como en curso. False si ya había una (o la ingesta de la KB)."""
    with _TRANS_SYNC_LOCK:
        if _TRANS_SYNC["running"]:
            return False
        _TRANS_SYNC.update(running=True, msg="Iniciando…", result=None, error=None, origen=origen)
        return True


def _ejecutar_sync_transcripciones() -> None:
    """Una pasada de sincronización (bloqueante). Requiere _reservar_sync_transcripciones()."""
    global _trans_monitor
    try:
        from app.services.youtube_channel_monitor import YouTubeChannelMonitor
        monitor = YouTubeChannelMonitor(db_manager=DatabaseConnection(DB_PATH))
        _trans_monitor = monitor

        def _progress(msg: str) -> None:
            with _TRANS_SYNC_LOCK:
                _TRANS_SYNC["msg"] = msg
            push_log(f"📝 {msg}", "INFO")

        result = monitor.sincronizar_canales(progress=_progress)
        result.pop("detalles", None)
        with _TRANS_SYNC_LOCK:
            _TRANS_SYNC["result"] = result
            _TRANS_SYNC["terminada_a"] = time.strftime("%H:%M")
    except Exception as exc:
        log.exception("[SERVER] Error sincronizando transcripciones")
        with _TRANS_SYNC_LOCK:
            _TRANS_SYNC["error"] = str(exc)
    finally:
        _trans_monitor = None
        with _TRANS_SYNC_LOCK:
            _TRANS_SYNC["running"] = False


@app.post("/api/transcripciones/sincronizar", status_code=202)
async def api_transcripciones_sincronizar(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Descarga transcripciones nuevas de los canales configurados (en segundo plano)."""
    if not _reservar_sync_transcripciones("manual"):
        raise HTTPException(status_code=409, detail="Ya hay una sincronización en curso.")
    background_tasks.add_task(_ejecutar_sync_transcripciones)
    return {"status": "started"}


@app.get("/api/transcripciones/sincronizar/estado")
async def api_transcripciones_sync_estado() -> Dict[str, Any]:
    with _TRANS_SYNC_LOCK:
        return dict(_TRANS_SYNC)


@app.post("/api/transcripciones/sincronizar/cancelar")
async def api_transcripciones_sync_cancelar() -> Dict[str, str]:
    monitor = _trans_monitor
    if monitor is None:
        raise HTTPException(status_code=409, detail="No hay sincronización en curso.")
    monitor.cancelar_sincronizacion()
    return {"status": "cancelling"}


# ─── KB context helper ────────────────────────────────────────────────────────

def _strip_md_fences(text: str) -> str:
    """Los modelos suelen envolver el JSON en ```json ... ```; deja solo el JSON."""
    t = (text or "").strip()
    if not t.startswith("```"):
        return t
    t = t.split("\n", 1)[1] if "\n" in t else ""
    if t.rstrip().endswith("```"):
        t = t.rstrip()[:-3]
    return t.strip()


def _build_kb_context(limit: int = 30) -> str:
    """Construye un bloque de texto con los insights KB más recientes para inyectar al agente."""
    rows = _get_kb_insights_combined(limit)
    if not rows:
        return "(Base de conocimiento vacía — realiza ingesta de videos YouTube primero.)"
    lines = []
    for r in rows:
        tabla = r.get("source_table", "")
        titulo = r.get("titulo") or "(sin título)"
        video = r.get("video_title") or "(sin título)"
        canal = r.get("channel_name") or "?"
        preview = (r.get("content_preview") or "").strip()
        lines.append(f"[{tabla}] {titulo} — vídeo «{video}» | canal: {canal}\n{preview}")
    return "\n\n".join(lines)


# ─── Agente IA endpoint ───────────────────────────────────────────────────────

@app.get("/api/kb/ruta")
async def api_kb_ruta(pregunta: str = Query("", max_length=2000),
                      agente: str = "auto") -> Dict[str, Any]:
    """Qué agente atenderá la pregunta y por qué (se muestra en vivo mientras se escribe)."""
    return agent_chat.elegir_ruta(pregunta, agente)


@app.get("/api/kb/agentes")
async def api_kb_agentes() -> List[Dict[str, Any]]:
    """Agentes disponibles con el modelo REAL que usa el motor (no etiquetas a mano)."""
    from app.agents_engine.executor import AGENT_MODEL_MAP, AGENT_TEMP_MAP
    return [
        {"nombre": nombre, "rol": info["rol"], "descripcion": info["descripcion"],
         "modelo": AGENT_MODEL_MAP.get(nombre, "desconocido"),
         "temperatura": AGENT_TEMP_MAP.get(nombre)}
        for nombre, info in agent_router.AGENTES.items()
    ]


@app.post("/api/kb/sync")
async def api_kb_sync(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Regenera kb_index.json y los archivos kb_*.md desde SQLite."""
    def _do_sync():
        from app.services.kb_index_sync import KBIndexSync
        syncer = KBIndexSync(db_path=DB_PATH)
        index = syncer.sync()
        # Exportar .md por cada video_id único en la KB
        video_ids = {e["video_id"] for e in index.get("entradas", []) if e.get("video_id")}
        for vid in video_ids:
            syncer.export_md_for_video(vid)
        log.info(f"[KB SYNC] {index['total_entradas']} entradas · {len(video_ids)} archivos .md")

    background_tasks.add_task(_do_sync)
    return {"status": "started", "message": "Sincronización KB lanzada en segundo plano."}


@app.post("/api/kb/query")
async def api_kb_query(data: KBQueryIn) -> Dict[str, Any]:
    """Una pregunta suelta al agente (sin streaming ni memoria). `texto` es la respuesta en lenguaje
    natural y `datos` sus datos de apoyo ya legibles; `resultado` conserva el JSON del motor."""
    try:
        loop = asyncio.get_running_loop()
        r = await loop.run_in_executor(
            None, lambda: agent_chat.responder(DB_PATH, data.pregunta, data.agente, proyecto=data.proyecto))
        try:
            parsed = json.loads(agent_chat.sin_fences(r["bruto"]))
        except (json.JSONDecodeError, TypeError):
            parsed = {"respuesta": r["texto"]}
        return {"status": "ok", "agente": r["ruta"]["agente"], "ruta": r["ruta"], "resultado": parsed,
                "texto": r["texto"], "datos": r["datos"], "confianza": r["confianza"],
                "con_tienda": r["con_tienda"], "fuentes": r["fuentes"]}
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        log.error(f"[KB QUERY] Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# API — CATÁLOGO DE PRODUCTOS
# ═══════════════════════════════════════════════════════════════════════════════

class ProductoIn(BaseModel):
    nombre: str = ""
    categoria: Optional[str] = None
    url_proveedor: Optional[str] = None
    origen_video_id: Optional[str] = None
    costo_origen: Optional[float] = None
    costo_envio: Optional[float] = None
    pvp: Optional[float] = None
    notas: Optional[str] = None


class ProductoMoverIn(BaseModel):
    estado: str
    nota: str = ""


class RefutacionesIn(BaseModel):
    respuestas: Dict[str, Any]


class DemandaIn(BaseModel):
    demanda: Dict[str, Any] = {}
    creativo_ok: Optional[bool] = None


def _producto_o_error(fn):
    """Traduce los errores del catálogo a respuestas HTTP claras."""
    try:
        return fn()
    except KeyError:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {exc}")


@app.get("/api/productos")
async def api_productos(estado: str = Query("", max_length=20), buscar: str = Query("", max_length=100)) -> Dict[str, Any]:
    return {"items": product_catalog.listar(DB_PATH, estado, buscar),
            "estados": product_catalog.TODOS_LOS_ESTADOS,
            "pasos": product_catalog.ESTADOS,
            "resumen": product_catalog.resumen_estados(DB_PATH),
            "refutaciones": {str(k): v for k, v in product_catalog.REFUTACIONES.items()}}


@app.post("/api/productos", status_code=201)
async def api_producto_crear(body: ProductoIn) -> Dict[str, Any]:
    return _producto_o_error(lambda: product_catalog.crear(DB_PATH, body.model_dump(exclude_none=True)))


@app.get("/api/productos/{producto_id}")
async def api_producto_detalle(producto_id: int) -> Dict[str, Any]:
    p = product_catalog.obtener(DB_PATH, producto_id)
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    p["escalado"] = business_metrics.evaluar_escalado(DB_PATH, p) if p["estado"] in ("tienda", "escalado") else None
    p["insights"] = _query_insights(buscar=p["nombre"], limite=5)["items"] if p["nombre"] else []
    return p


@app.patch("/api/productos/{producto_id}")
async def api_producto_editar(producto_id: int, body: ProductoIn) -> Dict[str, Any]:
    return _producto_o_error(lambda: product_catalog.actualizar(DB_PATH, producto_id, body.model_dump(exclude_none=True)))


@app.post("/api/productos/{producto_id}/mover")
async def api_producto_mover(producto_id: int, body: ProductoMoverIn) -> Dict[str, Any]:
    return _producto_o_error(lambda: product_catalog.mover(DB_PATH, producto_id, body.estado, body.nota))


@app.put("/api/productos/{producto_id}/refutaciones")
async def api_producto_refutaciones(producto_id: int, body: RefutacionesIn) -> Dict[str, Any]:
    return _producto_o_error(lambda: product_catalog.guardar_refutaciones(DB_PATH, producto_id, body.respuestas))


@app.put("/api/productos/{producto_id}/demanda")
async def api_producto_demanda(producto_id: int, body: DemandaIn) -> Dict[str, Any]:
    return _producto_o_error(lambda: product_catalog.guardar_demanda(DB_PATH, producto_id, body.demanda, body.creativo_ok))


@app.delete("/api/productos/{producto_id}")
async def api_producto_borrar(producto_id: int) -> Dict[str, Any]:
    if not product_catalog.borrar(DB_PATH, producto_id):
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    return {"status": "deleted", "id": producto_id}


# ═══════════════════════════════════════════════════════════════════════════════
# API — NEGOCIO: ROAS, CAJA, CPA, ESCALADO E INTEGRACIONES
# ═══════════════════════════════════════════════════════════════════════════════

class MetricaIn(BaseModel):
    fecha: Optional[str] = None
    producto_id: Optional[int] = None
    plataforma: str = "meta"
    gasto_ads: float = 0
    ingresos: float = 0
    pedidos: int = 0
    cogs_pagado: float = 0
    devoluciones: Optional[float] = None
    visitantes: Optional[int] = None
    presupuesto_diario: Optional[float] = None
    notas: str = ""


class CajaIn(BaseModel):
    fecha: Optional[str] = None
    saldo_cuenta: float
    liberaciones_pasarela: float = 0
    pagos_proveedor_pendientes: float = 0
    notas: str = ""


@app.get("/api/negocio/resumen")
async def api_negocio_resumen(dias: int = Query(7, ge=1, le=365),
                              producto_id: Optional[int] = None) -> Dict[str, Any]:
    return {"resumen": business_metrics.resumen(DB_PATH, dias, producto_id),
            "serie": business_metrics.serie_diaria(DB_PATH, max(dias, 14), producto_id),
            "metricas": business_metrics.listar_metricas(DB_PATH, dias, producto_id)}


@app.post("/api/negocio/metricas", status_code=201)
async def api_negocio_metrica(body: MetricaIn) -> Dict[str, Any]:
    try:
        return business_metrics.registrar_dia(DB_PATH, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.delete("/api/negocio/metricas/{metrica_id}")
async def api_negocio_metrica_borrar(metrica_id: int) -> Dict[str, Any]:
    if not business_metrics.borrar_dia(DB_PATH, metrica_id):
        raise HTTPException(status_code=404, detail="Registro no encontrado.")
    return {"status": "deleted", "id": metrica_id}


@app.post("/api/negocio/caja", status_code=201)
async def api_negocio_caja(body: CajaIn) -> Dict[str, Any]:
    try:
        return business_metrics.registrar_caja(DB_PATH, body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/negocio/importar")
async def api_negocio_importar(
    file: UploadFile = File(...),
    confirmar: bool = Form(False),
    plataforma: str = Form("auto"),
    producto_id: str = Form(""),
    usar_ingresos_meta: bool = Form(False),
    estimar_cogs: bool = Form(False),
    campanas: str = Form(""),
) -> Dict[str, Any]:
    """Importa el CSV de Meta Ads Manager o de Shopify a métricas diarias.
    Sin `confirmar` solo previsualiza (no escribe nada); con `confirmar` guarda en una transacción."""
    datos = await file.read(metrics_import.MAX_BYTES + 1)
    if len(datos) > metrics_import.MAX_BYTES:
        raise HTTPException(status_code=413, detail="El archivo pasa de 5 MB: exporta un periodo más corto.")
    try:
        pid = int(producto_id) if producto_id.strip() else None
        filtro = json.loads(campanas) if campanas.strip() else None
        if filtro is not None and not (isinstance(filtro, list) and all(isinstance(c, str) for c in filtro)):
            raise ValueError("La lista de campañas no es válida.")
        if plataforma not in ("auto", "meta", "shopify"):
            raise ValueError("Plataforma no válida.")
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc) or "Parámetros no válidos.")

    def _trabajo() -> Dict[str, Any]:
        parsed = metrics_import.parsear(datos, plataforma, filtro)
        if confirmar:
            return metrics_import.aplicar(DB_PATH, parsed, pid, usar_ingresos_meta, estimar_cogs)
        return metrics_import.previsualizar(DB_PATH, parsed, pid, usar_ingresos_meta, estimar_cogs)

    try:
        res = await asyncio.get_event_loop().run_in_executor(None, _trabajo)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if confirmar:
        _ALERTAS_EVAL["ts"] = 0.0       # los números nuevos pueden crear o resolver alertas
        log.info(f"[SERVER] Importación CSV {res['plataforma']}: {res['nuevos']} nuevos, "
                 f"{res['actualizados']} actualizados (correlation_id={res['correlation_id']}).")
    return res


@app.get("/api/negocio/escalado/{producto_id}")
async def api_negocio_escalado(producto_id: int) -> Dict[str, Any]:
    p = product_catalog.obtener(DB_PATH, producto_id)
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")
    return business_metrics.evaluar_escalado(DB_PATH, p)


@app.get("/api/integraciones")
async def api_integraciones() -> List[Dict[str, Any]]:
    """Qué integraciones están configuradas (sí/no; nunca se devuelven los valores)."""
    return business_metrics.estado_integraciones()


# ═══════════════════════════════════════════════════════════════════════════════
# GOBERNANZA — cumplimiento de reglas, memoria de agentes (equivalente web del
# panel de escritorio GovernancePanel)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/gobernanza")
async def api_gobernanza() -> Dict[str, Any]:
    try:
        from app.services.validator_rules import RulesValidator
        from app.services.memory_logger import MemoryLogger

        validator = RulesValidator(db_manager=DatabaseConnection())
        pre = validator.pre_execution_check()
        memoria = MemoryLogger(db_manager=DatabaseConnection())
        return {
            "pre_execution": pre,
            "compliance": validator.compliance_score(),
            "memoria": memoria.get_all_memory(limit=100),
            "memoria_stats": memoria.memory_stats(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# ENRUTADOR LLM — estado del pool híbrido (equivalente web de OllamaPanel)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/enrutador")
async def api_enrutador() -> Dict[str, Any]:
    try:
        from app.core.ollama_pool import HybridInferencePool
        pool = HybridInferencePool()
        return {
            "activa": pool.get_active_layer(),
            "disponibles": pool.get_available_layers(),
            "stats": pool.get_hybrid_stats(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/enrutador/health-check")
async def api_enrutador_health_check() -> Dict[str, Any]:
    try:
        from app.core.ollama_pool import HybridInferencePool
        pool = HybridInferencePool()
        disponible = pool.is_ollama_available(force_check=True)
        return {"ollama_disponible": disponible, "timestamp": datetime.now().isoformat()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN (solo lectura) — estado de claves, nunca el valor completo.
# La edición real de claves se queda solo en la app de escritorio (settings_panel.py):
# web_auth.py no tiene protección CSRF ni reautenticación para escrituras sensibles.
# ═══════════════════════════════════════════════════════════════════════════════

_CONFIG_EXTRA = [
    ("GEM_OS_PASSWORD", "Contraseña de la web (opcional)"),
    ("FREELLM_API_KEY", "FreeLLMAPI (opcional)"),
    ("ANTHROPIC_API_KEY", "Anthropic directa (opcional)"),
]


@app.get("/api/config/estado")
async def api_config_estado() -> List[Dict[str, Any]]:
    try:
        from app.config import secrets_store
        out = []
        for item in business_metrics.estado_integraciones():
            out.append({
                "id": item["id"], "nombre": item["nombre"], "para": item["para"],
                "configurada": item["configurada"], "nota": item.get("nota", ""),
            })
        for nombre_var, etiqueta in _CONFIG_EXTRA:
            valor = os.getenv(nombre_var, "")
            out.append({
                "id": nombre_var.lower(), "nombre": etiqueta, "para": "",
                "configurada": bool(valor.strip()),
                "ultimos4": secrets_store.enmascarar(valor) if valor.strip() else None,
            })
        return out
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ═══════════════════════════════════════════════════════════════════════════════
# CENTRO DE ALERTAS Y RESUMEN DIARIO (automáticos, sin IA)
# ═══════════════════════════════════════════════════════════════════════════════

_ALERTAS_EVAL = {"ts": 0.0}


@app.get("/api/alertas")
async def api_alertas(todas: bool = False, refrescar: bool = False) -> Dict[str, Any]:
    """Alertas activas. Se recalculan si la última revisión tiene más de 2 minutos
    (para que registrar la caja o un canal las actualice al momento)."""
    if refrescar or time.time() - _ALERTAS_EVAL["ts"] > 120:
        _ALERTAS_EVAL["ts"] = time.time()
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: alerts.evaluar(DB_PATH, CHANNELS_JSON_PATH))
        except Exception as exc:
            log.warning(f"[SERVER] No se pudieron recalcular las alertas: {exc}")
    return alerts.listar(DB_PATH, incluir_resueltas=todas)


@app.post("/api/alertas/vistas")
async def api_alertas_vistas(alerta_id: Optional[int] = None) -> Dict[str, Any]:
    """Marca como vista una alerta (o todas). Sigue activa mientras el problema exista."""
    return {"marcadas": alerts.marcar_vista(DB_PATH, alerta_id)}


@app.get("/api/avisos")
async def api_avisos() -> Dict[str, Any]:
    """Estado de los canales de aviso fuera de la app (nunca devuelve la URL del webhook)."""
    return notifier.configuracion()


@app.post("/api/avisos/prueba")
async def api_avisos_prueba() -> Dict[str, Any]:
    """Envía un aviso de prueba por los canales activos."""
    return await asyncio.get_event_loop().run_in_executor(None, notifier.enviar_prueba)


@app.get("/api/mantenimiento")
async def api_mantenimiento() -> Dict[str, Any]:
    """Resultado de la última pasada de mantenimiento y si hay una en curso."""
    return {"ultimo": mantenimiento.ultimo(CHANNELS_JSON_PATH), "en_curso": mantenimiento._LOCK.locked()}


@app.post("/api/mantenimiento/ejecutar")
async def api_mantenimiento_ejecutar() -> Dict[str, Any]:
    """Lanza el mantenimiento en segundo plano (verificar los canales tarda ~1 min)."""
    if mantenimiento._LOCK.locked():
        raise HTTPException(status_code=409, detail="Ya hay un mantenimiento en curso.")

    def _tarea() -> None:
        try:
            mantenimiento.ejecutar(DB_PATH, CHANNELS_JSON_PATH)
            alerts.evaluar(DB_PATH, CHANNELS_JSON_PATH)
        except Exception as exc:
            log.warning(f"[SERVER] Mantenimiento manual falló: {exc}")

    asyncio.get_event_loop().run_in_executor(None, _tarea)
    return {"iniciado": True}


@app.get("/api/resumen-diario")
async def api_resumen_diario() -> Dict[str, Any]:
    """Resumen de hoy (lo genera si todavía no existe) y el historial de los guardados."""
    loop = asyncio.get_event_loop()
    r = await loop.run_in_executor(
        None, lambda: daily_brief.ultimo(DB_PATH, regenerar_si_falta=True, config_path=CHANNELS_JSON_PATH))
    return {"resumen": r, "historial": daily_brief.historial(DB_PATH)}


@app.post("/api/resumen-diario/generar")
async def api_resumen_diario_generar() -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    r = await loop.run_in_executor(None, lambda: daily_brief.generar(DB_PATH, CHANNELS_JSON_PATH))
    return {"resumen": r, "historial": daily_brief.historial(DB_PATH)}


# ═══════════════════════════════════════════════════════════════════════════════
# ACCESO CON CONTRASEÑA (opcional: GEM_OS_PASSWORD) Y REGISTROS
# ═══════════════════════════════════════════════════════════════════════════════

class LoginIn(BaseModel):
    password: str = ""


@app.middleware("http")
async def _exigir_sesion(request: Request, call_next):
    """Con GEM_OS_PASSWORD definida, todo requiere sesión salvo login, estáticos y webhooks."""
    if not web_auth.activa() or web_auth.es_libre(request.url.path):
        return await call_next(request)
    if web_auth.token_valido(request.cookies.get(web_auth.COOKIE)):
        return await call_next(request)
    if request.method == "GET" and "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url="/login?next=" + quote(request.url.path), status_code=303)
    return JSONResponse(status_code=401, content={"detail": "Sesión requerida."})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return _render(request, "login.html")


@app.post("/api/login")
async def api_login(body: LoginIn, request: Request, response: Response) -> Dict[str, Any]:
    if not web_auth.activa():
        return {"status": "sin_contrasena"}
    ip = request.client.host if request.client else "?"
    espera = web_auth.bloqueado(ip)
    if espera:
        raise HTTPException(status_code=429, detail=f"Demasiados intentos. Espera {espera} s.")
    if not web_auth.password_correcta(body.password):
        web_auth.registrar_fallo(ip)
        raise HTTPException(status_code=401, detail="Contraseña incorrecta.")
    web_auth.limpiar_fallos(ip)
    seguro = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    response.set_cookie(web_auth.COOKIE, web_auth.crear_token(), max_age=web_auth.DIAS_SESION * 86400,
                        httponly=True, samesite="lax", secure=seguro, path="/")
    return {"status": "ok"}


@app.get("/logout")
async def logout() -> RedirectResponse:
    r = RedirectResponse(url="/login", status_code=303)
    r.delete_cookie(web_auth.COOKIE, path="/")
    return r


@app.get("/registros", response_class=HTMLResponse)
async def registros_page(request: Request):
    return _render(request, "registros.html")


@app.get("/api/registros")
async def api_registros(fuente: str = Query("servidor", pattern="^(servidor|elite|pipeline)$"),
                        nivel: str = Query("", pattern="^(|DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
                        q: str = Query("", max_length=100),
                        limite: int = Query(200, ge=1, le=1000)) -> Dict[str, Any]:
    """Registros recientes (más nuevos primero). 'pipeline' = mensajes en vivo de la ingesta."""
    if fuente == "pipeline":
        with _LOG_BUS_LOCK:
            bus = list(_LOG_BUS)
        items = [{"ts": e["ts"], "nivel": e["level"], "origen": "pipeline", "msg": e["msg"]} for e in reversed(bus)]
        if q.strip():
            items = [e for e in items if q.strip().lower() in e["msg"].lower()]
        minimo = log_viewer.NIVELES.get(nivel, 0)
        items = [e for e in items if log_viewer.NIVELES.get(e["nivel"], 20) >= minimo][:limite]
    else:
        ruta = _GEM_PATHS["logs"] / ("servidor.log" if fuente == "servidor" else "elite_suite.jsonl")
        items = log_viewer.consultar(fuente, ruta, nivel, q, limite)
    return {"fuente": fuente, "items": items}


# ═══════════════════════════════════════════════════════════════════════════════
# API — HISTORIAL Y EXPORTACIÓN CSV
# ═══════════════════════════════════════════════════════════════════════════════

def _dataset(tipo: str, buscar: str, limite: int, offset: int) -> Dict[str, Any]:
    """Filas en el formato común {columnas, filas, total} para cualquier tipo de historial."""
    try:
        return exports.dataset(DB_PATH, CHANNELS_JSON_PATH, tipo, buscar, limite, offset)
    except KeyError:
        raise HTTPException(status_code=404, detail="Tipo de historial desconocido.")


@app.get("/api/historial/{tipo}")
async def api_historial(tipo: str, buscar: str = Query("", max_length=100),
                        limite: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)) -> Dict[str, Any]:
    return _dataset(tipo, buscar, limite, offset)


@app.get("/api/exportar/{tipo}.csv")
async def api_exportar_csv(tipo: str, buscar: str = Query("", max_length=100)) -> Response:
    """Descarga el historial como CSV (UTF-8 con BOM, listo para Excel)."""
    try:
        datos = exports.todas_las_filas(DB_PATH, CHANNELS_JSON_PATH, tipo, buscar)
    except KeyError:
        raise HTTPException(status_code=404, detail="Tipo de historial desconocido.")
    nombre = f"gemos_{tipo}_{time.strftime('%Y%m%d')}.csv"
    return Response(content=exports.a_csv(datos["columnas"], datos["filas"]),
                    media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename={nombre}"})


# ═══════════════════════════════════════════════════════════════════════════════
# API — ACCIONES DE NEGOCIO (Fase 3)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/validar")
async def api_validar(data: ValidarIn) -> Dict[str, Any]:
    try:
        from app.services.financial_validator import FinancialValidator
        validator = FinancialValidator()
        return validator.validar_producto(
            sku=data.sku,
            costo_origen=data.costo_origen,
            costo_envio=data.costo_envio,
            peso_kg=data.peso_kg,
            pvp_sugerido=data.pvp_sugerido,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/copy")
async def api_copy(data: CopyIn) -> Dict[str, Any]:
    try:
        from app.services.copywriting_engine import CopywrightingEngine
        engine = CopywrightingEngine()
        result = engine.generar_con_openrouter(
            nombre_producto=data.nombre_producto,
            categoria=data.categoria,
            costo_origen=data.costo_origen,
            pvp=data.pvp,
            peso_kg=data.peso_kg,
        )
        return result if isinstance(result, dict) else {"copy": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/tiktok")
async def api_tiktok(data: TikTokIn) -> Dict[str, Any]:
    try:
        from app.services.tiktok_script_generator import TikTokScriptGenerator
        gen = TikTokScriptGenerator()
        result = gen.generar_con_openrouter(
            nombre_producto=data.nombre_producto,
            categoria=data.categoria,
            patron_hook=data.patron_hook,
            duracion_segundos=data.duracion_segundos,
        )
        return result if isinstance(result, dict) else {"script": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/tiktok/publicar")
async def api_tiktok_publicar(data: PublicarTikTokIn) -> Dict[str, Any]:
    """Envía el guión a Make.com (webhook) para registro y aviso automático."""
    from app.services.tiktok_publisher import TikTokPublisher

    publisher = TikTokPublisher()
    if not publisher.esta_configurado():
        raise HTTPException(
            status_code=400,
            detail="MAKE_WEBHOOK_TIKTOK no está configurado en .env",
        )

    resultado = publisher.publicar(
        guion={
            "patron_hook": data.patron_hook,
            "hook": data.hook,
            "cuerpo": data.cuerpo,
            "cta": data.cta,
            "duracion_segundos": data.duracion_segundos,
        },
        producto=data.producto,
        categoria=data.categoria,
    )

    if not resultado.get("ok"):
        raise HTTPException(status_code=502, detail=resultado.get("error", "Error desconocido"))

    push_log(f"Guión TikTok enviado a Make.com: {data.producto}", "INFO")
    return resultado


@app.get("/api/imagenes/estado")
async def api_imagenes_estado() -> Dict[str, Any]:
    """Informa qué método de remoción de fondo está disponible."""
    from app.services.image_remover import ImageRemover

    remover = ImageRemover()
    try:
        import rembg  # noqa: F401
        local_ok = True
    except ImportError:
        local_ok = False

    return {
        "removebg": bool(remover.removebg_key),
        "rembg_local": local_ok,
        "metodo_activo": "remove.bg" if remover.removebg_key else ("rembg-local" if local_ok else None),
    }


@app.post("/api/imagenes/remover-fondo")
async def api_remover_fondo(imagen: UploadFile = File(...)) -> Dict[str, Any]:
    """Sube una imagen, remueve el fondo y devuelve PNG + WebP listos para Shopify."""
    from app.services.image_remover import ImageRemover

    sufijo = Path(imagen.filename or "producto.png").suffix.lower()
    if sufijo not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=400, detail="Formato no soportado: usa PNG, JPG o WebP")

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    origen = IMG_DIR / f"{uuid.uuid4().hex}{sufijo}"
    origen.write_bytes(await imagen.read())

    resultado = ImageRemover().procesar_completo(str(origen), str(IMG_DIR))
    origen.unlink(missing_ok=True)

    if not resultado.get("ok"):
        raise HTTPException(status_code=502, detail=resultado.get("error", "Error desconocido"))

    push_log(f"Imagen procesada ({resultado['metodo']}): {resultado['size_kb']} KB", "INFO")
    return {
        **resultado,
        "png_url": f"/api/imagenes/archivo/{Path(resultado['png']).name}",
        "webp_url": f"/api/imagenes/archivo/{Path(resultado['webp']).name}",
    }


@app.get("/api/imagenes/archivo/{nombre}")
async def api_imagen_archivo(nombre: str) -> FileResponse:
    """Sirve una imagen ya procesada."""
    destino = (IMG_DIR / nombre).resolve()
    if destino.parent != IMG_DIR.resolve() or not destino.is_file():
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return FileResponse(destino)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPATIBILIDAD CON TKINTER (app/main.py en modo dev)
# ═══════════════════════════════════════════════════════════════════════════════

_server_instance = None


def start_dashboard(port: int = DASHBOARD_PORT, host: str = "127.0.0.1", daemon: bool = True):
    """Lanza el servidor en un hilo para modo desarrollo Tkinter (dev only)."""
    global _server_instance

    def _run():
        global _server_instance
        config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        server = uvicorn.Server(config)
        _server_instance = server
        server.run()

    thread = threading.Thread(target=_run, daemon=daemon)
    thread.start()
    print(f"🌐 GEM OS Web corriendo en http://{host}:{port}")
    return thread


def stop_dashboard():
    """Detiene el servidor de forma controlada."""
    global _server_instance
    if _server_instance:
        _server_instance.should_exit = True


# ── Fallback HTML (sin templates) ────────────────────────────────────────────
_FALLBACK_HTML = """<!DOCTYPE html>
<html lang="es" class="dark">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEM OS</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-gray-900 text-gray-100 min-h-screen flex items-center justify-center">
<div class="text-center p-8">
  <h1 class="text-3xl font-bold mb-4 text-cyan-400">GEM OS Dashboard</h1>
  <p class="text-gray-400 mb-6">Templates Jinja2 no encontrados.<br>
  Crea el directorio <code class="text-cyan-300">app/templates/</code> con los archivos HTML.</p>
  <div class="flex gap-4 justify-center flex-wrap">
    <a href="/api/metrics" class="text-cyan-400 hover:underline">/api/metrics</a>
    <a href="/api/channels" class="text-cyan-400 hover:underline">/api/channels</a>
    <a href="/api/insights" class="text-cyan-400 hover:underline">/api/insights</a>
    <a href="/api/status" class="text-cyan-400 hover:underline">/api/status</a>
  </div>
</div></body></html>"""


# ── Ejecución directa ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Solo local por defecto: el servidor no tiene login y expone acciones de
    # borrado/ingesta. Para publicarlo (VPS) hay que pedirlo: GEM_OS_HOST=0.0.0.0
    uvicorn.run(app, host=os.getenv("GEM_OS_HOST", "127.0.0.1"),
                port=DASHBOARD_PORT, log_level="info")
