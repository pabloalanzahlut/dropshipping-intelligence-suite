"""
Sistema de Migraciones de Base de Datos — GEM OS Suite
=========================================================
Permite evolucionar el esquema SQLite de forma segura y versionada.

Uso:
    from app.database.migrations import run_migrations
    run_migrations(db_path)

Convención:
    - Cada migración es una función con nombre migrate_NNNN_descripcion()
    - NNNN = número secuencial de 4 dígitos
    - Se ejecutan en orden numérico
    - Solo se ejecutan una vez (trackeadas en tabla _migrations)
"""

import logging
import sqlite3
from typing import List, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Registro de migraciones: se agregan aquí en orden
_MIGRATIONS: List[Callable[[sqlite3.Connection], None]] = []


def migration(version: int, description: str):
    """Decorador para registrar una migración."""
    def decorator(func: Callable):
        func._migration_version = version
        func._migration_desc = description
        _MIGRATIONS.append(func)
        return func
    return decorator


def _ensure_migrations_table(conn: sqlite3.Connection):
    """Crea la tabla de tracking de migraciones si no existe."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            version INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            executed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def _get_executed_versions(conn: sqlite3.Connection) -> set:
    """Retorna el conjunto de versiones ya ejecutadas."""
    try:
        rows = conn.execute("SELECT version FROM _migrations").fetchall()
        return {r[0] for r in rows}
    except sqlite3.OperationalError:
        return set()


def run_migrations(db_path: str) -> int:
    """
    Ejecuta todas las migraciones pendientes en orden.

    Args:
        db_path: Ruta al archivo SQLite

    Returns:
        Número de migraciones ejecutadas
    """
    if not _MIGRATIONS:
        logger.info("[MIGRATIONS] No hay migraciones registradas.")
        return 0

    # Ordenar por versión
    sorted_migrations = sorted(_MIGRATIONS, key=lambda f: f._migration_version)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    _ensure_migrations_table(conn)
    executed = _get_executed_versions(conn)

    count = 0
    for mig in sorted_migrations:
        if mig._migration_version in executed:
            logger.debug(f"[MIGRATIONS] Versión {mig._migration_version} ya ejecutada, saltando.")
            continue

        logger.info(f"[MIGRATIONS] Ejecutando v{mig._migration_version:04d}: {mig._migration_desc}")
        try:
            mig(conn)
            conn.execute(
                "INSERT INTO _migrations (version, description) VALUES (?, ?)",
                (mig._migration_version, mig._migration_desc)
            )
            conn.commit()
            count += 1
            logger.info(f"[MIGRATIONS] ✅ v{mig._migration_version:04d} completada.")
        except Exception as e:
            conn.rollback()
            logger.error(f"[MIGRATIONS] ❌ Error en v{mig._migration_version:04d}: {e}")
            raise

    conn.close()
    logger.info(f"[MIGRATIONS] Ejecutadas {count} migraciones. Total: {len(sorted_migrations)}")
    return count


# ============================================================================
# MIGRACIONES REGISTRADAS
# ============================================================================

@migration(1, "Crear tabla ai_cost_log para control de presupuesto")
def mig_0001_ai_cost_log(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_cost_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT NOT NULL,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            layer_used TEXT NOT NULL,
            model_name TEXT DEFAULT '',
            cost_usd REAL DEFAULT 0.0,
            cumulative_usd REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


@migration(2, "Agregar índice para búsqueda rápida en ai_cost_log")
def mig_0002_cost_log_index(conn: sqlite3.Connection):
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_cost_log_created
        ON ai_cost_log(created_at)
    """)


@migration(3, "Agregar columna budget_month a productos_validados")
def mig_0003_budget_month(conn: sqlite3.Connection):
    # Verificar si la columna ya existe
    cursor = conn.execute("PRAGMA table_info(productos_validados)")
    cols = {r[1] for r in cursor.fetchall()}
    if "budget_month" not in cols:
        conn.execute("""
            ALTER TABLE productos_validados
            ADD COLUMN budget_month TEXT DEFAULT ''
        """)


