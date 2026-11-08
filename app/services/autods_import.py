"""
autods_import — importa las exportaciones de AutoDS (CSV / XLSX) para conocer el coste real.

POR QUÉ UNA IMPORTACIÓN Y NO UNA API
  La API de AutoDS no es de autoservicio: requiere solicitud, aprobación y una tarifa de activación, y
  sus credenciales y documentación solo se entregan después. Hasta que exista esa credencial no hay forma
  honesta de «conectarse» sin inventar endpoints. Lo que sí se puede hacer hoy: exportar Pedidos / Productos
  desde AutoDS y subir el archivo aquí. Cuando haya API, esta capa se sustituye sin tocar el resto.

QUÉ NO SE ASUME
  · Las columnas se reconocen por nombre (ES/EN). Lo que no se reconoce se lista en `sin_mapear`; nada se
    adivina. Si faltan las columnas mínimas, el archivo se rechaza explicando cuáles.
  · Si el coste del export es POR UNIDAD o es el TOTAL de la línea lo decides tú (`coste_por_unidad`); la
    previsualización enseña el resultado para que lo compruebes con un pedido que conozcas.
  · Las fechas con barras se leen como DD/MM/AAAA salvo que indiques `formato_fecha="mdy"`.
  · Reimportar el mismo archivo (o uno solapado) no duplica nada: cada línea tiene una clave estable.

Los importes se guardan tal cual vienen (sin convertir divisas): usa un export en la divisa de tu tienda.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from app.services import metrics_import as _mi

MAX_BYTES = 10 * 1024 * 1024
MAX_FILAS = 100_000

_PEDIDOS: Dict[str, List[str]] = {
    "pedido_tienda": ["numero de pedido de la tienda", "store order number", "store order id", "store order",
                      "order number", "numero de pedido", "numero de orden", "order id", "id de pedido",
                      "id del pedido", "pedido", "orden", "order", "shopify order", "shopify order number",
                      "order name", "nombre del pedido", "id de orden de la tienda"],
    "fecha": ["fecha del pedido", "order date", "fecha de pedido", "fecha", "date", "ordered on", "ordered at",
              "created at", "created", "fecha de creacion", "creado"],
    "titulo": ["titulo", "title", "nombre del producto", "product name", "producto", "product", "articulo",
               "item", "item title", "nombre"],
    "sku": ["sku", "sku del proveedor", "supplier sku", "referencia", "sku del producto", "product sku"],
    "cantidad": ["cantidad", "quantity", "qty", "unidades", "cant"],
    "precio_venta": ["precio de venta", "selling price", "sell price", "sale price", "precio venta", "precio",
                     "price", "total del pedido", "order total", "ingresos", "revenue"],
    "coste_envio": ["costo de envio", "coste de envio", "shipping cost", "gastos de envio", "envio del proveedor",
                    "supplier shipping", "shipping price", "coste envio"],
    "coste_proveedor": ["costo", "coste", "cost", "costo total", "coste total", "total cost", "precio de compra",
                        "buy price", "purchase price", "precio de coste", "costo del proveedor",
                        "coste del proveedor", "supplier cost", "supplier price", "precio del proveedor",
                        "costo del producto", "coste del producto", "cost price", "product cost",
                        "precio de origen", "costo de origen"],
    "estado": ["estado", "status", "estado del pedido", "order status", "estado de la orden",
               "fulfillment status", "estado de cumplimiento"],
    "proveedor": ["proveedor", "supplier", "vendedor", "seller", "fuente", "source", "origen", "supplier name",
                  "nombre del proveedor"],
    "tracking": ["tracking", "numero de seguimiento", "tracking number", "seguimiento", "numero de rastreo",
                 "codigo de seguimiento", "tracking id"],
    "pais": ["pais", "country", "destino", "pais de destino", "shipping country", "pais de envio"],
}
_PRODUCTOS: Dict[str, List[str]] = {
    "titulo": _PEDIDOS["titulo"],
    "sku": _PEDIDOS["sku"],
    "coste": _PEDIDOS["coste_proveedor"],
    "precio_venta": _PEDIDOS["precio_venta"],
    "stock": ["stock", "inventario", "inventory", "cantidad en stock", "existencias", "available"],
    "proveedor": _PEDIDOS["proveedor"],
    "estado": _PEDIDOS["estado"],
}
_ORDEN_PEDIDOS = ["coste_envio", "coste_proveedor", "precio_venta", "pedido_tienda", "fecha", "titulo", "sku",
                  "cantidad", "estado", "proveedor", "tracking", "pais"]
_ORDEN_PRODUCTOS = ["coste", "precio_venta", "titulo", "sku", "stock", "proveedor", "estado"]


# ── lectura ──────────────────────────────────────────────────────────────────

def _filas_xlsx(contenido: bytes) -> List[List[str]]:
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    try:
        hoja = wb.active
        filas = []
        for f in hoja.iter_rows(values_only=True):
            filas.append(["" if c is None else (c.isoformat(sep=" ") if hasattr(c, "isoformat") else str(c))
                          for c in f])
            if len(filas) > MAX_FILAS + 20:
                break
        return filas
    finally:
        wb.close()


def _filas(contenido: bytes, archivo: str):
    if archivo.lower().endswith((".xlsx", ".xlsm")) or contenido[:2] == b"PK":
        try:
            return _filas_xlsx(contenido), "xlsx", False
        except Exception as exc:
            raise ValueError(f"No se pudo leer el Excel: {exc}")
    texto = _mi._decodificar(contenido)
    delim = _mi._delimitador(texto)
    filas = [f for f in csv.reader(io.StringIO(texto), delimiter=delim) if any(c.strip() for c in f)]
    return filas, "csv", delim == ";"


def _asignar(cabeceras: List[str], alias: Dict[str, List[str]], orden: List[str]) -> Dict[str, int]:
    """campo → índice de columna. Cada columna se asigna a un solo campo (por prioridad)."""
    usadas, out = set(), {}
    for campo in orden:
        for a in alias[campo]:
            if a in cabeceras and cabeceras.index(a) not in usadas:
                out[campo] = cabeceras.index(a)
                usadas.add(out[campo])
                break
    return out


def _localizar_cabecera(filas: List[List[str]]) -> int:
    claves = {a for v in list(_PEDIDOS.values()) + list(_PRODUCTOS.values()) for a in v}
    for i, f in enumerate(filas[:10]):
        if sum(1 for c in f if _mi._norm(c) in claves) >= 2:
            return i
    raise ValueError("No reconozco las columnas del archivo. Exporta «Pedidos» o «Productos» desde AutoDS y "
                     "sube el CSV/XLSX tal cual (con su fila de cabeceras).")


def _fecha(valor: Any, formato: str):
    s = str(valor or "").strip()
    if formato == "mdy":
        m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})(.*)", s)
        if m:
            s = f"{m[2]}/{m[1]}/{m[3]}"
    return _mi._fecha(s)


# ── parseo (sin tocar la base de datos) ──────────────────────────────────────

def parsear(contenido: bytes, archivo: str = "", tipo: str = "auto", coste_por_unidad: bool = False,
            formato_fecha: str = "auto") -> Dict[str, Any]:
    if len(contenido) > MAX_BYTES:
        raise ValueError("El archivo pasa de 10 MB: exporta un periodo más corto.")
    if tipo not in ("auto", "pedidos", "productos"):
        raise ValueError("El tipo debe ser «pedidos», «productos» o «auto».")
    filas, formato, coma_decimal = _filas(contenido, archivo)
    if len(filas) > MAX_FILAS:
        raise ValueError(f"Demasiadas filas ({len(filas)}); el máximo es {MAX_FILAS}.")
    if not filas:
        raise ValueError("El archivo está vacío.")
    h = _localizar_cabecera(filas)
    originales = filas[h]
    cab = [_mi._norm(c) for c in originales]
    cuerpo = filas[h + 1:]

    ped = _asignar(cab, _PEDIDOS, _ORDEN_PEDIDOS)
    prod = _asignar(cab, _PRODUCTOS, _ORDEN_PRODUCTOS)
    if tipo == "auto":
        if "fecha" in ped and ("coste_proveedor" in ped or "precio_venta" in ped):
            tipo = "pedidos"
        elif ("titulo" in prod or "sku" in prod) and ("coste" in prod or "precio_venta" in prod):
            tipo = "productos"
        else:
            raise ValueError("No sé si es un export de Pedidos o de Productos. Reconocí: " +
                             (", ".join(originales[i] for i in sorted({*ped.values(), *prod.values()})) or "ninguna columna") +
                             ". Un export de pedidos necesita una columna de fecha y otra de coste o precio.")
    mapa = ped if tipo == "pedidos" else prod
    if tipo == "pedidos":
        faltan = [n for n, c in (("fecha", "fecha"), ("coste del proveedor", "coste_proveedor")) if c not in mapa]
    else:
        faltan = [n for n, c in (("título o SKU", "titulo" if "titulo" in mapa else "sku"),
                                 ("coste", "coste")) if c not in mapa]
    if faltan:
        raise ValueError(f"DATA_GAP: al export de {tipo} le faltan columnas mínimas: {', '.join(faltan)}. "
                         f"Columnas reconocidas: {', '.join(f'{k}←«{originales[v]}»' for k, v in mapa.items()) or 'ninguna'}.")

    def c(f: List[str], campo: str) -> str:
        i = mapa.get(campo)
        return f[i].strip() if i is not None and i < len(f) and f[i] is not None else ""

    def n(f: List[str], campo: str) -> Optional[float]:
        v = _mi._numero(c(f, campo), coma_decimal)
        return v if v is not None and v >= 0 else None

    avisos: List[str] = []
    filas_ok: List[Dict[str, Any]] = []
    descartadas = ambiguas = 0
    vistas: Dict[str, int] = {}
    for f in cuerpo:
        if tipo == "pedidos":
            fd = _fecha(c(f, "fecha"), formato_fecha)
            coste = n(f, "coste_proveedor")
            if fd is None or coste is None and n(f, "precio_venta") is None:
                descartadas += 1
                continue
            ambiguas += fd[1]
            cant = n(f, "cantidad")
            cant = int(cant) if cant and cant >= 1 else 1
            envio = n(f, "coste_envio")
            fila = {
                "fecha": fd[0], "pedido_tienda": c(f, "pedido_tienda").lstrip("#"), "titulo": c(f, "titulo"),
                "sku": c(f, "sku"), "cantidad": cant, "precio_venta": n(f, "precio_venta"),
                "coste_proveedor": (coste * cant if coste_por_unidad and coste is not None else coste),
                "coste_envio": envio, "estado": c(f, "estado"), "proveedor": c(f, "proveedor"),
                "tracking": c(f, "tracking"), "pais": c(f, "pais"),
            }
            base = "|".join([fila["pedido_tienda"] or fila["fecha"], fila["sku"] or fila["titulo"],
                             str(cant) if not fila["pedido_tienda"] else "",
                             fila["tracking"] if not fila["pedido_tienda"] else ""])
        else:
            coste = n(f, "coste")
            if coste is None or not (c(f, "titulo") or c(f, "sku")):
                descartadas += 1
                continue
            stock = n(f, "stock")
            fila = {"titulo": c(f, "titulo"), "sku": c(f, "sku"), "coste": coste, "precio_venta": n(f, "precio_venta"),
                    "stock": int(stock) if stock is not None else None, "proveedor": c(f, "proveedor"),
                    "estado": c(f, "estado")}
            base = "|".join([fila["sku"] or fila["titulo"], fila["proveedor"]])
        orden = vistas[base] = vistas.get(base, 0) + 1
        fila["clave"] = hashlib.sha1(f"{tipo}|{base}|{orden}".encode("utf-8")).hexdigest()
        filas_ok.append(fila)

    if not filas_ok:
        raise ValueError("Ninguna fila tiene los datos mínimos (fecha y coste en pedidos; título/SKU y coste en "
                         "productos). Revisa el archivo.")
    if descartadas:
        avisos.append(f"{descartadas} fila(s) sin los datos mínimos se han ignorado.")
    if ambiguas:
        avisos.append("Hay fechas con barras: se han leído como "
                      + ("MM/DD/AAAA." if formato_fecha == "mdy" else "DD/MM/AAAA.") + " Revisa el periodo.")
    if tipo == "pedidos":
        if "pedido_tienda" not in mapa:
            avisos.append("Sin columna del nº de pedido de la tienda: no se podrá cruzar con Shopify para calcular "
                          "el margen real por pedido.")
        if "cantidad" not in mapa:
            avisos.append("Sin columna de cantidad: cada línea se cuenta como 1 unidad.")
        if "coste_envio" not in mapa:
            avisos.append("Sin columna de coste de envío: el margen no descuenta el envío del proveedor.")
        if coste_por_unidad and "cantidad" not in mapa:
            avisos.append("Indicaste coste por unidad pero no hay columna de cantidad: se toma 1 unidad.")
    reconocidas = set(mapa.values())
    ejemplo = filas_ok[0]
    return {
        "tipo": tipo, "archivo": archivo, "formato": formato, "sha256": hashlib.sha256(contenido).hexdigest(),
        "filas": filas_ok, "filas_leidas": len(cuerpo), "descartadas": descartadas,
        "columnas": {k: originales[v] for k, v in mapa.items()},
        "sin_mapear": [o for i, o in enumerate(originales) if i not in reconocidas and o.strip()],
        "coste_por_unidad": coste_por_unidad, "avisos": avisos, "ejemplo": ejemplo,
        "totales": ({"coste_proveedor": round(sum(r["coste_proveedor"] or 0 for r in filas_ok), 2),
                     "coste_envio": round(sum(r["coste_envio"] or 0 for r in filas_ok), 2),
                     "unidades": sum(r["cantidad"] for r in filas_ok),
                     "desde": min(r["fecha"] for r in filas_ok), "hasta": max(r["fecha"] for r in filas_ok)}
                    if tipo == "pedidos" else {"productos": len(filas_ok)}),
    }


# ── base de datos ────────────────────────────────────────────────────────────

def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _tabla(tipo: str) -> str:
    return "autods_pedidos" if tipo == "pedidos" else "autods_productos"


def previsualizar(db_path: str, parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Qué pasaría al importar: filas nuevas / ya existentes, y lo que se leyó de la primera fila."""
    tabla = _tabla(parsed["tipo"])
    with closing(_db(db_path)) as conn:
        existentes = {r[0] for r in conn.execute(f"SELECT clave FROM {tabla}")}
        ya = conn.execute("SELECT importado_at FROM autods_importaciones WHERE sha256 = ?",
                          (parsed["sha256"],)).fetchone()
    claves = [f["clave"] for f in parsed["filas"]]
    nuevas = sum(1 for k in claves if k not in existentes)
    return {k: parsed[k] for k in ("tipo", "archivo", "formato", "filas_leidas", "descartadas", "columnas",
                                   "sin_mapear", "coste_por_unidad", "avisos", "ejemplo", "totales")} | {
        "filas": len(claves), "nuevas": nuevas, "actualizadas": len(claves) - nuevas,
        "archivo_ya_importado": ya["importado_at"] if ya else None}


