"""
product_catalog — el catálogo de productos y su recorrido por el pipeline de CLAUDE.md.

Estados (en orden; "nunca saltar un paso"):
    candidato → clasificado → refutado → validado → creativo → tienda → escalado
    (y "descartado" desde cualquier punto)

Cada paso tiene una condición REAL que se comprueba aquí (Python puro, sin IA):
    clasificado  necesita coste, envío y PVP → multiplicador sobre coste landed → HOT/WARM/COLD/DISCARD
    refutado     necesita las 8 refutaciones respondidas y que la tesis sobreviva (skill refutar-producto)
    validado     el validador financiero debe aprobar (mínimo 2x sobre coste landed)
    creativo     datos del test de demanda + creativo confirmado por ti (no se inventa un umbral)
    tienda       creativo confirmado
    escalado     el árbol de escalado de métricas reales debe decir ESCALAR (ROAS, CPA, caja)
Toda escritura lleva correlation_id y deja un evento en producto_eventos (trazabilidad).
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services import business_metrics

ESTADOS = ["candidato", "clasificado", "refutado", "validado", "creativo", "tienda", "escalado"]
DESCARTADO = "descartado"
TODOS_LOS_ESTADOS = ESTADOS + [DESCARTADO]

# Las 8 refutaciones de .claude/commands/refutar-producto.md
REFUTACIONES = {
    1: "El margen no aguanta los costes reales (landed + fees 4 % + cancelaciones 10,1 % + CPA realista)",
    2: "La demanda es estacional y vamos tarde (el pico ya pasó)",
    3: "Está más saturado de lo que parece (más de 5 anunciantes activos con el mismo ángulo)",
    4: "El producto genera devoluciones (categoría propensa, por encima del 10,1 %)",
    5: "El envío mata la conversión (plazo del proveedor vs. lo que espera el mercado)",
    6: "Hay una barrera legal o aduanera (certificación que no tenemos, baterías, imitaciones)",
    7: "El wow factor no sobrevive al vídeo (no se ve el antes/después en 3 segundos)",
    8: "El competidor gana por algo que no podemos copiar (marca, exclusividad, stock local en 48 h)",
}
_REFUTACIONES_ELIMINATORIAS = (1, 6)

_CAMPOS_EDITABLES = {"nombre", "categoria", "url_proveedor", "origen_video_id", "costo_origen",
                     "costo_envio", "pvp", "notas"}


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _fila(r: sqlite3.Row) -> Dict[str, Any]:
    d = dict(r)
    for k in ("refutaciones", "demanda"):
        try:
            d[k] = json.loads(d.get(k) or "{}")
        except Exception:
            d[k] = {}
    d["creativo_ok"] = bool(d.get("creativo_ok"))
    d["siguiente"] = (ESTADOS[ESTADOS.index(d["estado"]) + 1]
                      if d["estado"] in ESTADOS[:-1] else None)
    return d


# ── reglas puras ─────────────────────────────────────────────────────────────

def clasificar(multiplicador: float) -> str:
    """HOT ≥ 5x · WARM 3–5x · COLD 2–3x · DISCARD < 2x (CLAUDE.md)."""
    if multiplicador >= 5:
        return "HOT"
    if multiplicador >= 3:
        return "WARM"
    if multiplicador >= 2:
        return "COLD"
    return "DISCARD"


def veredicto_refutacion(respuestas: Dict[Any, Any]) -> Optional[Dict[str, Any]]:
    """Veredicto del skill refutar-producto. None si faltan respuestas."""
    estado: Dict[int, str] = {}
    for k, v in (respuestas or {}).items():
        resultado = (v.get("resultado") if isinstance(v, dict) else v) or ""
        if str(resultado) in ("pasa", "refutada"):
            estado[int(k)] = str(resultado)
    if set(estado) != set(REFUTACIONES):
        return None
    refutadas = sorted(n for n, r in estado.items() if r == "refutada")
    eliminatorias = [n for n in refutadas if n in _REFUTACIONES_ELIMINATORIAS]
    if eliminatorias:
        return {"accion": "descartar", "refutadas": refutadas,
                "texto": f"Refutación eliminatoria ({', '.join(map(str, eliminatorias))}): descartar sin más análisis."}
    if len(refutadas) >= 3:
        return {"accion": "descartar", "refutadas": refutadas,
                "texto": f"{len(refutadas)} refutaciones: descartar y buscar otro producto."}
    if refutadas:
        return {"accion": "invertir_test", "refutadas": refutadas,
                "texto": "Invertir solo con el presupuesto test de 15 €/día y vigilar justo "
                         f"esas debilidades: {', '.join(REFUTACIONES[n].split(' (')[0] for n in refutadas)}."}
    return {"accion": "invertir", "refutadas": [], "texto": "Ninguna refutación se sostiene: la tesis aguanta."}


# ── lectura ──────────────────────────────────────────────────────────────────

def listar(db_path: str, estado: str = "", buscar: str = "") -> List[Dict[str, Any]]:
    sql, params = "SELECT * FROM productos WHERE 1=1", []
    if estado in TODOS_LOS_ESTADOS:
        sql += " AND estado = ?"
        params.append(estado)
    if buscar.strip():
        sql += " AND (nombre LIKE ? OR categoria LIKE ? OR notas LIKE ?)"
        params += [f"%{buscar.strip()}%"] * 3
    sql += " ORDER BY actualizado_at DESC, id DESC"
    with _db(db_path) as conn:
        return [_fila(r) for r in conn.execute(sql, params)]


def resumen_estados(db_path: str) -> Dict[str, int]:
    with _db(db_path) as conn:
        cuentas = {e: 0 for e in TODOS_LOS_ESTADOS}
        for r in conn.execute("SELECT estado, COUNT(*) n FROM productos GROUP BY estado"):
            cuentas[r["estado"]] = r["n"]
    return cuentas


def obtener(db_path: str, producto_id: int) -> Optional[Dict[str, Any]]:
    with _db(db_path) as conn:
        r = conn.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
        if not r:
            return None
        p = _fila(r)
        p["eventos"] = [dict(e) for e in conn.execute(
            "SELECT * FROM producto_eventos WHERE producto_id = ? ORDER BY id DESC", (producto_id,))]
    p["calculo"] = calculo_financiero(p)
    return p


def calculo_financiero(p: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Multiplicador sobre coste landed, clasificación, margen neto y CPA (si hay datos)."""
    if not (p.get("costo_origen") and p.get("pvp")):
        return None
    landed = p["costo_origen"] + (p.get("costo_envio") or 0)
    mult = p["pvp"] / landed if landed > 0 else 0.0
    cpa = business_metrics.cpa_producto(p["costo_origen"], p.get("costo_envio") or 0, p["pvp"])
    return {"costo_landed": round(landed, 2), "multiplicador": round(mult, 2),
            "clasificacion": clasificar(mult), "margen_neto_unidad": cpa["cpa_max"], **cpa}


