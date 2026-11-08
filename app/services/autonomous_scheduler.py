"""
Autonomous Scheduler — Agentes autónomos GEM OS.

Implementa el capítulo "Agentes autónomos" (8:15) del video Xavier Mitjana
"Así se usa la IA en 2027 (15 usos que casi nadie conoce)".

El pipeline corre solo sin intervención manual:
  - Cada 2h: YouTube Monitor → detecta nuevos videos de los mentores
  - Cada 2h: Transcript Cleaner → limpia e ingesta en KB
  - Cada 6h: Clasificador automático → HOT/WARM/COLD en SQLite
  - Cada 24h: Reporte diario → Google Sheets Dashboard

Uso:
    python -m app.services.autonomous_scheduler        # corre en foreground
    python -m app.services.autonomous_scheduler --once  # ejecuta ciclo único y sale

Dependencias: pip install schedule
"""

import os
import time
import logging
import argparse
import threading
from datetime import datetime
from typing import Callable

try:
    import schedule
except ImportError:
    raise SystemExit("Instala schedule: pip install schedule")

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── Locks para evitar solapamiento de tareas ──────────────────────────────────
_lock_youtube = threading.Lock()
_lock_classify = threading.Lock()
_lock_report = threading.Lock()


def _run_job(name: str, fn: Callable, lock: threading.Lock) -> None:
    """Ejecuta un job con lock para evitar ejecuciones simultáneas."""
    if not lock.acquire(blocking=False):
        logger.warning(f"[SCHEDULER] '{name}' ya en ejecución — salteando ciclo")
        return
    try:
        logger.info(f"[SCHEDULER] ▶ Iniciando: {name}")
        fn()
        logger.info(f"[SCHEDULER] ✓ Completado: {name}")
    except Exception as e:
        logger.error(f"[SCHEDULER] ✗ Error en '{name}': {e}")
    finally:
        lock.release()


# ── Tareas del pipeline ───────────────────────────────────────────────────────

def job_youtube_monitor() -> None:
    """Detecta nuevos videos de los canales mentores y descarga transcripciones."""
    try:
        from app.services.youtube_channel_monitor import YouTubeChannelMonitor
        monitor = YouTubeChannelMonitor()
        new_videos = monitor.check_all_channels()
        if new_videos:
            logger.info(f"[YOUTUBE_MONITOR] {len(new_videos)} nuevos videos detectados")
        else:
            logger.info("[YOUTUBE_MONITOR] Sin nuevos videos")
    except Exception as e:
        logger.error(f"[YOUTUBE_MONITOR] {e}")


def job_transcript_cleaner() -> None:
    """Limpia transcripciones crudas e ingesta en la Knowledge Base."""
    try:
        from app.services.transcript_cleaner import TranscriptCleaner
        cleaner = TranscriptCleaner()
        processed = cleaner.process_pending()
        logger.info(f"[TRANSCRIPT_CLEANER] {processed} transcripciones procesadas")
    except Exception as e:
        logger.error(f"[TRANSCRIPT_CLEANER] {e}")


