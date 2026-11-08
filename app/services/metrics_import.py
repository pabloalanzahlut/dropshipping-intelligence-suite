"""
metrics_import — importa el CSV de Meta Ads Manager o de Shopify a las métricas diarias.

Por qué dos perfiles: el ROAS que cuenta es el REAL (CLAUDE.md: «medido real, no el que declara
Meta»). Por eso:
  · CSV de Meta   → gasto en ads (+ visitas a la página de destino). Sus «compras» y «valor de
                    conversión» son cifras declaradas por Meta: solo se guardan si lo pides.
  · CSV de Shopify → ingresos y pedidos reales (+ sesiones).
Cada perfil escribe su propia fila (plataforma `meta` / `shopify`) y el resumen las suma, así que
importar los dos da gasto + ingresos reales del mismo día sin pisarse.

Reglas de seguridad de datos:
  · Reimportar el mismo archivo no duplica nada (misma clave fecha+producto+plataforma).
  · Al actualizar NO se tocan los campos que se teclean a mano (coste pagado, devoluciones,
    presupuesto, notas).
  · Previsualizar antes de escribir, y avisa si los ingresos/gasto se sumarían dos veces.
  · Sin datos → no se inventa: las columnas que no vengan quedan sin tocar.
"""
from __future__ import annotations

import csv
import io
import re
import sqlite3
import unicodedata
import uuid
from contextlib import closing
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

MAX_BYTES = 5 * 1024 * 1024
MAX_FILAS = 100_000

_META = {
    "fecha": ["dia", "day", "fecha", "date"],
    "inicio": ["inicio del informe", "reporting starts"],
    "fin": ["fin del informe", "reporting ends"],
    "campana": ["nombre de la campana", "campaign name", "campana", "campaign"],
    "gasto": ["importe gastado", "amount spent", "gasto", "spend"],
    "compras": ["compras", "purchases", "compras en el sitio web", "website purchases"],
    "valor": ["valor de conversion de compras", "valor de conversion de las compras", "valor de conversion de compra",
              "purchases conversion value", "purchase conversion value", "website purchases conversion value",
              "valor de conversion de compras en el sitio web"],
    "visitantes": ["visitas a la pagina de destino", "landing page views", "website landing page views"],
}
_SHOPIFY = {
    "fecha": ["dia", "day", "fecha", "date"],
    "pedidos": ["pedidos", "orders"],
    "ventas_totales": ["ventas totales", "total sales"],
    "ventas_netas": ["ventas netas", "net sales"],
    "ventas_brutas": ["ventas brutas", "gross sales"],
    "visitantes": ["sesiones", "sessions", "visitantes", "visitors"],
}
_PRIORIDAD_VENTAS = ["ventas_totales", "ventas_netas", "ventas_brutas"]


# ── lectura del archivo ──────────────────────────────────────────────────────

def _decodificar(datos: bytes) -> str:
    if datos.startswith((b"\xff\xfe", b"\xfe\xff")):
        return datos.decode("utf-16")
    for codificacion in ("utf-8-sig", "cp1252"):
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return datos.decode("latin-1")


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"\([^)]*\)", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _moneda(cabecera: str) -> Optional[str]:
    m = re.search(r"\(([A-Za-z]{3})\)", cabecera or "")
    return m.group(1).upper() if m else None


def _delimitador(texto: str) -> str:
    primera = next((l for l in texto.splitlines() if l.strip()), "")
    cuentas = {d: primera.count(d) for d in (",", ";", "\t")}
    return max(cuentas, key=cuentas.get) if any(cuentas.values()) else ","


def _numero(valor: Any, coma_decimal: bool) -> Optional[float]:
    """«1.234,56», «1,234.56», «12.5», «€ 12,50», «-» → número o None."""
    s = re.sub(r"[^\d,.\-]", "", str(valor or "").replace(" ", " "))
    if s in ("", "-", ".", ","):
        return None
    if "," in s and "." in s:                       # el último separador es el decimal
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        s = s.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "," in s:
        if coma_decimal or not re.fullmatch(r"-?\d{1,3}(,\d{3})+", s):
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "." in s and coma_decimal and re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")                      # «1.234» con delimitador «;» = mil doscientos treinta y cuatro
    try:
        return float(s)
    except ValueError:
        return None


