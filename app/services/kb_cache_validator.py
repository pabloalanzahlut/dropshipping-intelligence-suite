import sqlite3
from typing import Optional, Dict, Any

class KBCacheValidator:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from app.config.path_manager import PathManager
            db_path = str(PathManager.get_paths()['db'])
        self.db_path = db_path

    def check_video_exists(self, video_id: str) -> bool:
        """Verifica de forma fulminante si el ID del video ya está indexado en la KB."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM video_sources WHERE video_id = ?", (video_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def get_cached_knowledge(self, video_id: str) -> Dict[str, Any]:
        """Recupera la información estructurada directamente de la base de datos sin usar internet."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Permite acceder por nombre de columna
        cursor = conn.cursor()
        
        knowledge = {
            "source": {},
            "products": [],
            "conversion": [],
            "operations": []
        }
        
        # Obtener fuente
        cursor.execute("SELECT * FROM video_sources WHERE video_id = ?", (video_id,))
        source = cursor.fetchone()
        if source:
            knowledge["source"] = dict(source)
            
            # Obtener Productos Relacionados
            cursor.execute("SELECT * FROM product_trends WHERE video_id = ?", (video_id,))
            knowledge["products"] = [dict(row) for row in cursor.fetchall()]
            
            # Obtener Fórmulas de Conversión
            cursor.execute("SELECT * FROM conversion_formulas WHERE video_id = ?", (video_id,))
            knowledge["conversion"] = [dict(row) for row in cursor.fetchall()]
            
            # Obtener Operaciones y Tráfico
            cursor.execute("SELECT * FROM operations_traffic WHERE video_id = ?", (video_id,))
            knowledge["operations"] = [dict(row) for row in cursor.fetchall()]
            
        conn.close()
        return knowledge