def job_classify_products() -> None:
    """
    Clasifica automáticamente productos nuevos en la KB: HOT / WARM / COLD.
    Usa el LLM router → Claude Sonnet para clasificación crítica.
    """
    try:
        from app.services.llm_router import chat

        # Leer transcripciones no clasificadas desde la KB
        import sqlite3
        db_path = os.getenv("DATABASE_PATH", "app/database/dropshipping_suite.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, titulo, transcripcion_limpia FROM product_trends "
            "WHERE clasificacion IS NULL LIMIT 10"
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            logger.info("[CLASSIFY] Sin productos pendientes de clasificación")
            return

        from app.services.validator_rules import SYSTEM_PROMPT_CLASIFICACION
        classified = 0
        for row_id, titulo, transcripcion in rows:
            result = chat(
                task="clasificar_producto",
                system_prompt=SYSTEM_PROMPT_CLASIFICACION,
                user_message=f"Título: {titulo}\n\nTranscripción:\n{transcripcion[:3000]}",
                max_tokens=512,
                temperature=0.0,
            )
            if result:
                conn = sqlite3.connect(db_path)
                conn.execute(
                    "UPDATE product_trends SET clasificacion=?, clasificado_at=? WHERE id=?",
                    (result[:50], datetime.utcnow().isoformat(), row_id),
                )
                conn.commit()
                conn.close()
                classified += 1

        logger.info(f"[CLASSIFY] {classified}/{len(rows)} productos clasificados")

    except Exception as e:
        logger.error(f"[CLASSIFY] {e}")


def job_daily_report() -> None:
    """
    Genera el reporte diario y actualiza el Google Sheets Dashboard.
    Columnas: fecha, videos_nuevos, productos_hot, productos_warm, alertas.
    """
    try:
        import sqlite3
        import json
        db_path = os.getenv("DATABASE_PATH", "app/database/dropshipping_suite.db")
        today = datetime.utcnow().date().isoformat()

        conn = sqlite3.connect(db_path)
        hot = conn.execute(
            "SELECT COUNT(*) FROM product_trends WHERE clasificacion LIKE '%HOT%' "
            "AND DATE(clasificado_at) = ?", (today,)
        ).fetchone()[0]
        warm = conn.execute(
            "SELECT COUNT(*) FROM product_trends WHERE clasificacion LIKE '%WARM%' "
            "AND DATE(clasificado_at) = ?", (today,)
        ).fetchone()[0]
        conn.close()

        logger.info(f"[DAILY_REPORT] {today}: HOT={hot} WARM={warm}")

        # Escribir en Google Sheets si las credenciales están disponibles
        creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
        sheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
        if creds_path and sheet_id and os.path.exists(creds_path):
            _update_google_sheets(today, hot, warm)

    except Exception as e:
        logger.error(f"[DAILY_REPORT] {e}")


def _update_google_sheets(date: str, hot: int, warm: int) -> None:
    """Añade fila al tab ROAS_Diario del dashboard GEM OS."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds = Credentials.from_service_account_file(
            os.getenv("GOOGLE_CREDENTIALS_PATH"),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID"))
        ws = sh.worksheet("ROAS_Diario")
        ws.append_row([date, hot, warm, "auto"], value_input_option="USER_ENTERED")
        logger.info(f"[SHEETS] Fila añadida: {date}")
    except Exception as e:
        logger.error(f"[SHEETS] No se pudo actualizar Google Sheets: {e}")


# ── Configuración del schedule ────────────────────────────────────────────────

def setup_schedule() -> None:
    """
    Registra todos los jobs con sus intervalos.
    Intervalos basados en CLAUDE.md config (YOUTUBE_MONITOR_SYNC_INTERVAL_HOURS=2).
    """
    sync_hours = int(os.getenv("YOUTUBE_MONITOR_SYNC_INTERVAL_HOURS", "2"))

    # YouTube Monitor + Transcript Cleaner: cada N horas
    schedule.every(sync_hours).hours.do(
        _run_job, "youtube_monitor", job_youtube_monitor, _lock_youtube
    )
    schedule.every(sync_hours).hours.do(
        _run_job, "transcript_cleaner", job_transcript_cleaner, _lock_youtube
    )

    # Clasificación: cada 6 horas
    schedule.every(6).hours.do(
        _run_job, "classify_products", job_classify_products, _lock_classify
    )

    # Reporte diario: a las 08:00 UTC
    schedule.every().day.at("08:00").do(
        _run_job, "daily_report", job_daily_report, _lock_report
    )

    logger.info(
        f"[SCHEDULER] Schedule configurado: "
        f"monitor={sync_hours}h | classify=6h | report=08:00 UTC"
    )


def run_once() -> None:
    """Ejecuta todos los jobs una sola vez (para testing o trigger manual)."""
    logger.info("[SCHEDULER] Modo --once: ejecutando todos los jobs")
    _run_job("youtube_monitor",   job_youtube_monitor,   _lock_youtube)
    _run_job("transcript_cleaner", job_transcript_cleaner, _lock_youtube)
    _run_job("classify_products", job_classify_products, _lock_classify)
    _run_job("daily_report",      job_daily_report,      _lock_report)
    logger.info("[SCHEDULER] Ciclo único completado")


def run_forever() -> None:
    """Loop principal — corre indefinidamente comprobando jobs pendientes."""
    setup_schedule()
    logger.info("[SCHEDULER] Agente autónomo GEM OS activo ✓")

    # Ejecutar ciclo inicial al arrancar
    _run_job("youtube_monitor",   job_youtube_monitor,   _lock_youtube)
    _run_job("transcript_cleaner", job_transcript_cleaner, _lock_youtube)

    while True:
        schedule.run_pending()
        time.sleep(60)  # comprobar cada minuto


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GEM OS Autonomous Scheduler")
    parser.add_argument("--once", action="store_true", help="Ejecutar ciclo único y salir")
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_forever()