def _fecha(valor: Any) -> Optional[Tuple[str, bool]]:
    """(AAAA-MM-DD, ambigua) o None. Con barras se asume DD/MM/AAAA (formato español)."""
    s = str(valor or "").strip()[:10]
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        a, mes, d, amb = int(m[1]), int(m[2]), int(m[3]), False
    else:
        m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", s)
        if not m:
            return None
        d, mes, a = int(m[1]), int(m[2]), int(m[3])
        amb = d <= 12 and mes <= 12 and d != mes
    try:
        return date(a, mes, d).isoformat(), amb
    except ValueError:
        return None


def _indice(cabeceras: List[str], alias: List[str]) -> Optional[int]:
    for a in alias:
        if a in cabeceras:
            return cabeceras.index(a)
    return None


def _localizar_cabecera(filas: List[List[str]]) -> int:
    """Primera fila (entre las 10 primeras) que reconoce columnas de Meta o de Shopify."""
    claves = set(sum(_META.values(), [])) | set(sum(_SHOPIFY.values(), []))
    for i, f in enumerate(filas[:10]):
        if sum(1 for c in f if _norm(c) in claves) >= 2:
            return i
    raise ValueError("No reconozco las columnas del CSV. Exporta desde Meta Ads Manager (con «Importe gastado» "
                     "y el desglose por día) o desde Shopify Analytics («Ventas por día» con Pedidos y Ventas).")


# ── perfiles ─────────────────────────────────────────────────────────────────

def parsear(contenido: bytes, plataforma: str = "auto", campanas: Optional[List[str]] = None) -> Dict[str, Any]:
    """Lee el CSV y devuelve los días agregados + avisos. No toca la base de datos."""
    if len(contenido) > MAX_BYTES:
        raise ValueError("El archivo pasa de 5 MB: exporta un periodo más corto.")
    texto = _decodificar(contenido)
    delim = _delimitador(texto)
    filas = [f for f in csv.reader(io.StringIO(texto), delimiter=delim) if any(c.strip() for c in f)]
    if len(filas) > MAX_FILAS:
        raise ValueError(f"Demasiadas filas ({len(filas)}); el máximo es {MAX_FILAS}.")
    if not filas:
        raise ValueError("El archivo está vacío.")
    h = _localizar_cabecera(filas)
    cabeceras_orig = filas[h]
    cab = [_norm(c) for c in cabeceras_orig]
    cuerpo = filas[h + 1:]
    coma_decimal = delim == ";"

    i_gasto = _indice(cab, _META["gasto"])
    i_ventas = next((j for j in (_indice(cab, _SHOPIFY[k]) for k in _PRIORIDAD_VENTAS) if j is not None), None)
    if plataforma == "auto":
        plataforma = "meta" if i_gasto is not None else "shopify" if i_ventas is not None else ""
    if plataforma == "meta" and i_gasto is None:
        raise ValueError("Falta la columna «Importe gastado» (Amount spent).")
    if plataforma == "shopify" and i_ventas is None:
        raise ValueError("Falta una columna de ventas («Ventas totales», «Ventas netas» o «Ventas brutas»).")
    if plataforma not in ("meta", "shopify"):
        raise ValueError("No sé si es un CSV de Meta o de Shopify: faltan «Importe gastado» o las columnas de ventas.")

    out = _parsear_meta(cab, cabeceras_orig, cuerpo, coma_decimal, campanas) if plataforma == "meta" \
        else _parsear_shopify(cab, cabeceras_orig, cuerpo, coma_decimal)
    out.update({"plataforma": plataforma, "delimitador": delim, "filas_leidas": len(cuerpo)})
    return out


def _ordenar_dias(por_dia: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"fecha": f, **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in por_dia[f].items()}}
            for f in sorted(por_dia)]


