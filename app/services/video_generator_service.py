"""
video_generator_service — genera vídeo TikTok con IA (skill generar-video-ia).

Envuelve dos clientes ya existentes que no tenían persistencia:
  - `gemini_vision.analyze_product_image()` — specs del producto desde su foto.
  - `higgsfield_client.build_motion_prompt()` / `.generate_product_video()` — vídeo animado.

Si falta `HIGGSFIELD_API_KEY`, sigue el camino de fallback manual que el propio skill ya
documenta: entrega los specs y el prompt de movimiento para que el operador produzca el
vídeo a mano en vez de fallar o inventar un resultado.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services import gemini_vision, higgsfield_client

ESTADOS = ("pendiente", "generado", "fallback_manual", "error")


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _crear_job(db_path: str, producto_id: Optional[int], imagen_url: str) -> int:
    with _db(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO video_jobs (producto_id, imagen_url, estado) VALUES (?, ?, 'pendiente')",
            (producto_id, imagen_url))
        conn.commit()
        return cur.lastrowid


def _actualizar_job(db_path: str, job_id: int, estado: str, specs: Optional[Dict[str, Any]],
                    prompt_movimiento: str, video_url: Optional[str] = None, proveedor: str = "") -> None:
    with _db(db_path) as conn:
        conn.execute(
            "UPDATE video_jobs SET estado = ?, specs_json = ?, prompt_movimiento = ?, video_url = ?, "
            "proveedor = ? WHERE id = ?",
            (estado, json.dumps(specs or {}, ensure_ascii=False), prompt_movimiento, video_url, proveedor, job_id))
        conn.commit()


def generar(db_path: str, producto_id: Optional[int], imagen_url: str, nombre_producto: str,
           hook_visual: str) -> Dict[str, Any]:
    job_id = _crear_job(db_path, producto_id, imagen_url)
    specs = gemini_vision.analyze_product_image(imagen_url, task="extract_specs")
    prompt = higgsfield_client.build_motion_prompt(nombre_producto, hook_visual)

    if not os.getenv("HIGGSFIELD_API_KEY", "").strip():
        _actualizar_job(db_path, job_id, "fallback_manual", specs, prompt)
        return {"id": job_id, "estado": "fallback_manual", "specs": specs, "prompt_movimiento": prompt,
                "video_url": None, "aviso": "Falta HIGGSFIELD_API_KEY — produce el vídeo a mano con este "
                                           "prompt y específicaciones, o configura la clave en Configuración."}

    video_url = higgsfield_client.generate_product_video(imagen_url, prompt)
    estado = "generado" if video_url else "error"
    _actualizar_job(db_path, job_id, estado, specs, prompt, video_url, proveedor="higgsfield")
    return {"id": job_id, "estado": estado, "specs": specs, "prompt_movimiento": prompt, "video_url": video_url}


def listar(db_path: str, producto_id: Optional[int] = None) -> List[Dict[str, Any]]:
    sql, params = "SELECT * FROM video_jobs WHERE 1=1", []
    if producto_id is not None:
        sql += " AND producto_id = ?"
        params.append(producto_id)
    sql += " ORDER BY creado_at DESC, id DESC"
    with _db(db_path) as conn:
        try:
            filas = [dict(r) for r in conn.execute(sql, params)]
        except sqlite3.OperationalError:
            return []
    for f in filas:
        f["specs"] = json.loads(f.pop("specs_json") or "{}")
    return filas
