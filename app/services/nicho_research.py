"""
nicho_research — informe de 10 ángulos de ataque para un nicho (skill investigar-nicho).

Persiste en SQLite (antes solo existía como salida de chat, sin historial). No es una
decisión financiera ni de copy, así que no pasa por `deterministic_gate.py`: es un informe
de investigación para que el humano decida qué ángulo probar.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.llm_router import chat

SYSTEM_PROMPT = """Eres un investigador de nichos de dropshipping para GEM OS.

Dado un nicho, genera un informe con:
1. Un resumen de hasta 5 líneas.
2. 10 ángulos de ataque, cada uno con: problema severo que resuelve, público objetivo
   (demográfico, intereses para Meta Ads, comportamiento), tipo de producto, rango de
   precio (costo de origen estimado $5-15, PVP sugerido, si cumple la regla 3x), un hook
   de anuncio, y una señal de demanda observable.
3. Un ranking de esos 10 ángulos ponderado: urgencia 40%, facilidad de cumplir 3x 30%,
   calidad del targeting 20%, riesgo logístico 10% (menor riesgo = mejor).

No inventes cifras de venta reales que no puedas justificar — basa el ranking en lo que
es razonable estimar de estos criterios, y dilo si un ángulo tiene poca información.

Responde EXCLUSIVAMENTE con este JSON, sin texto antes ni después:
{"resumen": "...", "angulos": [{"id": 1, "problema": "...", "publico_objetivo": {"demografico": "...", "intereses_meta": "...", "comportamiento": "..."}, "tipo_producto": "...", "precio": {"costo_origen": 0, "pvp_sugerido": 0, "cumple_3x": true}, "hook": "...", "senal_demanda": "..."}, ... 10 elementos], "ranking": [{"angulo_id": 1, "score": 0, "motivo": "..."}, ... ordenado de mejor a peor]}"""


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _parsear(bruto: Optional[str]) -> Dict[str, Any]:
    if not bruto:
        return {"resumen": "", "angulos": [], "ranking": []}
    try:
        inicio, fin = bruto.find("{"), bruto.rfind("}")
        datos = json.loads(bruto[inicio:fin + 1]) if inicio != -1 and fin != -1 else {}
    except (ValueError, TypeError):
        datos = {}
    return {
        "resumen": str(datos.get("resumen", ""))[:2000],
        "angulos": datos.get("angulos") if isinstance(datos.get("angulos"), list) else [],
        "ranking": datos.get("ranking") if isinstance(datos.get("ranking"), list) else [],
    }


def investigar(nicho: str, contexto: str = "") -> Dict[str, Any]:
    """Llama al modelo y devuelve el informe parseado (sin persistir)."""
    if not nicho.strip():
        raise ValueError("El nicho no puede estar vacío.")
    mensaje = f"Nicho: {nicho.strip()}"
    if contexto.strip():
        mensaje += f"\n\nContexto adicional:\n{contexto.strip()[:3000]}"
    bruto = chat(task="investigar_nicho", system_prompt=SYSTEM_PROMPT, user_message=mensaje,
                 max_tokens=4096, temperature=0.3)
    resultado = _parsear(bruto)
    resultado["nicho"] = nicho.strip()
    resultado["generado"] = bool(bruto)
    return resultado


def guardar_investigacion(db_path: str, nicho: str, resumen: str, angulos: List[Dict[str, Any]],
                          ranking: List[Dict[str, Any]], producto_id: Optional[int] = None) -> int:
    with _db(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO nicho_investigaciones (nicho, resumen, angulos_json, ranking_json, producto_id, creado_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (nicho, resumen, json.dumps(angulos, ensure_ascii=False), json.dumps(ranking, ensure_ascii=False),
             producto_id, datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return cur.lastrowid


def listar(db_path: str, nicho: str = "") -> List[Dict[str, Any]]:
    sql, params = "SELECT * FROM nicho_investigaciones WHERE 1=1", []
    if nicho.strip():
        sql += " AND nicho LIKE ?"
        params.append(f"%{nicho.strip()}%")
    sql += " ORDER BY creado_at DESC, id DESC"
    with _db(db_path) as conn:
        try:
            filas = [dict(r) for r in conn.execute(sql, params)]
        except sqlite3.OperationalError:
            return []
    for f in filas:
        f["angulos"] = json.loads(f.pop("angulos_json") or "[]")
        f["ranking"] = json.loads(f.pop("ranking_json") or "[]")
    return filas


def obtener(db_path: str, investigacion_id: int) -> Optional[Dict[str, Any]]:
    with _db(db_path) as conn:
        r = conn.execute("SELECT * FROM nicho_investigaciones WHERE id = ?", (investigacion_id,)).fetchone()
        if not r:
            return None
        f = dict(r)
    f["angulos"] = json.loads(f.pop("angulos_json") or "[]")
    f["ranking"] = json.loads(f.pop("ranking_json") or "[]")
    return f