def _parsear_meta(cab, orig, cuerpo, coma_decimal, campanas) -> Dict[str, Any]:
    i = {k: _indice(cab, a) for k, a in _META.items()}
    avisos: List[str] = []
    if i["fecha"] is None and not (i["inicio"] is not None and i["fin"] is not None):
        raise ValueError("El CSV no trae desglose por día. En Ads Manager: Desglose → Tiempo → Día, y vuelve a exportar.")
    por_dia: Dict[str, Dict[str, Any]] = {}
    camp: Dict[str, Dict[str, float]] = {}
    descartadas = rango = futuras = ambiguas = 0
    for f in cuerpo:
        def c(k):
            return f[i[k]] if i[k] is not None and i[k] < len(f) else ""
        if i["fecha"] is not None:
            bruto = c("fecha")
        else:
            bruto = c("inicio") if c("inicio") == c("fin") else ""
            if not bruto and c("inicio"):
                rango += 1
                continue
        fd = _fecha(bruto)
        if fd is None:
            descartadas += 1                    # filas de totales o sin fecha
            continue
        dia, amb = fd
        if dia > date.today().isoformat():
            futuras += 1
            continue
        gasto = _numero(c("gasto"), coma_decimal)
        if gasto is not None and gasto < 0:
            descartadas += 1
            continue
        nombre = c("campana").strip() or "(sin campaña)"
        ficha = camp.setdefault(nombre, {"gasto": 0.0, "filas": 0})
        ficha["gasto"] += gasto or 0.0
        ficha["filas"] += 1
        if campanas is not None and nombre not in campanas:
            continue
        ambiguas += amb
        d = por_dia.setdefault(dia, {"gasto_ads": 0.0, "visitantes": None, "compras_meta": None, "valor_meta": None})
        d["gasto_ads"] += gasto or 0.0
        for destino, clave in (("visitantes", "visitantes"), ("compras_meta", "compras"), ("valor_meta", "valor")):
            n = _numero(c(clave), coma_decimal)
            if n is not None and n >= 0:
                d[destino] = (d[destino] or 0) + n
    if rango:
        avisos.append(f"{rango} filas abarcan un rango de fechas (no son diarias) y se han saltado.")
    if not por_dia:
        raise ValueError("Ninguna fila coincide con las campañas elegidas." if campanas is not None and camp
                         else "No hay ninguna fila diaria válida. Exporta con el desglose por día.")
    if descartadas:
        avisos.append(f"{descartadas} filas sin fecha válida (totales o filas vacías) se han ignorado.")
    if futuras:
        avisos.append(f"{futuras} filas con fecha futura se han ignorado.")
    if ambiguas:
        avisos.append("Hay fechas con barras (DD/MM/AAAA o MM/DD/AAAA): se han leído como DD/MM/AAAA. Revisa el periodo.")
    for d in por_dia.values():
        d["visitantes"] = int(d["visitantes"]) if d["visitantes"] is not None else None
        d["compras_meta"] = int(d["compras_meta"]) if d["compras_meta"] is not None else None
    if i["visitantes"] is None:
        avisos.append("Sin «Visitas a la página de destino»: no se calculará la tasa de conversión (CR) con estos datos.")
    if i["valor"] is None or i["compras"] is None:
        avisos.append("El CSV no trae compras / valor de conversión: no hay cifras declaradas por Meta que importar.")
    dias = _ordenar_dias(por_dia)
    return {
        "dias": dias, "avisos": avisos,
        "moneda": _moneda(orig[i["gasto"]]),
        "columnas": {k: orig[v] for k, v in i.items() if v is not None},
        "campanas": [{"nombre": n, "gasto": round(v["gasto"], 2), "filas": int(v["filas"])}
                     for n, v in sorted(camp.items(), key=lambda kv: -kv[1]["gasto"])],
        "tiene_declarado_meta": i["valor"] is not None and i["compras"] is not None,
        "totales": {"gasto_ads": round(sum(d["gasto_ads"] for d in dias), 2)},
    }


def _parsear_shopify(cab, orig, cuerpo, coma_decimal) -> Dict[str, Any]:
    i = {k: _indice(cab, a) for k, a in _SHOPIFY.items()}
    if i["fecha"] is None:
        raise ValueError("El CSV de Shopify no trae la columna «Día». Exporta «Ventas a lo largo del tiempo» por día.")
    i_ventas = next(i[k] for k in _PRIORIDAD_VENTAS if i[k] is not None)
    clave_ventas = next(k for k in _PRIORIDAD_VENTAS if i[k] is not None)
    por_dia: Dict[str, Dict[str, Any]] = {}
    descartadas = futuras = ambiguas = 0
    for f in cuerpo:
        def c(idx):
            return f[idx] if idx is not None and idx < len(f) else ""
        fd = _fecha(c(i["fecha"]))
        if fd is None:
            descartadas += 1
            continue
        dia, amb = fd
        if dia > date.today().isoformat():
            futuras += 1
            continue
        ingresos = _numero(c(i_ventas), coma_decimal)
        if ingresos is not None and ingresos < 0:
            descartadas += 1
            continue
        ambiguas += amb
        d = por_dia.setdefault(dia, {"ingresos": 0.0, "pedidos": None, "visitantes": None})
        d["ingresos"] += ingresos or 0.0
        for destino, idx in (("pedidos", i["pedidos"]), ("visitantes", i["visitantes"])):
            n = _numero(c(idx), coma_decimal)
            if n is not None and n >= 0:
                d[destino] = (d[destino] or 0) + n
    if not por_dia:
        raise ValueError("No hay ninguna fila diaria válida. Exporta las ventas desglosadas por día.")
    avisos: List[str] = []
    if descartadas:
        avisos.append(f"{descartadas} filas sin fecha válida o con importes negativos se han ignorado.")
    if futuras:
        avisos.append(f"{futuras} filas con fecha futura se han ignorado.")
    if ambiguas:
        avisos.append("Hay fechas con barras: se han leído como DD/MM/AAAA. Revisa el periodo.")
    if i["pedidos"] is None:
        avisos.append("Sin columna «Pedidos»: no se podrá calcular el CPA real con estos datos.")
    nombre_col = orig[i_ventas]
    if clave_ventas != "ventas_netas":
        avisos.append(f"Ingresos tomados de «{nombre_col}»: incluye envío e impuestos si tu tienda los cobra aparte.")
    for d in por_dia.values():
        d["pedidos"] = int(d["pedidos"]) if d["pedidos"] is not None else None
        d["visitantes"] = int(d["visitantes"]) if d["visitantes"] is not None else None
    dias = _ordenar_dias(por_dia)
    return {
        "dias": dias, "avisos": avisos, "moneda": _moneda(nombre_col),
        "columnas": {k: orig[v] for k, v in i.items() if v is not None},
        "ingresos_columna": nombre_col, "campanas": [],
        "tiene_declarado_meta": False,
        "totales": {"ingresos": round(sum(d["ingresos"] for d in dias), 2),
                    "pedidos": sum(d["pedidos"] or 0 for d in dias)},
    }


