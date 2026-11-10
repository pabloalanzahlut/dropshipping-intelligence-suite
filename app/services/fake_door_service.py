"""
fake_door_service — eventos del test de demanda sin stock ni ads (skill fake-door).

`registrar_evento()` es la única función que toca un visitante real y anónimo: nunca
lanza una excepción hacia fuera (un fallo aquí no debe romper la página pública), guarda
solo un hash de la IP (nunca la IP en claro) y solo para el throttle anti-spam.

El resto (`resumen_producto`, `resumen_global`) alimenta el gate determinista
(`deterministic_gate.check_fake_door_ctr`) desde el panel interno — nada de esto decide
nada por su cuenta: solo calcula la mediana y el CTR, el humano confirma el creativo.
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_TIPOS_VALIDOS = ("visita", "clic_comprar", "email")

# Throttle anti-spam en memoria: máximo N eventos por IP por minuto. No es una medida de
# seguridad fuerte (se reinicia si el proceso se reinicia), solo evita que un script
# trivial infle la tabla de eventos de una página pública sin sesión.
_LIMITE_POR_MINUTO = 30
_eventos_por_ip: Dict[str, List[float]] = {}


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _hash_ip(ip: Optional[str]) -> Optional[str]:
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]


def limite_alcanzado(ip: Optional[str], ahora: Optional[float] = None) -> bool:
    """True si esta IP ya superó el límite de eventos en la última ventana de 60s."""
    if not ip:
        return False
    ahora = ahora or time.time()
    vistos = [t for t in _eventos_por_ip.get(ip, []) if ahora - t < 60]
    _eventos_por_ip[ip] = vistos
    return len(vistos) >= _LIMITE_POR_MINUTO


def _marcar_evento_ip(ip: Optional[str], ahora: Optional[float] = None) -> None:
    if not ip:
        return
    _eventos_por_ip.setdefault(ip, []).append(ahora or time.time())


def registrar_evento(db_path: str, producto_id: int, tipo: str, slug: str = "",
                     email: Optional[str] = None, ip: Optional[str] = None) -> bool:
    """Registra un evento del visitante. Nunca lanza — si algo falla, se registra en el
    log y se devuelve False; la página pública siempre responde «ok» para no filtrar
    detalles internos a un visitante anónimo."""
    if tipo not in _TIPOS_VALIDOS:
        return False
    if limite_alcanzado(ip):
        logger.warning(f"[FAKE_DOOR] Límite de eventos alcanzado para una IP — evento descartado.")
        return False
    try:
        with _db(db_path) as conn:
            if not conn.execute("SELECT 1 FROM productos WHERE id = ?", (producto_id,)).fetchone():
                return False
            conn.execute(
                "INSERT INTO fake_door_eventos (producto_id, slug, tipo, email, ip_hash) VALUES (?, ?, ?, ?, ?)",
                (producto_id, slug[:120], tipo, (email or "")[:200] or None, _hash_ip(ip)))
            conn.commit()
        _marcar_evento_ip(ip)
        return True
    except sqlite3.Error as exc:
        logger.error(f"[FAKE_DOOR] No se pudo registrar el evento: {exc}")
        return False


def resumen_producto(db_path: str, producto_id: int) -> Dict[str, Any]:
    with _db(db_path) as conn:
        fila = conn.execute(
            "SELECT "
            "SUM(CASE WHEN tipo='visita' THEN 1 ELSE 0 END) AS visitas, "
            "SUM(CASE WHEN tipo='clic_comprar' THEN 1 ELSE 0 END) AS clics_comprar, "
            "SUM(CASE WHEN tipo='email' THEN 1 ELSE 0 END) AS emails "
            "FROM fake_door_eventos WHERE producto_id = ?", (producto_id,)).fetchone()
    visitas = fila["visitas"] or 0
    clics = fila["clics_comprar"] or 0
    emails = fila["emails"] or 0
    ctr = round(clics / visitas, 4) if visitas else 0.0
    return {"producto_id": producto_id, "visitas": visitas, "clics_comprar": clics, "emails": emails, "ctr": ctr}


def resumen_global(db_path: str) -> List[Dict[str, Any]]:
    """CTR por producto con al menos una visita — para calcular la mediana global."""
    with _db(db_path) as conn:
        filas = conn.execute(
            "SELECT producto_id, "
            "SUM(CASE WHEN tipo='visita' THEN 1 ELSE 0 END) AS visitas, "
            "SUM(CASE WHEN tipo='clic_comprar' THEN 1 ELSE 0 END) AS clics_comprar "
            "FROM fake_door_eventos GROUP BY producto_id HAVING visitas > 0").fetchall()
    return [{"producto_id": f["producto_id"], "visitas": f["visitas"], "clics_comprar": f["clics_comprar"],
             "ctr": round(f["clics_comprar"] / f["visitas"], 4)} for f in filas]


def mediana_ctr(db_path: str, excluir_producto_id: Optional[int] = None) -> float:
    valores = sorted(r["ctr"] for r in resumen_global(db_path)
                     if r["producto_id"] != excluir_producto_id)
    if not valores:
        return 0.0
    n = len(valores)
    medio = n // 2
    return valores[medio] if n % 2 else (valores[medio - 1] + valores[medio]) / 2