# ── escritura ────────────────────────────────────────────────────────────────

def _evento(conn: sqlite3.Connection, pid: int, antes: Optional[str], despues: Optional[str],
            nota: str, cid: str) -> None:
    conn.execute(
        "INSERT INTO producto_eventos (producto_id, estado_anterior, estado_nuevo, nota, correlation_id, fecha) "
        "VALUES (?,?,?,?,?,?)", (pid, antes, despues, nota[:500], cid, _ahora()))


def _limpiar(datos: Dict[str, Any]) -> Dict[str, Any]:
    limpio: Dict[str, Any] = {}
    for k, v in datos.items():
        if k not in _CAMPOS_EDITABLES or v is None:
            continue
        if k in ("costo_origen", "costo_envio", "pvp"):
            try:
                n = float(v)
            except (TypeError, ValueError):
                raise ValueError(f"{k.replace('_', ' ').capitalize()} debe ser un número.")
            if n < 0:
                raise ValueError(f"{k.replace('_', ' ').capitalize()} no puede ser negativo.")
            limpio[k] = n
        else:
            limpio[k] = str(v).strip()[:2000]
    return limpio


def crear(db_path: str, datos: Dict[str, Any]) -> Dict[str, Any]:
    limpio = _limpiar(datos)
    if not limpio.get("nombre"):
        raise ValueError("El producto necesita un nombre.")
    cid = str(uuid.uuid4())
    campos = list(limpio) + ["estado", "correlation_id", "creado_at", "actualizado_at"]
    valores = list(limpio.values()) + ["candidato", cid, _ahora(), _ahora()]
    with _db(db_path) as conn:
        cur = conn.execute(f"INSERT INTO productos ({', '.join(campos)}) VALUES ({', '.join('?' * len(campos))})", valores)
        pid = cur.lastrowid
        _evento(conn, pid, None, "candidato", "Producto creado", cid)
        conn.commit()
    return obtener(db_path, pid)