# ── base de datos ────────────────────────────────────────────────────────────

def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _plan(conn: sqlite3.Connection, parsed: Dict[str, Any], producto_id: Optional[int],
          usar_ingresos_meta: bool, estimar_cogs: bool) -> Dict[str, Any]:
    """Qué se escribiría, día a día, y qué avisos merece (sin escribir nada)."""
    plataforma = parsed["plataforma"]
    producto = None
    if producto_id:
        producto = conn.execute("SELECT id, nombre, costo_origen, costo_envio FROM productos WHERE id = ?",
                                (producto_id,)).fetchone()
        if not producto:
            raise ValueError("Ese producto no existe.")
    avisos = list(parsed["avisos"])
    if plataforma == "shopify" and usar_ingresos_meta:
        usar_ingresos_meta = False
    escribe_ingresos = plataforma == "shopify" or (plataforma == "meta" and usar_ingresos_meta)
    if plataforma == "meta" and usar_ingresos_meta:
        avisos.append("Los ingresos y compras importados son los que DECLARA Meta (atribución propia), no los reales de Shopify.")
    estimar = bool(estimar_cogs)
    coste_unit = None
    if estimar:
        if not producto or producto["costo_origen"] is None:
            avisos.append("No se estima el coste pagado: elige un producto que tenga coste de origen.")
            estimar = False
        else:
            coste_unit = (producto["costo_origen"] or 0) + (producto["costo_envio"] or 0)
    if not estimar:
        avisos.append("El CSV no trae el coste pagado al proveedor: sin él, el margen neto y los días de caja salen "
                      "optimistas. Regístralo a mano o marca «Estimar el coste».")

    fechas = [d["fecha"] for d in parsed["dias"]]
    pid = producto_id or 0
    previas = {r["fecha"]: r for r in conn.execute(
        "SELECT fecha, cogs_pagado FROM metricas_diarias WHERE plataforma = ? AND COALESCE(producto_id, 0) = ? "
        "AND fecha BETWEEN ? AND ?", (plataforma, pid, min(fechas), max(fechas)))}
    otras = list(conn.execute(
        "SELECT fecha, plataforma, SUM(gasto_ads) AS gasto, SUM(ingresos) AS ingresos FROM metricas_diarias "
        "WHERE plataforma != ? AND COALESCE(producto_id, 0) = ? AND fecha BETWEEN ? AND ? GROUP BY fecha, plataforma",
        (plataforma, pid, min(fechas), max(fechas))))
    solapan_ing = sorted({r["fecha"] for r in otras if r["ingresos"] and r["ingresos"] > 0 and r["fecha"] in fechas})
    solapan_gasto = sorted({r["fecha"] for r in otras if r["gasto"] and r["gasto"] > 0 and r["fecha"] in fechas})
    if escribe_ingresos and solapan_ing:
        avisos.append(f"En {len(solapan_ing)} fecha(s) ya hay ingresos registrados en otra plataforma "
                      f"({solapan_ing[0]}…): se SUMARÍAN a estos. Borra esos registros si son los mismos pedidos.")
    if plataforma == "meta" and solapan_gasto:
        avisos.append(f"En {len(solapan_gasto)} fecha(s) ya hay gasto registrado en otra plataforma "
                      f"({solapan_gasto[0]}…): se sumaría al de Meta.")

    filas: List[Dict[str, Any]] = []
    for d in parsed["dias"]:
        fila: Dict[str, Any] = {"fecha": d["fecha"], "estado": "actualiza" if d["fecha"] in previas else "nuevo"}
        if plataforma == "meta":
            fila["gasto_ads"] = d["gasto_ads"]
            if d["visitantes"] is not None:
                fila["visitantes"] = d["visitantes"]
            if usar_ingresos_meta:
                if d["valor_meta"] is not None:
                    fila["ingresos"] = d["valor_meta"]
                if d["compras_meta"] is not None:
                    fila["pedidos"] = d["compras_meta"]
        else:
            fila["ingresos"] = d["ingresos"]
            if d["pedidos"] is not None:
                fila["pedidos"] = d["pedidos"]
            if d["visitantes"] is not None:
                fila["visitantes"] = d["visitantes"]
        if estimar and fila.get("pedidos") is not None:
            previo = previas.get(d["fecha"])
            if previo is None or not (previo["cogs_pagado"] or 0):        # nunca pisa lo tecleado a mano
                fila["cogs_pagado"] = round(fila["pedidos"] * coste_unit, 2)
        filas.append(fila)
    return {"filas": filas, "avisos": avisos, "producto": dict(producto) if producto else None,
            "nuevos": sum(f["estado"] == "nuevo" for f in filas),
            "actualizados": sum(f["estado"] == "actualiza" for f in filas),
            "escribe_ingresos": escribe_ingresos, "cogs_estimado": estimar}


