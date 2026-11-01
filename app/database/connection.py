import sqlite3
import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseConnection:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from app.config.path_manager import PathManager
            paths = PathManager.get_paths()
            self.db_path = str(paths['db'])
        else:
            self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()
        # Ejecutar migraciones pendientes
        self._run_migrations()

    def _run_migrations(self):
        """Ejecuta migraciones de esquema al iniciar la conexión."""
        try:
            from app.database.migrations import run_migrations
            count = run_migrations(self.db_path)
            if count > 0:
                logger.info(f"[DB] {count} migraciones ejecutadas.")
        except Exception as e:
            logger.warning(f"[DB] Error ejecutando migraciones: {e}")

    def get_connection(self) -> sqlite3.Connection:
        """Establece una conexión segura con la base de datos relacional SQLite."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  
        conn.execute("PRAGMA foreign_keys = ON;")  
        return conn

    def init_db(self):
        """Inicializa el esquema relacional optimizado para GEM OS de forma idempotente."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS video_sources (
                video_id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                title TEXT NOT NULL,
                channel_name TEXT NOT NULL,
                content_hash TEXT UNIQUE NOT NULL,
                processed_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS transcripciones_youtube (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                titulo TEXT NOT NULL,
                canal TEXT NOT NULL,
                fecha TEXT NOT NULL,
                transcripcion_texto TEXT NOT NULL,
                transcripcion_limpia TEXT,
                hash_md5 TEXT UNIQUE NOT NULL,
                tokens_original INTEGER DEFAULT 0,
                tokens_limpios INTEGER DEFAULT 0,
                procesada BOOLEAN DEFAULT 0,
                creada_at TEXT DEFAULT CURRENT_TIMESTAMP,
                actualizada_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES video_sources(video_id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS productos_validados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT UNIQUE NOT NULL,
                costo_origen REAL NOT NULL,
                pvp REAL,
                margen_bruto REAL,
                status_validacion TEXT DEFAULT 'pendiente',
                validado_regla_3x BOOLEAN DEFAULT 0,
                peso_kg REAL DEFAULT 0.0,
                nota_auditoria TEXT,
                creada_at TEXT DEFAULT CURRENT_TIMESTAMP,
                actualizada_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS product_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                product_name TEXT NOT NULL,
                niche TEXT NOT NULL,
                wow_factor TEXT,
                estimated_margin REAL DEFAULT 3.0,
                competitor_weaknesses TEXT,
                validated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES video_sources(video_id) ON DELETE SET NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS conversion_formulas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                category TEXT NOT NULL,
                framework_name TEXT DEFAULT 'AIDA',
                raw_structure TEXT NOT NULL,
                persuasion_triggers TEXT,
                recommended_apps TEXT,
                FOREIGN KEY (video_id) REFERENCES video_sources(video_id) ON DELETE SET NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS operations_traffic (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                traffic_source TEXT NOT NULL,
                scaling_strategy TEXT,
                logistics_notes TEXT,
                weight_kg REAL DEFAULT 0.0,
                gateways_legal TEXT,
                FOREIGN KEY (video_id) REFERENCES video_sources(video_id) ON DELETE SET NULL
            );
            """
        ]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for query in queries:
                cursor.execute(query)
            
            # Creación automática de índices aceleradores semánticos
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trends_niche ON product_trends(niche);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversion_cat ON conversion_formulas(category);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_traffic_source ON operations_traffic(traffic_source);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripciones_md5 ON transcripciones_youtube(hash_md5);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripciones_procesada ON transcripciones_youtube(procesada);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_sku ON productos_validados(sku);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_status ON productos_validados(status_validacion);")
            conn.commit()

    def check_video_processed(self, content_hash: str) -> bool:
        """Idempotency Guard basado en el hash MD5 de la transcripción cruda."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM video_sources WHERE content_hash = ?", (content_hash,))
            return cursor.fetchone() is not None