def actualizar(db_path: str, producto_id: int, datos: Dict[str, Any]) -> Dict[str, Any]:
    limpio = _limpiar(datos)
    if "nombre" in limpio and not limpio["nombre"]:
        raise ValueError("El nombre no puede estar vacío.")
    cid = str(uuid.uuid4())
    with _db(db_path) as conn:
        if not conn.execute("SELECT 1 FROM productos WHERE id = ?", (producto_id,)).fetchone():
            raise KeyError("Producto no encontrado")
        if limpio:
            sets = ", ".join(f"{k} = ?" for k in limpio) + ", actualizado_at = ?, correlation_id = ?"
            conn.execute(f"UPDATE productos SET {sets} WHERE id = ?",
                         list(limpio.values()) + [_ahora(), cid, producto_id])
            _evento(conn, producto_id, None, None, "Datos actualizados: " + ", ".join(limpio), cid)
        conn.commit()
    return obtener(db_path, producto_id)


def guardar_refutaciones(db_path: str, producto_id: int, respuestas: Dict[Any, Any]) -> Dict[str, Any]:
    limpio: Dict[str, Dict[str, str]] = {}
    for k, v in (respuestas or {}).items():
        try:
            n = int(k)
        except (TypeError, ValueError):
            continue
        if n not in REFUTACIONES or not isinstance(v, dict):
            continue
        if v.get("resultado") in ("pasa", "refutada"):
            limpio[str(n)] = {"resultado": v["resultado"], "dato": str(v.get("dato") or "")[:500]}
    cid = str(uuid.uuid4())
    with _db(db_path) as conn:
        if not conn.execute("SELECT 1 FROM productos WHERE id = ?", (producto_id,)).fetchone():
            raise KeyError("Producto no encontrado")
        ver = veredicto_refutacion(limpio)
        conn.execute("UPDATE productos SET refutaciones = ?, veredicto_refutacion = ?, "
                     "actualizado_at = ?, correlation_id = ? WHERE id = ?",
                     (json.dumps(limpio, ensure_ascii=False), ver["texto"] if ver else None,
                      _ahora(), cid, producto_id))
        _evento(conn, producto_id, None, None, f"Refutaciones guardadas ({len(limpio)}/8)", cid)
        conn.commit()
    return obtener(db_path, producto_id)


def guardar_demanda(db_path: str, producto_id: int, demanda: Dict[str, Any], creativo_ok: Optional[bool]) -> Dict[str, Any]:
    """Resultados del fake door (visitantes, clics en comprar, emails) y confirmación del creativo."""
    datos: Dict[str, Any] = {}
    for k in ("visitantes", "clics_comprar", "emails", "dias_test"):
        v = (demanda or {}).get(k)
        if v not in (None, ""):
            try:
                datos[k] = int(float(v))
            except (TypeError, ValueError):
                raise ValueError(f"{k} debe ser un número.")
            if datos[k] < 0:
                raise ValueError(f"{k} no puede ser negativo.")
    if (demanda or {}).get("notas"):
        datos["notas"] = str(demanda["notas"])[:500]
    cid = str(uuid.uuid4())
    with _db(db_path) as conn:
        if not conn.execute("SELECT 1 FROM productos WHERE id = ?", (producto_id,)).fetchone():
            raise KeyError("Producto no encontrado")
        sets, vals = ["demanda = ?"], [json.dumps(datos, ensure_ascii=False)]
        if creativo_ok is not None:
            sets.append("creativo_ok = ?")
            vals.append(int(bool(creativo_ok)))
        conn.execute(f"UPDATE productos SET {', '.join(sets)}, actualizado_at = ?, correlation_id = ? WHERE id = ?",
                     vals + [_ahora(), cid, producto_id])
        _evento(conn, producto_id, None, None,
                "Demanda/creativo actualizados" + (" · creativo confirmado" if creativo_ok else ""), cid)
        conn.commit()
    return obtener(db_path, producto_id)


def borrar(db_path: str, producto_id: int) -> bool:
    with _db(db_path) as conn:
        n = conn.execute("DELETE FROM productos WHERE id = ?", (producto_id,)).rowcount
        conn.commit()
    return n > 0