def previsualizar(db_path: str, parsed: Dict[str, Any], producto_id: Optional[int] = None,
                  usar_ingresos_meta: bool = False, estimar_cogs: bool = False) -> Dict[str, Any]:
    with closing(_db(db_path)) as conn:
        p = _plan(conn, parsed, producto_id, usar_ingresos_meta, estimar_cogs)
    return {**{k: parsed[k] for k in ("plataforma", "moneda", "columnas", "campanas", "totales",
                                       "delimitador", "filas_leidas", "tiene_declarado_meta")},
            "ingresos_columna": parsed.get("ingresos_columna"),
            "dias": p["filas"], "avisos": p["avisos"], "nuevos": p["nuevos"], "actualizados": p["actualizados"],
            "producto": p["producto"], "escribe_ingresos": p["escribe_ingresos"], "cogs_estimado": p["cogs_estimado"]}


def aplicar(db_path: str, parsed: Dict[str, Any], producto_id: Optional[int] = None,
            usar_ingresos_meta: bool = False, estimar_cogs: bool = False) -> Dict[str, Any]:
    """Escribe los días en una sola transacción. Solo actualiza las columnas que el CSV aporta."""
    plataforma = parsed["plataforma"]
    cid = str(uuid.uuid4())
    with closing(_db(db_path)) as conn:
        plan = _plan(conn, parsed, producto_id, usar_ingresos_meta, estimar_cogs)
        try:
            for f in plan["filas"]:
                valores = {"gasto_ads": f.get("gasto_ads", 0.0), "ingresos": f.get("ingresos", 0.0),
                           "pedidos": f.get("pedidos", 0), "cogs_pagado": f.get("cogs_pagado", 0.0),
                           "visitantes": f.get("visitantes")}
                actualizar = [c for c in ("gasto_ads", "ingresos", "pedidos", "cogs_pagado", "visitantes") if c in f]
                sets = ", ".join([f"{c}=excluded.{c}" for c in actualizar] + ["correlation_id=excluded.correlation_id"])
                conn.execute(
                    f"""INSERT INTO metricas_diarias
                            (fecha, producto_id, plataforma, gasto_ads, ingresos, pedidos, cogs_pagado,
                             visitantes, notas, correlation_id)
                        VALUES (?,?,?,?,?,?,?,?,?,?)
                        ON CONFLICT(fecha, COALESCE(producto_id, 0), plataforma) DO UPDATE SET {sets}""",
                    (f["fecha"], producto_id or None, plataforma, valores["gasto_ads"], valores["ingresos"],
                     valores["pedidos"], valores["cogs_pagado"], valores["visitantes"],
                     f"Importado de CSV ({plataforma})", cid))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"plataforma": plataforma, "dias": len(plan["filas"]), "nuevos": plan["nuevos"],
            "actualizados": plan["actualizados"], "correlation_id": cid, "avisos": plan["avisos"]}
