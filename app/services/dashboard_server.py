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
import json
import logging
import os
import re
import sqlite3
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
import jinja2
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config.path_manager import PathManager
from app.database.connection import DatabaseConnection

log = logging.getLogger(__name__)

# ── Constantes ───────────────────────────────────────────────────────────────
_GEM_PATHS = PathManager.get_paths()
DB_PATH = str(_GEM_PATHS["db"])
QUEUE_STATE_PATH = str(_GEM_PATHS["queue"])
CHANNELS_JSON_PATH = str(_GEM_PATHS["config"])
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "47821"))
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Regex de validación de URLs de canal YouTube (misma fuente de verdad que el engine)
_YOUTUBE_CHANNEL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/"
    r"(?:@[A-Za-z0-9._-]+|channel/UC[A-Za-z0-9_-]+|c/[A-Za-z0-9_.-]+|user/[A-Za-z0-9_.-]+)"
    r"/?$"
)

# ── Lazy engine singleton ────────────────────────────────────────────────────
_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                try:
                    from app.services.provider_monitor_engine import ProviderMonitorEngine
                    _engine = ProviderMonitorEngine()
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

    if _scheduler_available and _scheduler is not None and engine is not None:
        _scheduler.add_job(
            engine.run_global_ingestion,
            "interval",
            hours=1,
            id="auto_ingest",
            max_instances=1,
            misfire_grace_time=300,
            replace_existing=True,
        )
        _scheduler.start()
        log.info("[SERVER] APScheduler iniciado — ingesta autónoma cada 1h.")

    yield

    if _scheduler_available and _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("[SERVER] Scheduler detenido.")


# ── App FastAPI ───────────────────────────────────────────────────────────────
app = FastAPI(title="GEM OS Dashboard", version="3.7.2", lifespan=lifespan)

# Webhooks Shopify
try:
    from app.routes.webhooks import webhooks_router
    app.include_router(webhooks_router)
    log.info("[SERVER] Webhooks Shopify montados en /webhooks")
except Exception as _wh_err:
    log.warning(f"[SERVER] Webhooks no disponibles: {_wh_err}")

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
        content = tmpl.render(request=request, **(ctx or {}))
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
    agente: str = "gem-orchestrator-core"
    proyecto: str = "kb_consulta"


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
    Path(CHANNELS_JSON_PATH).write_text(
        json.dumps(channels, ensure_ascii=False, indent=2), encoding="utf-8"
    )


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
            cur.execute("SELECT COUNT(*) FROM video_sources")
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


def _get_kb_insights_combined(limit: int = 50) -> List[Dict[str, Any]]:
    """Combina las 3 tablas KB con metadatos del video para GET /api/insights."""
    rows: List[Dict[str, Any]] = []
    query_map = [
        ("product_trends", "wow_factor"),
        ("conversion_formulas", "raw_structure"),
        ("operations_traffic", "scaling_strategy"),
    ]
    try:
        db = _get_db()
        with db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            for table, content_col in query_map:
                try:
                    cur.execute(f"""
                        SELECT t.id, '{table}' AS source_table,
                               v.title AS video_title, v.channel_name,
                               t.{content_col} AS content_preview,
                               t.validated_at AS created_at
                        FROM {table} t
                        LEFT JOIN video_sources v ON t.video_id = v.video_id
                        ORDER BY t.id DESC LIMIT ?
                    """, (limit,))
                    for row in cur.fetchall():
                        r = dict(row)
                        if r.get("content_preview"):
                            r["content_preview"] = str(r["content_preview"])[:200]
                        rows.append(r)
                except sqlite3.OperationalError:
                    continue
    except sqlite3.Error:
        pass
    rows.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return rows[:limit]


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


@app.get("/insights", response_class=HTMLResponse)
async def insights_page(request: Request):
    return _render(request, "insights.html")


@app.get("/agente", response_class=HTMLResponse)
async def agente_page(request: Request):
    return _render(request, "agente.html")


@app.get("/transcripciones", response_class=HTMLResponse)
async def transcripciones_page(request: Request):
    return _render(request, "transcripciones.html")


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

@app.get("/api/channels")
async def get_channels() -> List[Dict[str, Any]]:
    return _load_channels_json()


@app.post("/api/channels", status_code=201)
async def add_channel(channel: ChannelIn) -> Dict[str, Any]:
    url = channel.url.strip()
    if not _YOUTUBE_CHANNEL_RE.match(url):
        raise HTTPException(status_code=422, detail="URL de canal YouTube inválida.")
    channels = _load_channels_json()
    if any(ch.get("url") == url for ch in channels):
        raise HTTPException(status_code=409, detail="Canal ya registrado.")
    new_entry = {
        "url": url, "nombre": channel.nombre.strip(), "activo": True,
        "tags": [t.strip() for t in channel.tags.split(",") if t.strip()],
        "idioma": channel.idioma, "prioridad": channel.prioridad,
        "max_videos_scan": channel.max_videos_scan,
    }
    channels.append(new_entry)
    _save_channels_json(channels)
    # Sincronizar en canales_favoritos
    try:
        handle = url.rstrip("/").split("/")[-1].lower()
        import sqlite3 as _sq
        with _sq.connect(DB_PATH) as _conn:
            _conn.execute(
                """INSERT OR IGNORE INTO canales_favoritos
                   (handle, nombre, url, idioma, especialidad, tags, prioridad)
                   VALUES (?,?,?,?,?,?,?)""",
                (handle, channel.nombre.strip(), url, channel.idioma,
                 "general", channel.tags, channel.prioridad)
            )
    except Exception:
        pass
    return new_entry


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
    background_tasks.add_task(engine.run_global_ingestion)
    return {"status": "started", "message": "Ingesta masiva lanzada en segundo plano."}


