"""
clonar_seccion_service — HTML de la competencia → Liquid para Shopify (skill clonar-seccion).

Se copia el patrón (urgencia, prueba social, garantía, comparativa), nunca el contenido
del competidor. Todo el texto generado pasa por `deterministic_gate.verificar_copy` antes
de guardarse — el propio skill ya nombra ese paso como su gate.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services import deterministic_gate
from app.services.llm_router import chat

SYSTEM_PROMPT = """Eres un desarrollador de temas Shopify para GEM OS. Recibes el HTML de
una sección de la tienda de un competidor (copiado con "Copy outerHTML" del inspector del
navegador) y debes convertirla en una sección Liquid propia.

Pasos:
1. Identifica por qué funciona esa sección: ¿qué objeción resuelve? ¿es urgencia, prueba
   social, garantía o comparativa? ¿qué dato variable muestra (stock, reseñas, plazo)?
2. Conserva la estructura y el patrón — el texto y los datos del competidor se reemplazan
   por variables de Shopify (product.title, product.selected_or_first_available_variant.
   inventory_quantity, etc.), nunca se copian literalmente.
3. Convierte a Liquid con sintaxis válida ({%- ... -%}, {{ ... }}).
4. Renombra las clases CSS con un prefijo propio para no colisionar con el tema.
5. Si la sección muestra un dato que la tienda no tiene de verdad (reseñas reales, unidades
   vendidas), no lo inventes: dilo en las notas en vez de inventar la fuente.

Nunca reproduzcas textos, imágenes o la marca del competidor — solo el patrón.

Responde EXCLUSIVAMENTE con este JSON, sin texto antes ni después:
{"que_resuelve": "...", "patron": "urgencia"|"prueba_social"|"garantia"|"comparativa",
"liquid_code": "...", "css_code": "...", "variables": ["product.title", ...], "notas": "..."}"""


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _parsear(bruto: Optional[str]) -> Dict[str, Any]:
    vacio = {"que_resuelve": "", "patron": "", "liquid_code": "", "css_code": "", "variables": [], "notas": ""}
    if not bruto:
        return vacio
    try:
        inicio, fin = bruto.find("{"), bruto.rfind("}")
        datos = json.loads(bruto[inicio:fin + 1]) if inicio != -1 and fin != -1 else {}
    except (ValueError, TypeError):
        return vacio
    if not isinstance(datos, dict):
        return vacio
    return {
        "que_resuelve": str(datos.get("que_resuelve", ""))[:500],
        "patron": str(datos.get("patron", ""))[:50],
        "liquid_code": str(datos.get("liquid_code", "")),
        "css_code": str(datos.get("css_code", "")),
        "variables": datos.get("variables") if isinstance(datos.get("variables"), list) else [],
        "notas": str(datos.get("notas", ""))[:1000],
    }


def clonar(html_competencia: str, nota: str = "") -> Dict[str, Any]:
    if not html_competencia.strip():
        raise ValueError("Pega el HTML de la sección a clonar.")
    mensaje = f"HTML de la sección:\n{html_competencia.strip()[:6000]}"
    if nota.strip():
        mensaje += f"\n\nQué quiero conservar: {nota.strip()[:500]}"
    bruto = chat(task="clonar_seccion", system_prompt=SYSTEM_PROMPT, user_message=mensaje,
                 max_tokens=3072, temperature=0.2)
    resultado = _parsear(bruto)
    texto_a_verificar = " ".join([resultado["que_resuelve"], resultado["notas"]])
    gate = deterministic_gate.verificar_copy(texto_a_verificar)
    resultado["gate_pass"] = gate["passed"]
    resultado["gate_violations"] = gate["violations"]
    resultado["generado"] = bool(bruto)
    return resultado


def guardar(db_path: str, producto_id: Optional[int], resultado: Dict[str, Any]) -> int:
    with _db(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO secciones_clonadas (producto_id, que_resuelve, patron, liquid_code, css_code, "
            "variables_json, gate_pass, gate_violations_json, creado_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (producto_id, resultado.get("que_resuelve", ""), resultado.get("patron", ""),
             resultado.get("liquid_code", ""), resultado.get("css_code", ""),
             json.dumps(resultado.get("variables", []), ensure_ascii=False),
             int(bool(resultado.get("gate_pass"))),
             json.dumps(resultado.get("gate_violations", []), ensure_ascii=False),
             datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return cur.lastrowid


def listar(db_path: str, producto_id: Optional[int] = None) -> List[Dict[str, Any]]:
    sql, params = "SELECT * FROM secciones_clonadas WHERE 1=1", []
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
        f["variables"] = json.loads(f.pop("variables_json") or "[]")
        f["gate_violations"] = json.loads(f.pop("gate_violations_json") or "[]")
        f["gate_pass"] = bool(f["gate_pass"])
    return filas
