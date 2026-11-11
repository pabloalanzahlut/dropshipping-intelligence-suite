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
    # Se llama cada vez que se abre una DatabaseConnection (varias por petición web): solo se
    # avisa cuando de verdad se ejecutó algo; si no, inundaba el registro del servidor.
    logger.log(logging.INFO if count else logging.DEBUG,
               f"[MIGRATIONS] Ejecutadas {count} migraciones. Total: {len(sorted_migrations)}")
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
        ("@soyivancaicedo",  "Iván Caicedo",  "https://www.youtube.com/@soyivancaicedo",  "es", "dropshipping,productos",   2),
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

@migration(16, "Índice único de productos por vídeo y estado/filtro de tema en canales_favoritos")
def mig_0016_unico_producto_y_estado_canales(conn: sqlite3.Connection):
    # El mismo producto del mismo vídeo no se guarda dos veces (los 'sin nombre' pueden ser
    # productos distintos y quedan fuera del índice)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_product_trends_video_nombre
        ON product_trends(video_id, lower(product_name))
        WHERE product_name != 'Producto Extraído por IA'
    """)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(canales_favoritos)").fetchall()}
    for col, ddl in (("filtro_tema", "INTEGER DEFAULT 0"),
                     ("ultimo_estado", "TEXT"),
                     ("ultimo_check", "TEXT")):
        if col not in cols:
            conn.execute(f"ALTER TABLE canales_favoritos ADD COLUMN {col} {ddl}")


@migration(17, "Catálogo de productos con estados (pipeline) y su historial")
def mig_0017_catalogo_productos(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            categoria TEXT DEFAULT '',
            url_proveedor TEXT DEFAULT '',
            origen_video_id TEXT,
            costo_origen REAL,
            costo_envio REAL DEFAULT 0,
            pvp REAL,
            estado TEXT NOT NULL DEFAULT 'candidato',
            clasificacion TEXT,
            multiplicador REAL,
            margen_neto_unidad REAL,
            refutaciones TEXT DEFAULT '{}',
            veredicto_refutacion TEXT,
            demanda TEXT DEFAULT '{}',
            creativo_ok INTEGER DEFAULT 0,
            notas TEXT DEFAULT '',
            correlation_id TEXT,
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            actualizado_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_productos_estado ON productos(estado)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS producto_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            estado_anterior TEXT,
            estado_nuevo TEXT,
            nota TEXT DEFAULT '',
            correlation_id TEXT,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_producto_eventos_prod ON producto_eventos(producto_id)")


@migration(18, "Métricas diarias del negocio (ROAS, CPA) y caja diaria")
def mig_0018_metricas_negocio(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metricas_diarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            producto_id INTEGER,
            plataforma TEXT NOT NULL DEFAULT 'meta',
            gasto_ads REAL NOT NULL DEFAULT 0,
            ingresos REAL NOT NULL DEFAULT 0,
            pedidos INTEGER NOT NULL DEFAULT 0,
            cogs_pagado REAL NOT NULL DEFAULT 0,
            devoluciones REAL,
            visitantes INTEGER,
            presupuesto_diario REAL,
            notas TEXT DEFAULT '',
            correlation_id TEXT,
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL
        )
    """)
    # Una fila por día, producto y plataforma (producto 0 = tienda completa)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_metricas_dia
        ON metricas_diarias(fecha, COALESCE(producto_id, 0), plataforma)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS caja_diaria (
            fecha TEXT PRIMARY KEY,
            saldo_cuenta REAL NOT NULL DEFAULT 0,
            liberaciones_pasarela REAL NOT NULL DEFAULT 0,
            pagos_proveedor_pendientes REAL NOT NULL DEFAULT 0,
            notas TEXT DEFAULT '',
            correlation_id TEXT,
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


@migration(19, "Centro de alertas y resúmenes diarios")
def mig_0019_alertas_y_resumenes(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clave TEXT NOT NULL UNIQUE,
            nivel TEXT NOT NULL DEFAULT 'aviso',
            titulo TEXT NOT NULL,
            detalle TEXT DEFAULT '',
            enlace TEXT DEFAULT '',
            origen TEXT DEFAULT '',
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            actualizado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            vista_at TEXT,
            resuelta_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alertas_activas ON alertas(resuelta_at)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resumenes_diarios (
            fecha TEXT PRIMARY KEY,
            contenido TEXT NOT NULL,
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


@migration(20, "Avisos externos: registro de cuándo se notificó cada alerta")
def mig_0020_alertas_notificada(conn: sqlite3.Connection):
    columnas = {r[1] for r in conn.execute("PRAGMA table_info(alertas)")}
    if "notificada_at" not in columnas:
        conn.execute("ALTER TABLE alertas ADD COLUMN notificada_at TEXT")


@migration(21, "Tienda: pedidos y variantes de Shopify, importaciones de AutoDS y registro de sincronizaciones")
def mig_0021_tienda_shopify_autods(conn: sqlite3.Connection):
    # Instantánea de Shopify (se rellena con la API; los importes van en la divisa de la tienda)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tienda_pedidos (
            pedido_id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL DEFAULT '',
            creado_at TEXT NOT NULL,
            fecha TEXT NOT NULL,
            cancelado_at TEXT,
            moneda TEXT DEFAULT '',
            total REAL NOT NULL DEFAULT 0,
            subtotal REAL NOT NULL DEFAULT 0,
            descuentos REAL NOT NULL DEFAULT 0,
            envio REAL NOT NULL DEFAULT 0,
            impuestos REAL NOT NULL DEFAULT 0,
            reembolsado REAL NOT NULL DEFAULT 0,
            estado_pago TEXT DEFAULT '',
            estado_envio TEXT DEFAULT '',
            unidades INTEGER NOT NULL DEFAULT 0,
            pais TEXT DEFAULT '',
            canal TEXT DEFAULT '',
            lineas_incompletas INTEGER NOT NULL DEFAULT 0,
            actualizado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            correlation_id TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tienda_pedidos_fecha ON tienda_pedidos(fecha)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tienda_lineas (
            pedido_id TEXT NOT NULL,
            idx INTEGER NOT NULL,
            variante_id TEXT DEFAULT '',
            sku TEXT DEFAULT '',
            titulo TEXT DEFAULT '',
            cantidad INTEGER NOT NULL DEFAULT 0,
            precio_unit REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (pedido_id, idx),
            FOREIGN KEY (pedido_id) REFERENCES tienda_pedidos(pedido_id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tienda_lineas_variante ON tienda_lineas(variante_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tienda_variantes (
            variante_id TEXT PRIMARY KEY,
            producto_id TEXT NOT NULL,
            producto TEXT DEFAULT '',
            estado TEXT DEFAULT '',
            vendor TEXT DEFAULT '',
            sku TEXT DEFAULT '',
            titulo TEXT DEFAULT '',
            precio REAL NOT NULL DEFAULT 0,
            coste REAL,
            stock INTEGER,
            actualizado_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tienda_variantes_producto ON tienda_variantes(producto_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tienda_sync (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fuente TEXT NOT NULL DEFAULT 'shopify',
            iniciado_at TEXT NOT NULL,
            terminado_at TEXT,
            estado TEXT NOT NULL DEFAULT 'en_curso',
            dias INTEGER,
            pedidos INTEGER DEFAULT 0,
            variantes INTEGER DEFAULT 0,
            tienda TEXT DEFAULT '',
            moneda TEXT DEFAULT '',
            detalle TEXT DEFAULT '',
            correlation_id TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tienda_sync_fuente ON tienda_sync(fuente, id)")

    # AutoDS: exportaciones (CSV/XLSX) que el operador sube; la clave evita duplicar al reimportar
    conn.execute("""
        CREATE TABLE IF NOT EXISTS autods_importaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archivo TEXT DEFAULT '',
            sha256 TEXT NOT NULL UNIQUE,
            tipo TEXT NOT NULL,
            filas INTEGER NOT NULL DEFAULT 0,
            nuevas INTEGER NOT NULL DEFAULT 0,
            mapeo TEXT DEFAULT '',
            importado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            correlation_id TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS autods_pedidos (
            clave TEXT PRIMARY KEY,
            importacion_id INTEGER,
            pedido_tienda TEXT DEFAULT '',
            fecha TEXT NOT NULL,
            titulo TEXT DEFAULT '',
            sku TEXT DEFAULT '',
            cantidad INTEGER NOT NULL DEFAULT 1,
            precio_venta REAL,
            coste_proveedor REAL,
            coste_envio REAL,
            estado TEXT DEFAULT '',
            proveedor TEXT DEFAULT '',
            tracking TEXT DEFAULT '',
            pais TEXT DEFAULT '',
            importado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            correlation_id TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_autods_pedidos_fecha ON autods_pedidos(fecha)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_autods_pedidos_tienda ON autods_pedidos(pedido_tienda)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS autods_productos (
            clave TEXT PRIMARY KEY,
            importacion_id INTEGER,
            titulo TEXT DEFAULT '',
            sku TEXT DEFAULT '',
            coste REAL,
            precio_venta REAL,
            stock INTEGER,
            proveedor TEXT DEFAULT '',
            estado TEXT DEFAULT '',
            importado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            correlation_id TEXT
        )
    """)


@migration(22, "Marca de promoción de candidatos de product_trends al catálogo de productos")
def mig_0022_product_trends_promocion(conn: sqlite3.Connection):
    columnas = {r[1] for r in conn.execute("PRAGMA table_info(product_trends)")}
    if "promovido_a_producto_id" not in columnas:
        conn.execute("ALTER TABLE product_trends ADD COLUMN promovido_a_producto_id INTEGER")


@migration(23, "Propuestas de self_improve en SQLite (antes solo en un Markdown append-only)")
def mig_0023_propuestas_ajuste(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS propuestas_ajuste (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            resumen TEXT NOT NULL,
            analisis_md TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente',
            revisado_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_propuestas_estado ON propuestas_ajuste(estado)")


@migration(24, "Informes de investigación de nicho (skill investigar-nicho)")
def mig_0024_nicho_investigaciones(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS nicho_investigaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nicho TEXT NOT NULL,
            resumen TEXT DEFAULT '',
            angulos_json TEXT NOT NULL DEFAULT '[]',
            ranking_json TEXT NOT NULL DEFAULT '[]',
            producto_id INTEGER,
            correlation_id TEXT,
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_nicho_investigaciones_nicho ON nicho_investigaciones(nicho)")


@migration(25, "Matrices de hooks TikTok/Meta Ads (skill hook-matrix)")
def mig_0025_hook_matrices(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hook_matrices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            hooks_json TEXT NOT NULL DEFAULT '[]',
            total_hooks INTEGER NOT NULL DEFAULT 0,
            validacion_json TEXT NOT NULL DEFAULT '[]',
            recomendacion_test TEXT DEFAULT '',
            gate_pass INTEGER NOT NULL DEFAULT 0,
            correlation_id TEXT,
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hook_matrices_producto ON hook_matrices(producto_id)")


@migration(26, "Eventos de fake-door (skill fake-door): visitas, clics y emails por producto")
def mig_0026_fake_door_eventos(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fake_door_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            slug TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('visita', 'clic_comprar', 'email')),
            email TEXT,
            ip_hash TEXT,
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fake_door_producto_tipo ON fake_door_eventos(producto_id, tipo)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fake_door_slug ON fake_door_eventos(slug)")


@migration(27, "Anuncios Meta estáticos generados por IA (skill redactar-anuncios-meta)")
def mig_0027_anuncios_meta(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS anuncios_meta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            formato_a_json TEXT NOT NULL DEFAULT '{}',
            formato_b_json TEXT NOT NULL DEFAULT '{}',
            formato_c_json TEXT NOT NULL DEFAULT '{}',
            gate_pass INTEGER NOT NULL DEFAULT 0,
            gate_violations_json TEXT NOT NULL DEFAULT '[]',
            correlation_id TEXT,
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_anuncios_meta_producto ON anuncios_meta(producto_id)")


@migration(28, "Jobs de video TikTok con IA (skill generar-video-ia: Gemini Vision + Higgsfield)")
def mig_0028_video_jobs(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS video_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            imagen_url TEXT NOT NULL,
            specs_json TEXT DEFAULT '{}',
            prompt_movimiento TEXT DEFAULT '',
            video_url TEXT,
            proveedor TEXT DEFAULT '',
            estado TEXT NOT NULL DEFAULT 'pendiente',
            correlation_id TEXT,
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_video_jobs_producto ON video_jobs(producto_id)")


@migration(29, "Ofertas multi-unidad 1+1/2+2 validadas (skill oferta-multiunidad)")
def mig_0029_ofertas_multiunidad(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ofertas_multiunidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            escalones_json TEXT NOT NULL DEFAULT '{}',
            veredicto TEXT DEFAULT '',
            correlation_id TEXT,
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ofertas_multiunidad_producto ON ofertas_multiunidad(producto_id)")


@migration(30, "Secciones de la competencia clonadas a Liquid (skill clonar-seccion)")
def mig_0030_secciones_clonadas(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS secciones_clonadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            que_resuelve TEXT DEFAULT '',
            patron TEXT DEFAULT '',
            liquid_code TEXT DEFAULT '',
            css_code TEXT DEFAULT '',
            variables_json TEXT NOT NULL DEFAULT '[]',
            gate_pass INTEGER NOT NULL DEFAULT 0,
            gate_violations_json TEXT NOT NULL DEFAULT '[]',
            correlation_id TEXT,
            creado_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_secciones_clonadas_producto ON secciones_clonadas(producto_id)")
