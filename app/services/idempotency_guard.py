import hashlib
import sqlite3
from typing import Optional

class IdempotencyGuard:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from app.config.path_manager import PathManager
            db_path = str(PathManager.get_paths()['db'])
        self.db_path = db_path

    def calculate_hash(self, text: str) -> str:
        """Genera el identificador único basado en el contenido del texto."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def is_already_processed(self, content_hash: str) -> bool:
        """Verifica en SQLite si el hash ya existe para bloquear duplicados."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM video_sources WHERE content_hash = ?", (content_hash,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
