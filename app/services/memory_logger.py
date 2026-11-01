"""
memory_logger.py — Bitácora de Memoria Activa para Agentes GEM OS v2.0
Implementa el punto 2.3 del agent.md: registro automático de todo
lo que el agente necesita recordar para futuras interacciones.
"""

import os, json
from typing import Dict, List, Optional
from datetime import datetime, timezone
from app.database.connection import DatabaseConnection


class MemoryLogger:
    """
    Sistema de memoria persistente para agentes.
    Almacena: decisiones, errores, datos recibidos, patrones.
    Formato dual: JSON Lines + SQLite (redundancia).
    """

    def __init__(self, memory_dir: str = "governance/memory",
                 db_manager: Optional[DatabaseConnection] = None):
        self.memory_dir = memory_dir
        self.db_manager = db_manager if db_manager else DatabaseConnection()
        os.makedirs(self.memory_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Inicializa tabla de memoria en SQLite."""
        try:
            with self.db_manager.get_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    CREATE TABLE IF NOT EXISTS agent_memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        agent_name TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        category TEXT DEFAULT 'info',
                        summary TEXT NOT NULL,
                        details TEXT,
                        context_hash TEXT,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                c.execute("CREATE INDEX IF NOT EXISTS idx_memory_agent ON agent_memory(agent_name)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_memory_ts ON agent_memory(timestamp)")
                conn.commit()
        except Exception as e:
            print(f"[MemoryLogger] DB init: {str(e)}")

    def log(self, agent_name: str, event_type: str, summary: str,
            category: str = "info", details: Optional[Dict] = None,
            context_hash: Optional[str] = None) -> Dict:
        """
        Registra evento en memoria del agente (implementa punto 2.3 agent.md).
        Args:
            agent_name, event_type, summary, category, details, context_hash
        Returns: Dict con entrada registrada
        """
        entry = {
            'agent_name': agent_name, 'event_type': event_type,
            'category': category, 'summary': summary,
            'details': json.dumps(details) if details else None,
            'context_hash': context_hash,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self._write_jsonl(entry)
        self._write_sqlite(entry)
        return entry

    def log_decision(self, agent_name: str, decision: str,
                     reasoning: str, data_sources: List[str] = None) -> Dict:
        """Atajo: registrar decisión."""
        return self.log(agent_name, 'decision', f"Decisión: {decision}",
                        category='business',
                        details={'reasoning': reasoning, 'data_sources': data_sources or []})

    def log_error(self, agent_name: str, error_msg: str,
                  stacktrace: str = None, critical: bool = False) -> Dict:
        """Atajo: registrar error."""
        cat = 'critical' if critical else 'technical'
        det = {'stacktrace': stacktrace} if stacktrace else None
        return self.log(agent_name, 'error', f"Error: {error_msg}", category=cat, details=det)

    def log_success(self, agent_name: str, accomplishment: str,
                    metrics: Dict = None) -> Dict:
        """Atajo: registrar éxito."""
        return self.log(agent_name, 'success', f"Éxito: {accomplishment}",
                        category='business', details=metrics)

    def recall(self, agent_name: str, limit: int = 20,
               event_type: Optional[str] = None,
               category: Optional[str] = None) -> List[Dict]:
        """
        Recupera memoria reciente de un agente.
        Permite coherencia entre sesiones (Método 2 - Memoria secuencial).
        """
        try:
            with self.db_manager.get_connection() as conn:
                c = conn.cursor()
                query = "SELECT * FROM agent_memory WHERE agent_name = ?"
                params = [agent_name]
                if event_type:
                    query += " AND event_type = ?"; params.append(event_type)
                if category:
                    query += " AND category = ?"; params.append(category)
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                c.execute(query, params)
                rows = c.fetchall()
                cols = [d[0] for d in c.description]
                return [dict(zip(cols, r)) for r in rows]
        except Exception as e:
            print(f"[MemoryLogger] recall error: {str(e)}")
            return []

    def get_context(self, agent_name: str, max_entries: int = 10) -> str:
        """Genera contexto formateado para inyectar en prompts del agente."""
        entries = self.recall(agent_name, limit=max_entries)
        if not entries:
            return "Sin memoria previa disponible."
        lines = ["=== MEMORIA ACTIVA DEL AGENTE ==="]
        for e in entries:
            ts = (e.get('timestamp') or '?')[:19]
            et = e.get('event_type', '?')
            sm = e.get('summary', '?')
            lines.append(f"[{ts}] {et.upper()}: {sm}")
        return '\n'.join(lines)

    def get_all_memory(self, limit: int = 100) -> List[Dict]:
        """Obtiene toda la memoria de todos los agentes."""
        try:
            with self.db_manager.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM agent_memory ORDER BY timestamp DESC LIMIT ?", (limit,))
                rows = c.fetchall()
                cols = [d[0] for d in c.description]
                return [dict(zip(cols, r)) for r in rows]
        except Exception as e:
            return []

    def _write_jsonl(self, entry: Dict):
        """Escribe entrada en JSON Lines como respaldo portable."""
        fp = os.path.join(self.memory_dir, f"{entry['agent_name']}_memory.jsonl")
        try:
            with open(fp, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[MemoryLogger] JSONL error: {str(e)}")

    def clear_agent_memory(self, agent_name: str) -> int:
        """Limpia la memoria de un agente específico."""
        try:
            with self.db_manager.get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM agent_memory WHERE agent_name = ?", (agent_name,))
                conn.commit()
                deleted = c.rowcount
            jl = os.path.join(self.memory_dir, f"{agent_name}_memory.jsonl")
            if os.path.exists(jl):
                open(jl, 'w').close()
            return deleted
        except Exception as e:
            print(f"[MemoryLogger] clear error: {str(e)}")
            return 0

    def memory_stats(self) -> Dict:
        """Estadísticas de memoria por agente."""
        try:
            with self.db_manager.get_connection() as conn:
                c = conn.cursor()
                c.execute("""SELECT agent_name, COUNT(*) as cnt, MAX(timestamp) as last
                    FROM agent_memory GROUP BY agent_name""")
                rows = c.fetchall()
                agents = {r[0]: {'entries': r[1], 'last': r[2]} for r in rows}
                c.execute("SELECT COUNT(*) FROM agent_memory")
                total = c.fetchone()[0]
                return {'total_entries': total, 'agents': agents}
        except Exception as e:
            return {'total_entries': 0, 'agents': {}, 'error': str(e)}
    def _write_sqlite(self, entry: Dict):
        """Escribe entrada en SQLite."""
        try:
            with self.db_manager.get_connection() as conn:
                c = conn.cursor()
                c.execute("""INSERT INTO agent_memory
                    (agent_name, event_type, category, summary, details, context_hash)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (entry['agent_name'], entry['event_type'], entry['category'],
                     entry['summary'], entry['details'], entry['context_hash']))
                conn.commit()
        except Exception as e:
            print(f"[MemoryLogger] SQLite error: {str(e)}")

    def log_data_received(self, agent_name: str, data_type: str,
                          source: str, hash_id: str = None) -> Dict:
        """Atajo: registrar datos recibidos del usuario."""
        return self.log(agent_name, 'data_received',
                        f"Datos recibidos: {data_type} de {source}",
                        category='info', context_hash=hash_id)