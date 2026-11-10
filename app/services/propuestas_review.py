"""
propuestas_review — lectura y marcado de las propuestas que escribe `self_improve.py`.

Solo lee y marca «pendiente / aprobada / rechazada»: **nunca ejecuta nada**. Marcar una
propuesta como aprobada es una anotación humana, no un disparador — si algo de la
propuesta se decide aplicar, se hace a mano en otra pantalla (Validador, etc.), igual que
antes. Esto mantiene intacta la regla de `self_improve.py`: "propone, nunca aplica".
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

_ESTADOS = ("pendiente", "aprobada", "rechazada")


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def listar(db_path: str, estado: str = "") -> List[Dict[str, Any]]:
    sql, params = "SELECT * FROM propuestas_ajuste WHERE 1=1", []
    if estado in _ESTADOS:
        sql += " AND estado = ?"
        params.append(estado)
    sql += " ORDER BY creado_at DESC, id DESC"
    with _db(db_path) as conn:
        try:
            return [dict(r) for r in conn.execute(sql, params)]
        except sqlite3.OperationalError:
            return []   # la tabla llega con la migración 23; una BD muy vieja aún sin migrar no tiene nada


def obtener(db_path: str, propuesta_id: int) -> Optional[Dict[str, Any]]:
    with _db(db_path) as conn:
        r = conn.execute("SELECT * FROM propuestas_ajuste WHERE id = ?", (propuesta_id,)).fetchone()
        return dict(r) if r else None


def marcar(db_path: str, propuesta_id: int, estado: str) -> Dict[str, Any]:
    if estado not in _ESTADOS:
        raise ValueError(f"Estado desconocido: {estado}")
    with _db(db_path) as conn:
        if not conn.execute("SELECT 1 FROM propuestas_ajuste WHERE id = ?", (propuesta_id,)).fetchone():
            raise KeyError("Propuesta no encontrada")
        conn.execute("UPDATE propuestas_ajuste SET estado = ?, revisado_at = ? WHERE id = ?",
                     (estado, datetime.now().isoformat(timespec="seconds"), propuesta_id))
        conn.commit()
    return obtener(db_path, propuesta_id)