def aplicar(db_path: str, parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Escribe en una sola transacción. Reimportar el mismo archivo no cambia nada."""
    tipo, tabla, cid = parsed["tipo"], _tabla(parsed["tipo"]), str(uuid.uuid4())
    with closing(_db(db_path)) as conn:
        if conn.execute("SELECT 1 FROM autods_importaciones WHERE sha256 = ?", (parsed["sha256"],)).fetchone():
            return {"tipo": tipo, "duplicado": True, "filas": len(parsed["filas"]), "nuevas": 0,
                    "mensaje": "Este archivo ya se había importado: no se ha cambiado nada."}
        existentes = {r[0] for r in conn.execute(f"SELECT clave FROM {tabla}")}
        nuevas = sum(1 for f in parsed["filas"] if f["clave"] not in existentes)
        try:
            imp_id = conn.execute(
                "INSERT INTO autods_importaciones (archivo, sha256, tipo, filas, nuevas, mapeo, correlation_id) "
                "VALUES (?,?,?,?,?,?,?)",
                (parsed["archivo"][:200], parsed["sha256"], tipo, len(parsed["filas"]), nuevas,
                 str(parsed["columnas"]), cid)).lastrowid
            if tipo == "pedidos":
                conn.executemany(
                    """INSERT INTO autods_pedidos (clave, importacion_id, pedido_tienda, fecha, titulo, sku, cantidad,
                           precio_venta, coste_proveedor, coste_envio, estado, proveedor, tracking, pais, correlation_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(clave) DO UPDATE SET importacion_id=excluded.importacion_id,
                           precio_venta=excluded.precio_venta, coste_proveedor=excluded.coste_proveedor,
                           coste_envio=excluded.coste_envio, estado=excluded.estado, proveedor=excluded.proveedor,
                           tracking=excluded.tracking, pais=excluded.pais, correlation_id=excluded.correlation_id""",
                    [(f["clave"], imp_id, f["pedido_tienda"], f["fecha"], f["titulo"], f["sku"], f["cantidad"],
                      f["precio_venta"], f["coste_proveedor"], f["coste_envio"], f["estado"], f["proveedor"],
                      f["tracking"], f["pais"], cid) for f in parsed["filas"]])
            else:
                conn.executemany(
                    """INSERT INTO autods_productos (clave, importacion_id, titulo, sku, coste, precio_venta, stock,
                           proveedor, estado, correlation_id) VALUES (?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(clave) DO UPDATE SET importacion_id=excluded.importacion_id, coste=excluded.coste,
                           precio_venta=excluded.precio_venta, stock=excluded.stock, estado=excluded.estado,
                           correlation_id=excluded.correlation_id""",
                    [(f["clave"], imp_id, f["titulo"], f["sku"], f["coste"], f["precio_venta"], f["stock"],
                      f["proveedor"], f["estado"], cid) for f in parsed["filas"]])
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"tipo": tipo, "duplicado": False, "filas": len(parsed["filas"]), "nuevas": nuevas,
            "actualizadas": len(parsed["filas"]) - nuevas, "importacion_id": imp_id, "correlation_id": cid}


# ── estadísticas de AutoDS ───────────────────────────────────────────────────

def resumen(db_path: str, dias: int = 90, hoy: Optional[date] = None) -> Dict[str, Any]:
    """Lo que dicen las exportaciones de AutoDS importadas (pedidos con fecha en el periodo)."""
    hoy = hoy or date.today()
    desde = (hoy - timedelta(days=max(1, dias) - 1)).isoformat()
    with closing(_db(db_path)) as conn:
        filas = [dict(r) for r in conn.execute(
            "SELECT * FROM autods_pedidos WHERE fecha BETWEEN ? AND ?", (desde, hoy.isoformat()))]
        total_filas = conn.execute("SELECT COUNT(*) FROM autods_pedidos").fetchone()[0]
        productos = conn.execute("SELECT COUNT(*) FROM autods_productos").fetchone()[0]
        ultima = conn.execute("SELECT importado_at FROM autods_importaciones ORDER BY id DESC LIMIT 1").fetchone()
    estados: Dict[str, int] = {}
    proveedores: Dict[str, int] = {}
    for f in filas:
        estados[(f["estado"] or "sin estado").lower()] = estados.get((f["estado"] or "sin estado").lower(), 0) + 1
        if f["proveedor"]:
            proveedores[f["proveedor"]] = proveedores.get(f["proveedor"], 0) + 1
    con_coste = [f for f in filas if f["coste_proveedor"] is not None]
    con_envio = [f for f in filas if f["coste_envio"] is not None]
    return {
        "periodo_dias": dias, "pedidos": len(filas), "pedidos_importados_total": total_filas,
        "productos_importados": productos, "ultima_importacion": ultima[0] if ultima else None,
        "unidades": sum(f["cantidad"] for f in filas),
        "coste_proveedor": round(sum(f["coste_proveedor"] for f in con_coste), 2),
        "coste_envio": round(sum(f["coste_envio"] for f in con_envio), 2) if con_envio else None,
        "con_tracking_pct": round(sum(1 for f in filas if f["tracking"]) / len(filas), 4) if filas else None,
        "estados": sorted(({"estado": k, "n": v} for k, v in estados.items()), key=lambda x: -x["n"])[:6],
        "proveedores": sorted(({"proveedor": k, "n": v} for k, v in proveedores.items()), key=lambda x: -x["n"])[:5],
    }