@migration(4, "Crear tabla app_settings para configuraciones persistentes")
def mig_0004_app_settings(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


@migration(5, "Crear tabla update_check para tracking de actualizaciones")
def mig_0005_update_check(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS update_check (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version_checked TEXT NOT NULL,
            version_available TEXT,
            checked_at TEXT DEFAULT CURRENT_TIMESTAMP,
            downloaded BOOLEAN DEFAULT 0
        )
    """)


@migration(6, "Crear tabla canales_favoritos con metadata extendida")
def mig_0006_canales_favoritos(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS canales_favoritos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            handle TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            url TEXT NOT NULL,
            idioma TEXT DEFAULT 'es',
            especialidad TEXT DEFAULT 'general',
            tags TEXT DEFAULT '',
            prioridad INTEGER DEFAULT 5,
            activo BOOLEAN DEFAULT 1,
            last_scan_at TEXT,
            video_count INTEGER DEFAULT 0,
            notas TEXT DEFAULT '',
            agregado_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_canales_handle ON canales_favoritos(handle)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_canales_especialidad ON canales_favoritos(especialidad)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_canales_prioridad ON canales_favoritos(prioridad)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_canales_activo ON canales_favoritos(activo)")
    # Seed: los 5 canales actuales
    canales = [
        ("@adriansaenz",  "Adrián Sáenz",  "https://www.youtube.com/@adriansaenz",  "es", "ads,shopify,dropshipping", 1),
        ("@ivancaicedo",  "Iván Caicedo",  "https://www.youtube.com/@ivancaicedo",  "es", "dropshipping,productos",   2),
        ("@javiecom",     "JaviEcom",      "https://www.youtube.com/@javiecom",     "es", "shopify,ecom",            2),
        ("@marcverdu",    "Marc Verdú",    "https://www.youtube.com/@marcverdu",    "es", "shopify,productos",       3),
        ("@ecomilions","Vic Ecomilions","https://www.youtube.com/@ecomilions","es", "dropshipping,scaling",    3),
    ]
    for handle, nombre, url, idioma, tags, prioridad in canales:
        conn.execute(
            "INSERT OR IGNORE INTO canales_favoritos (handle, nombre, url, idioma, especialidad, tags, prioridad) VALUES (?,?,?,?,?,?,?)",
            (handle, nombre, url, idioma, "general", tags, prioridad)
        )


@migration(7, "Crear tabla videos_favoritos con seed de 3 videos confirmados")
def mig_0007_videos_favoritos(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS videos_favoritos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,
            canal TEXT NOT NULL,
            url TEXT NOT NULL,
            razon TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            transcripcion_procesada BOOLEAN DEFAULT 0,
            guardado_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vfav_canal ON videos_favoritos(canal)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vfav_tags ON videos_favoritos(tags)")
    videos = [
        ("4j7Vi60WUrU", "Tutorial Completo De TikTok Ads Para Principiantes (2026)",
         "Adrián Sáenz", "https://www.youtube.com/watch?v=4j7Vi60WUrU",
         "Tutorial ads 2026", "tiktok,ads,principiantes"),
        ("AsHQy6lAiig", "Curso Gratis De Google Ads Para Principiantes (2026)",
         "Adrián Sáenz", "https://www.youtube.com/watch?v=AsHQy6lAiig",
         "Curso ads gratuito 2026", "google-ads,principiantes"),
        ("FgWCRB0YWPk", "CÓMO VENDER USANDO FACEBOOK ADS | 4 Errores Al Hacer Dropshipping con Shopify",
         "Adrián Sáenz", "https://www.youtube.com/watch?v=FgWCRB0YWPk",
         "Errores clave Facebook Ads + Shopify", "facebook-ads,shopify,errores"),
    ]
    for video_id, titulo, canal, url, razon, tags in videos:
        conn.execute(
            "INSERT OR IGNORE INTO videos_favoritos (video_id, titulo, canal, url, razon, tags) VALUES (?,?,?,?,?,?)",
            (video_id, titulo, canal, url, razon, tags)
        )


@migration(8, "Crear tabla playlists_favoritas con seed playlist personal del usuario")
def mig_0008_playlists_favoritas(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS playlists_favoritas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,
            canal TEXT DEFAULT '',
            url TEXT NOT NULL,
            es_privada BOOLEAN DEFAULT 0,
            tags TEXT DEFAULT '',
            activa BOOLEAN DEFAULT 1,
            last_scan_at TEXT,
            video_count INTEGER DEFAULT 0,
            agregada_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_plfav_activa ON playlists_favoritas(activa)")
    conn.execute(
        "INSERT OR IGNORE INTO playlists_favoritas (playlist_id, titulo, canal, url, es_privada, tags) VALUES (?,?,?,?,?,?)",
        ("PLrs1PAk24jHeU8waSkHzgQTHmduOk9xMn", "DROPSHIPPING - NEGOCIO 2",
         "Personal", "https://www.youtube.com/playlist?list=PLrs1PAk24jHeU8waSkHzgQTHmduOk9xMn",
         1, "dropshipping,shopify,personal")
    )


@migration(9, "Agregar columna idioma a transcripciones_youtube")
def mig_0009_idioma_transcripciones(conn: sqlite3.Connection):
    cursor = conn.execute("PRAGMA table_info(transcripciones_youtube)")
    cols = {r[1] for r in cursor.fetchall()}
    if "idioma" not in cols:
        conn.execute("ALTER TABLE transcripciones_youtube ADD COLUMN idioma TEXT DEFAULT 'es'")


@migration(10, "Agregar columnas tags y especialidad a video_sources")
def mig_0010_tags_video_sources(conn: sqlite3.Connection):
    cursor = conn.execute("PRAGMA table_info(video_sources)")
    cols = {r[1] for r in cursor.fetchall()}
    if "tags" not in cols:
        conn.execute("ALTER TABLE video_sources ADD COLUMN tags TEXT DEFAULT ''")
    if "especialidad" not in cols:
        conn.execute("ALTER TABLE video_sources ADD COLUMN especialidad TEXT DEFAULT 'general'")


@migration(11, "Crear índice compuesto canal+fecha en transcripciones y vista v_resumen_canales")
def mig_0011_indice_canal_fecha_y_vista(conn: sqlite3.Connection):
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_transcripciones_canal_fecha
        ON transcripciones_youtube(canal, fecha DESC)
    """)
    conn.execute("DROP VIEW IF EXISTS v_resumen_canales")
    conn.execute("""
        CREATE VIEW v_resumen_canales AS
        SELECT
            cf.nombre,
            cf.handle,
            cf.especialidad,
            cf.prioridad,
            cf.idioma,
            cf.tags,
            COUNT(DISTINCT vs.video_id) AS videos_descargados,
            MAX(ty.creada_at)           AS ultimo_video_procesado
        FROM canales_favoritos cf
        LEFT JOIN video_sources vs ON vs.channel_name = cf.nombre
        LEFT JOIN transcripciones_youtube ty ON ty.canal = cf.nombre
        GROUP BY cf.handle
    """)


@migration(12, "Agregar columna valor_score a product_trends")
def mig_0012_valor_score(conn: sqlite3.Connection):
    cursor = conn.execute("PRAGMA table_info(product_trends)")
    cols = {r[1] for r in cursor.fetchall()}
    if "valor_score" not in cols:
        conn.execute("ALTER TABLE product_trends ADD COLUMN valor_score REAL DEFAULT 0.0")


@migration(13, "Crear tabla importaciones_masivas para importación por URL")
def mig_0013_importaciones_masivas(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS importaciones_masivas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            correlation_id TEXT UNIQUE NOT NULL,
            url_origen TEXT NOT NULL,
            plataforma TEXT NOT NULL,
            product_id_externo TEXT DEFAULT '',
            shopify_draft_id TEXT,
            status TEXT DEFAULT 'pending',
            validacion_financiera TEXT DEFAULT '{}',
            error_msg TEXT,
            creada_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_import_status ON importaciones_masivas(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_import_plataforma ON importaciones_masivas(plataforma)")


@migration(14, "Agregar columna correlation_id a productos_validados")
def mig_0014_correlation_id_productos(conn: sqlite3.Connection):
    cursor = conn.execute("PRAGMA table_info(productos_validados)")
    cols = {r[1] for r in cursor.fetchall()}
    if "correlation_id" not in cols:
        conn.execute("""
            ALTER TABLE productos_validados
            ADD COLUMN correlation_id TEXT DEFAULT ''
        """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_productos_correlation_id
        ON productos_validados(correlation_id)
    """)


@migration(15, "Agregar columna vertical a productos_validados")
def mig_0015_vertical_productos(conn: sqlite3.Connection):
    cursor = conn.execute("PRAGMA table_info(productos_validados)")
    cols = {r[1] for r in cursor.fetchall()}
    if "vertical" not in cols:
        conn.execute("""
            ALTER TABLE productos_validados
            ADD COLUMN vertical TEXT DEFAULT ''
        """)