# ═══════════════════════════════════════════════════════════════════════════════
# API — KNOWLEDGE BASE / INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/insights")
async def api_insights() -> List[Dict[str, Any]]:
    return _get_kb_insights_combined(50)


# ═══════════════════════════════════════════════════════════════════════════════
# API — TRANSCRIPCIONES
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/transcripciones")
async def api_transcripciones(
    limite: int = 50,
    buscar: str = "",
    solo_procesadas: Optional[bool] = None,
    canal: str = "",
) -> List[Dict[str, Any]]:
    """Lista transcripciones con filtros opcionales de búsqueda, canal y estado."""
    try:
        import sqlite3 as _sq
        with _sq.connect(DB_PATH) as conn:
            conn.row_factory = _sq.Row
            conditions = []
            params: list = []
            if buscar:
                conditions.append(
                    "(t.titulo LIKE ? OR t.canal LIKE ? OR t.transcripcion_limpia LIKE ?)"
                )
                like = f"%{buscar}%"
                params += [like, like, like]
            if solo_procesadas is not None:
                conditions.append("t.procesada = ?")
                params.append(1 if solo_procesadas else 0)
            if canal:
                conditions.append("t.canal LIKE ?")
                params.append(f"%{canal}%")
            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            params.append(limite)
            rows = conn.execute(f"""
                SELECT t.id, t.video_id, t.titulo, t.canal, t.fecha,
                       t.tokens_original, t.tokens_limpios, t.procesada,
                       t.creada_at,
                       CASE WHEN t.transcripcion_limpia IS NOT NULL
                            THEN substr(t.transcripcion_limpia, 1, 300)
                            ELSE substr(t.transcripcion_texto, 1, 300)
                       END AS preview
                FROM transcripciones_youtube t
                {where}
                ORDER BY t.id DESC LIMIT ?
            """, params).fetchall()
            return [dict(r) for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/transcripciones/{transcripcion_id}")
async def api_transcripcion_detalle(transcripcion_id: int) -> Dict[str, Any]:
    """Retorna una transcripción completa (texto limpio o crudo) por su ID."""
    try:
        import sqlite3 as _sq
        with _sq.connect(DB_PATH) as conn:
            conn.row_factory = _sq.Row
            row = conn.execute(
                """SELECT t.id, t.video_id, t.titulo, t.canal, t.fecha,
                          t.transcripcion_texto, t.transcripcion_limpia,
                          t.hash_md5, t.tokens_original, t.tokens_limpios,
                          t.procesada, t.creada_at, t.actualizada_at,
                          v.platform, v.processed_at
                   FROM transcripciones_youtube t
                   LEFT JOIN video_sources v ON t.video_id = v.video_id
                   WHERE t.id = ?""",
                (transcripcion_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Transcripción no encontrada.")
        return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/transcripciones/stats/resumen")
async def api_transcripciones_stats() -> Dict[str, Any]:
    """Resumen estadístico de la tabla de transcripciones."""
    try:
        import sqlite3 as _sq
        with _sq.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM transcripciones_youtube")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM transcripciones_youtube WHERE procesada = 1")
            procesadas = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT canal) FROM transcripciones_youtube")
            canales = cur.fetchone()[0]
            cur.execute("SELECT SUM(tokens_limpios) FROM transcripciones_youtube")
            tokens = cur.fetchone()[0] or 0
        return {
            "total": total,
            "procesadas": procesadas,
            "pendientes": total - procesadas,
            "canales_unicos": canales,
            "tokens_totales": tokens,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ─── KB context helper ────────────────────────────────────────────────────────

def _build_kb_context(limit: int = 30) -> str:
    """Construye un bloque de texto con los insights KB más recientes para inyectar al agente."""
    rows = _get_kb_insights_combined(limit)
    if not rows:
        return "(Base de conocimiento vacía — realiza ingesta de videos YouTube primero.)"
    lines = []
    for r in rows:
        tabla = r.get("source_table", "")
        titulo = r.get("video_title") or "(sin título)"
        canal = r.get("channel_name") or "?"
        preview = (r.get("content_preview") or "").strip()
        lines.append(f"[{tabla}] {titulo} | {canal}\n{preview}")
    return "\n\n".join(lines)


# ─── Agente IA endpoint ───────────────────────────────────────────────────────

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
    """Envía una pregunta al AgentExecutor con contexto KB inyectado desde SQLite."""
    try:
        from app.agents_engine.executor import AgentExecutor
        executor = AgentExecutor()
        kb_context = _build_kb_context(30)
        pregunta_enriquecida = (
            f"CONTEXTO KB (últimos insights del sistema):\n"
            f"---\n{kb_context}\n---\n\n"
            f"PREGUNTA DEL OPERADOR:\n{data.pregunta}"
        )
        resultado = executor.execute_agent_task(
            agent_name=data.agente,
            skill_name="consultar_kb_agente",
            project_name=data.proyecto,
            user_request=pregunta_enriquecida,
        )
        try:
            parsed = json.loads(resultado)
        except (json.JSONDecodeError, TypeError):
            parsed = {"respuesta": resultado}
        return {"status": "ok", "agente": data.agente, "resultado": parsed}
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        log.error(f"[KB QUERY] Error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


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
    uvicorn.run(app, host="0.0.0.0", port=DASHBOARD_PORT, log_level="info")
