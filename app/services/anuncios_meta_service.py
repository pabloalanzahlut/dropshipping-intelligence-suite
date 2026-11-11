"""
anuncios_meta_service — copy estático para Meta Ads (skill redactar-anuncios-meta).

Persiste en SQLite (antes solo existía como salida de chat, sin historial). Todo el texto
pasa por `deterministic_gate.verificar_copy` tal cual (superlativos, envío irreal) — sin
cambios en el gate, según el propio contrato del skill.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services import deterministic_gate
from app.services.llm_router import chat

SYSTEM_PROMPT = """Eres un redactor de Meta Ads estáticos para GEM OS (Facebook/Instagram,
no vídeo). Genera 3 formatos a partir de los datos del producto que recibas:

Formato A (imagen única): Primary Text (máx 125 caracteres visibles), Headline (máx 27
caracteres), Descripción (máx 30 caracteres, garantía o refuerzo de confianza).

Formato B (carousel de 3 tarjetas, cada una debe entenderse sola):
1. El Problema (headline + descripción de la consecuencia de no tener el producto).
2. La Solución (headline con el beneficio principal + descripción con un dato medible).
3. La Oferta (headline con PVP/garantía + descripción con CTA y urgencia real, nunca inventada).

Formato C (A/B del primary text): variante "Dolor" (empieza por el problema) y variante
"Resultado" (empieza por la transformación) — SIEMPRE las dos, nunca una sola.

Reglas que no puedes romper:
- Prohibido superlativos vacíos (increíble, revolucionario, el mejor, etc.).
- Prohibido prometer envío en menos de 6 días (la política real es 2-5 días hábiles en
  Shopify o 5-7 días en TikTok Shop) — nunca sin confirmación del proveedor.
- Prohibido prometer resultados médicos o de pérdida de peso sin evidencia.
- Basa los beneficios solo en los datos que te den; no inventes especificaciones.

Responde EXCLUSIVAMENTE con este JSON, sin texto antes ni después:
{"formato_a": {"primary_text": "...", "headline": "...", "descripcion": "..."},
"formato_b": {"problema": {"headline": "...", "descripcion": "..."},
"solucion": {"headline": "...", "descripcion": "..."}, "oferta": {"headline": "...", "descripcion": "..."}},
"formato_c": {"dolor": "...", "resultado": "..."}}"""


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _parsear(bruto: Optional[str]) -> Dict[str, Any]:
    vacio = {"formato_a": {}, "formato_b": {}, "formato_c": {}}
    if not bruto:
        return vacio
    try:
        inicio, fin = bruto.find("{"), bruto.rfind("}")
        datos = json.loads(bruto[inicio:fin + 1]) if inicio != -1 and fin != -1 else {}
    except (ValueError, TypeError):
        return vacio
    return {
        "formato_a": datos.get("formato_a") if isinstance(datos.get("formato_a"), dict) else {},
        "formato_b": datos.get("formato_b") if isinstance(datos.get("formato_b"), dict) else {},
        "formato_c": datos.get("formato_c") if isinstance(datos.get("formato_c"), dict) else {},
    }


def _texto_para_gate(resultado: Dict[str, Any]) -> str:
    """Concatena todo el texto generado para pasarlo una sola vez por `verificar_copy`."""
    trozos: List[str] = []
    a = resultado.get("formato_a", {})
    trozos += [str(a.get("primary_text", "")), str(a.get("headline", "")), str(a.get("descripcion", ""))]
    b = resultado.get("formato_b", {})
    for tarjeta in ("problema", "solucion", "oferta"):
        t = b.get(tarjeta, {}) if isinstance(b.get(tarjeta), dict) else {}
        trozos += [str(t.get("headline", "")), str(t.get("descripcion", ""))]
    c = resultado.get("formato_c", {})
    trozos += [str(c.get("dolor", "")), str(c.get("resultado", ""))]
    return " ".join(t for t in trozos if t)


def generar(contexto_producto: str) -> Dict[str, Any]:
    bruto = chat(task="redactar_anuncio_meta", system_prompt=SYSTEM_PROMPT,
                 user_message=f"Datos del producto:\n{contexto_producto.strip()[:2000]}",
                 max_tokens=2048, temperature=0.4)
    resultado = _parsear(bruto)
    gate = deterministic_gate.verificar_copy(_texto_para_gate(resultado))
    resultado["gate_pass"] = gate["passed"]
    resultado["gate_violations"] = gate["violations"]
    resultado["generado"] = bool(bruto)
    return resultado


def guardar(db_path: str, producto_id: Optional[int], resultado: Dict[str, Any]) -> int:
    with _db(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO anuncios_meta (producto_id, formato_a_json, formato_b_json, formato_c_json, "
            "gate_pass, gate_violations_json, creado_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (producto_id, json.dumps(resultado.get("formato_a", {}), ensure_ascii=False),
             json.dumps(resultado.get("formato_b", {}), ensure_ascii=False),
             json.dumps(resultado.get("formato_c", {}), ensure_ascii=False),
             int(bool(resultado.get("gate_pass"))),
             json.dumps(resultado.get("gate_violations", []), ensure_ascii=False),
             datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return cur.lastrowid


def listar(db_path: str, producto_id: Optional[int] = None) -> List[Dict[str, Any]]:
    sql, params = "SELECT * FROM anuncios_meta WHERE 1=1", []
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
        f["formato_a"] = json.loads(f.pop("formato_a_json") or "{}")
        f["formato_b"] = json.loads(f.pop("formato_b_json") or "{}")
        f["formato_c"] = json.loads(f.pop("formato_c_json") or "{}")
        f["gate_violations"] = json.loads(f.pop("gate_violations_json") or "[]")
        f["gate_pass"] = bool(f["gate_pass"])
    return filas
