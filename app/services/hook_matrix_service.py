"""
hook_matrix_service — matriz de ≥12 hooks TikTok/Meta Ads por fórmula (skill hook-matrix).

Persiste en SQLite (antes solo existía como salida de chat, sin historial, sin gate).
Toda salida pasa por `deterministic_gate.verificar_hook_matrix` antes de guardarse — nunca
confía en el `total_hooks`/`validacion` que declare el propio LLM.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services import deterministic_gate
from app.services.llm_router import chat

FORMULAS = deterministic_gate.FORMULAS_HOOK

SYSTEM_PROMPT = f"""Eres un redactor de hooks de TikTok/Meta Ads para GEM OS.

Genera al menos 2 hooks por cada una de estas 6 fórmulas ({', '.join(FORMULAS)}), mínimo
12 hooks en total, para el producto/ángulo que recibas.

Reglas (las mismas que el resto de copy de GEM OS):
- Sin superlativos vacíos (increíble, fantástico, el mejor del mundo, etc.).
- Sin promesas de envío que el proveedor no pueda sostener (nunca "24-48h" ni "envío express"
  salvo que el dato venga confirmado).
- Cada hook debe funcionar en los primeros 3 segundos: la primera línea es lo que se lee
  como caption o se oye como voz en off.

Responde EXCLUSIVAMENTE con este JSON, sin texto antes ni después:
{{"hook_matrix": [{{"id": 1, "formula": "Story"|"Shock"|"Curiosity"|"Before/After"|"POV"|"Urgencia",
"angulo": "...", "formato": "tiktok_caption"|"meta_ad"|"ambos", "texto": "...",
"primera_linea_chars": 0, "apto_tiktok_caption": true, "apto_meta_ad": true,
"notas_produccion": "..."}}, ... al menos 12 elementos], "total_hooks": 0,
"recomendacion_test": "qué 2-3 hooks probar primero y por qué"}}"""


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _parsear(bruto: Optional[str]) -> Dict[str, Any]:
    if not bruto:
        return {"hook_matrix": [], "recomendacion_test": ""}
    try:
        inicio, fin = bruto.find("{"), bruto.rfind("}")
        datos = json.loads(bruto[inicio:fin + 1]) if inicio != -1 and fin != -1 else {}
    except (ValueError, TypeError):
        datos = {}
    hooks = datos.get("hook_matrix") if isinstance(datos.get("hook_matrix"), list) else []
    return {"hook_matrix": hooks, "recomendacion_test": str(datos.get("recomendacion_test", ""))[:1000]}


def generar(angulo_contexto: str) -> Dict[str, Any]:
    """Llama al modelo, verifica con el gate determinista y devuelve el resultado (sin persistir)."""
    bruto = chat(task="hook_matrix", system_prompt=SYSTEM_PROMPT,
                 user_message=f"Producto/ángulo: {angulo_contexto.strip()[:2000]}",
                 max_tokens=4096, temperature=0.4)
    resultado = _parsear(bruto)
    gate = deterministic_gate.verificar_hook_matrix(resultado)
    resultado["total_hooks"] = len(resultado["hook_matrix"])
    resultado["gate_pass"] = gate["passed"]
    resultado["gate_violations"] = gate["violations"]
    resultado["generado"] = bool(bruto)
    return resultado


def guardar(db_path: str, producto_id: Optional[int], resultado: Dict[str, Any]) -> int:
    with _db(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO hook_matrices (producto_id, hooks_json, total_hooks, validacion_json, "
            "recomendacion_test, gate_pass, creado_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (producto_id, json.dumps(resultado["hook_matrix"], ensure_ascii=False),
             resultado["total_hooks"], json.dumps(resultado.get("gate_violations", []), ensure_ascii=False),
             resultado.get("recomendacion_test", ""), int(bool(resultado.get("gate_pass"))),
             datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return cur.lastrowid


def listar(db_path: str, producto_id: Optional[int] = None) -> List[Dict[str, Any]]:
    sql, params = "SELECT * FROM hook_matrices WHERE 1=1", []
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
        f["hooks"] = json.loads(f.pop("hooks_json") or "[]")
        f["gate_violations"] = json.loads(f.pop("validacion_json") or "[]")
        f["gate_pass"] = bool(f["gate_pass"])
    return filas