def mover(db_path: str, producto_id: int, nuevo: str, nota: str = "") -> Dict[str, Any]:
    """Cambia de estado respetando el orden y las condiciones de cada paso.

    Raises: KeyError (no existe), ValueError (movimiento no permitido; el mensaje explica por qué)."""
    if nuevo not in TODOS_LOS_ESTADOS:
        raise ValueError("Estado desconocido.")
    p = obtener(db_path, producto_id)
    if not p:
        raise KeyError("Producto no encontrado")
    actual = p["estado"]
    cid = str(uuid.uuid4())
    destino, nota_final = nuevo, nota

    if nuevo == DESCARTADO:
        pass
    elif actual == DESCARTADO:
        if nuevo != "candidato":
            raise ValueError("Un producto descartado solo se puede reabrir como candidato.")
    else:
        i = ESTADOS.index(actual)
        if nuevo not in ESTADOS or ESTADOS.index(nuevo) != i + 1:
            esperado = ESTADOS[i + 1] if i + 1 < len(ESTADOS) else None
            raise ValueError("No se puede saltar pasos: " +
                             (f"desde «{actual}» el siguiente es «{esperado}»." if esperado else f"«{actual}» es el último paso."))

        calc = p["calculo"]
        if nuevo == "clasificado":
            if not calc:
                raise ValueError("Faltan datos para clasificar: introduce coste de origen y PVP (y el envío).")
            if p["costo_envio"] in (None, 0):
                nota_final = (nota + " · " if nota else "") + "Aviso: envío sin informar; el multiplicador puede estar inflado."
            if calc["clasificacion"] == "DISCARD":
                destino = DESCARTADO
                nota_final = f"Multiplicador {calc['multiplicador']}x sobre coste landed: por debajo del mínimo 2x (DISCARD)."
        elif nuevo == "refutado":
            ver = veredicto_refutacion(p["refutaciones"])
            if ver is None:
                raise ValueError("Responde las 8 refutaciones antes de continuar.")
            if ver["accion"] == "descartar":
                destino, nota_final = DESCARTADO, ver["texto"]
            else:
                nota_final = ver["texto"]
        elif nuevo == "validado":
            if not calc:
                raise ValueError("Faltan coste de origen y PVP.")
            from app.services.financial_validator import FinancialValidator
            from app.database.connection import DatabaseConnection
            v = FinancialValidator(db_manager=DatabaseConnection(db_path)).validar_producto(
                p["nombre"], p["costo_origen"], 0.0, p["pvp"], costo_envio=p.get("costo_envio") or 0.0)
            if not v["validado"]:
                raise ValueError("El validador financiero rechaza el producto: " + v["nota_auditoria"])
            nota_final = (nota + " · " if nota else "") + v["nota_auditoria"][:300]
        elif nuevo == "creativo":
            d = p["demanda"]
            if not d or not d.get("visitantes"):
                raise ValueError("Registra los resultados del test de demanda (visitantes, clics en comprar, emails).")
            if not p["creativo_ok"]:
                raise ValueError("Confirma que el creativo funciona (casilla «El creativo funciona»).")
        elif nuevo == "tienda":
            if not p["creativo_ok"]:
                raise ValueError("Solo se monta la tienda si el creativo funciona.")
        elif nuevo == "escalado":
            dec = business_metrics.evaluar_escalado(db_path, p)
            if dec["decision"] != "ESCALAR":
                raise ValueError(f"Las métricas no dicen ESCALAR ({dec['decision']}): {dec['accion']}")
            nota_final = (nota + " · " if nota else "") + dec["accion"]

    with _db(db_path) as conn:
        sets = ["estado = ?", "actualizado_at = ?", "correlation_id = ?"]
        vals: List[Any] = [destino, _ahora(), cid]
        if destino == "clasificado" or (nuevo == "clasificado" and p["calculo"]):
            sets += ["clasificacion = ?", "multiplicador = ?", "margen_neto_unidad = ?"]
            vals += [p["calculo"]["clasificacion"], p["calculo"]["multiplicador"], p["calculo"]["margen_neto_unidad"]]
        elif nuevo == "clasificado" and destino == DESCARTADO and p["calculo"]:
            sets += ["clasificacion = ?", "multiplicador = ?"]
            vals += [p["calculo"]["clasificacion"], p["calculo"]["multiplicador"]]
        conn.execute(f"UPDATE productos SET {', '.join(sets)} WHERE id = ?", vals + [producto_id])
        _evento(conn, producto_id, actual, destino, nota_final, cid)
        conn.commit()
    resultado = obtener(db_path, producto_id)
    resultado["auto_descartado"] = destino == DESCARTADO and nuevo != DESCARTADO
    return resultado
