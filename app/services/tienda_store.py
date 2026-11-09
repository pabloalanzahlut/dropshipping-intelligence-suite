"""
tienda_store — datos reales de la tienda: sincroniza Shopify a SQLite y calcula las estadísticas.

Principios (CLAUDE.md: «NO INVENTAR»):
  · Todo es Python puro y determinista; la IA no calcula nada. El agente solo recibe el resultado.
  · Si un dato no está (coste, gasto en ads, AutoDS…) NO se estima: se anota en `datos_que_faltan`.
  · Las referencias salen de business_metrics (fees 4,0 %, cancelaciones y devoluciones 10,1 %,
    ROAS mínimo 2): este módulo no define umbrales propios.

Qué se sincroniza (Shopify, solo lectura):
  · tienda_pedidos / tienda_lineas — pedidos de los últimos N días, con importes en la divisa de la tienda.
  · tienda_variantes              — catálogo con el coste unitario si la app tiene el scope read_inventory.
  · metricas_diarias (plataforma «shopify») — ingresos y pedidos REALES por día, que es lo que necesitan el
    ROAS real y la caja. No pisa gasto, coste pagado, devoluciones ni notas, y no escribe en un día donde
    otra plataforma ya declara ingresos (evita contarlos dos veces).
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import uuid
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

from app.services import business_metrics as bm
from app.services import product_catalog
from app.services.shopify_client import (SCOPES_NECESARIOS, ShopifyClient, ShopifyError,
                                          estado_credenciales)

logger = logging.getLogger(__name__)

SYNC_LOCK = threading.Lock()
DIAS_SYNC_COMPLETA = 60      # sin el scope read_all_orders Shopify solo entrega los últimos 60 días
DIAS_SYNC_RAPIDA = 14        # la sincronización horaria: repasa reembolsos y cambios recientes
HORAS_OBSOLETO = 24


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _zona(nombre: Optional[str]) -> Any:
    try:
        return ZoneInfo(nombre) if nombre else timezone.utc
    except Exception:
        return timezone.utc


def _fecha_local(iso: str, zona: Any) -> str:
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.astimezone(zona).date().isoformat()


# ── registro de sincronizaciones ─────────────────────────────────────────────

def ultima_sync(db_path: str, fuente: str = "shopify", solo_ok: bool = False) -> Optional[Dict[str, Any]]:
    sql = "SELECT * FROM tienda_sync WHERE fuente = ?" + (" AND estado = 'ok'" if solo_ok else "")
    with closing(_db(db_path)) as conn:
        r = conn.execute(sql + " ORDER BY id DESC LIMIT 1", (fuente,)).fetchone()
    if not r:
        return None
    d = dict(r)
    try:
        d["detalle"] = json.loads(d.get("detalle") or "{}")
    except ValueError:
        d["detalle"] = {"texto": d.get("detalle")}
    return d


def horas_desde(iso: Optional[str]) -> Optional[float]:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - dt).total_seconds() / 3600, 1)


# ── sincronización de Shopify ────────────────────────────────────────────────

def sincronizar_shopify(db_path: str, cliente: ShopifyClient, dias: int = DIAS_SYNC_COMPLETA,
                        progreso: Optional[Callable[[str], None]] = None,
                        escribir_metricas: Optional[bool] = None) -> Dict[str, Any]:
    """Descarga variantes y pedidos de los últimos `dias` días y los guarda en una sola transacción.
    Lanza ShopifyError si Shopify falla (y deja constancia en tienda_sync); no deja datos a medias."""
    dias = max(1, min(int(dias), 3650))
    if escribir_metricas is None:
        escribir_metricas = os.getenv("SHOPIFY_SYNC_METRICAS", "1").strip() not in ("0", "false", "no")
    say = progreso or (lambda m: None)
    if not SYNC_LOCK.acquire(blocking=False):
        raise RuntimeError("Ya hay una sincronización con Shopify en curso.")
    cid = str(uuid.uuid4())
    inicio = _ahora_iso()
    with closing(_db(db_path)) as conn:
        sync_id = conn.execute(
            "INSERT INTO tienda_sync (fuente, iniciado_at, estado, dias, tienda, correlation_id) "
            "VALUES ('shopify', ?, 'en_curso', ?, ?, ?)", (inicio, dias, cliente.tienda, cid)).lastrowid
        conn.commit()
    try:
        say("Conectando con Shopify…")
        tienda = cliente.shop_info()
        zona = _zona(tienda.get("zona_horaria"))
        scopes = cliente.scopes()
        avisos: List[str] = []
        if scopes:
            faltan = [s for s in SCOPES_NECESARIOS if s not in scopes]
            if faltan:
                raise ShopifyError("permiso", "A la app le faltan permisos de lectura: " + ", ".join(faltan) +
                                   ". Añádelos en el Dev Dashboard, publica la versión y reinstala la app.")
            if dias > 60 and "read_all_orders" not in scopes:
                avisos.append("Sin el scope read_all_orders Shopify solo entrega los pedidos de los últimos 60 días.")
        say("Leyendo catálogo y costes…")
        variantes = list(cliente.iter_variantes())
        avisos += list(cliente.avisos)

        hoy_local = datetime.now(timezone.utc).astimezone(zona).date()
        desde_local = datetime.combine(hoy_local - timedelta(days=dias), datetime.min.time(), tzinfo=zona)
        desde_iso = desde_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        say(f"Leyendo pedidos desde {desde_local.date().isoformat()}…")
        pedidos: List[Dict[str, Any]] = []
        for p in cliente.iter_pedidos(desde_iso):
            pedidos.append(p)
            if len(pedidos) % 100 == 0:
                say(f"{len(pedidos)} pedidos leídos…")
        incompletos = sum(1 for p in pedidos if p["lineas_incompletas"])
        if incompletos:
            avisos.append(f"{incompletos} pedido(s) tienen más de 10 líneas: sus importes son correctos, "
                          "pero el detalle por producto está incompleto.")

        say("Guardando…")
        with closing(_db(db_path)) as conn:
            conn.execute("DELETE FROM tienda_variantes")
            conn.executemany(
                "INSERT INTO tienda_variantes (variante_id, producto_id, producto, estado, vendor, sku, titulo, "
                "precio, coste, stock) VALUES (?,?,?,?,?,?,?,?,?,?)",
                [(v["variante_id"], v["producto_id"], v["producto"], v["estado"], v["vendor"], v["sku"],
                  v["titulo"], v["precio"], v["coste"], v["stock"]) for v in variantes])
            for p in pedidos:
                conn.execute(
                    """INSERT INTO tienda_pedidos
                           (pedido_id, nombre, creado_at, fecha, cancelado_at, moneda, total, subtotal, descuentos,
                            envio, impuestos, reembolsado, estado_pago, estado_envio, unidades, pais, canal,
                            lineas_incompletas, actualizado_at, correlation_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,?)
                       ON CONFLICT(pedido_id) DO UPDATE SET
                           nombre=excluded.nombre, creado_at=excluded.creado_at, fecha=excluded.fecha,
                           cancelado_at=excluded.cancelado_at, moneda=excluded.moneda, total=excluded.total,
                           subtotal=excluded.subtotal, descuentos=excluded.descuentos, envio=excluded.envio,
                           impuestos=excluded.impuestos, reembolsado=excluded.reembolsado,
                           estado_pago=excluded.estado_pago, estado_envio=excluded.estado_envio,
                           unidades=excluded.unidades, pais=excluded.pais, canal=excluded.canal,
                           lineas_incompletas=excluded.lineas_incompletas, actualizado_at=CURRENT_TIMESTAMP,
                           correlation_id=excluded.correlation_id""",
                    (p["pedido_id"], p["nombre"], p["creado_at"], _fecha_local(p["creado_at"], zona),
                     p["cancelado_at"], p["moneda"], p["total"], p["subtotal"], p["descuentos"], p["envio"],
                     p["impuestos"], p["reembolsado"], p["estado_pago"], p["estado_envio"], p["unidades"],
                     p["pais"], p["canal"], int(p["lineas_incompletas"]), cid))
                conn.execute("DELETE FROM tienda_lineas WHERE pedido_id = ?", (p["pedido_id"],))
                conn.executemany(
                    "INSERT INTO tienda_lineas (pedido_id, idx, variante_id, sku, titulo, cantidad, precio_unit) "
                    "VALUES (?,?,?,?,?,?,?)",
                    [(p["pedido_id"], l["idx"], l["variante_id"], l["sku"], l["titulo"], l["cantidad"],
                      l["precio_unit"]) for l in p["lineas"]])
            metricas = (_volcar_metricas(conn, desde_local.date().isoformat(), cid)
                        if escribir_metricas else {"escritos": 0, "omitidos": [], "desactivado": True})
            conn.commit()
        if metricas.get("omitidos"):
            avisos.append("No se escribieron los ingresos de " + ", ".join(metricas["omitidos"][:5]) +
                          (" y más" if len(metricas["omitidos"]) > 5 else "") +
                          ": otra plataforma ya declara ingresos ese día (se evita contarlos dos veces).")
        detalle = {"tienda": tienda, "scopes": scopes, "avisos": avisos, "metricas_diarias": metricas,
                   "variantes_con_coste": sum(1 for v in variantes if v["coste"] is not None)}
        _cerrar_sync(db_path, sync_id, "ok", len(pedidos), len(variantes), tienda.get("moneda") or "", detalle)
        say(f"Listo: {len(pedidos)} pedidos y {len(variantes)} variantes.")
        return {"estado": "ok", "pedidos": len(pedidos), "variantes": len(variantes), "dias": dias,
                "tienda": tienda, "avisos": avisos, "metricas_diarias": metricas, "correlation_id": cid}
    except Exception as exc:
        _cerrar_sync(db_path, sync_id, "error", 0, 0, "", {"error": str(exc), "codigo": getattr(exc, "codigo", "")})
        logger.warning("[TIENDA] Sincronización con Shopify falló: %s", exc)
        raise
    finally:
        SYNC_LOCK.release()


def _cerrar_sync(db_path: str, sync_id: int, estado: str, pedidos: int, variantes: int, moneda: str,
                 detalle: Dict[str, Any]) -> None:
    with closing(_db(db_path)) as conn:
        conn.execute("UPDATE tienda_sync SET terminado_at=?, estado=?, pedidos=?, variantes=?, moneda=?, detalle=? "
                     "WHERE id=?", (_ahora_iso(), estado, pedidos, variantes, moneda,
                                    json.dumps(detalle, ensure_ascii=False, default=str), sync_id))
        conn.commit()


def _volcar_metricas(conn: sqlite3.Connection, desde: str, cid: str) -> Dict[str, Any]:
    """Ingresos y pedidos reales por día → metricas_diarias (plataforma «shopify», toda la tienda)."""
    dias = conn.execute(
        """SELECT fecha, COUNT(*) AS pedidos, SUM(total - reembolsado) AS ingresos FROM tienda_pedidos
           WHERE cancelado_at IS NULL AND fecha >= ? GROUP BY fecha""", (desde,)).fetchall()
    escritos, omitidos = 0, []
    for d in dias:
        otra = conn.execute(
            "SELECT 1 FROM metricas_diarias WHERE fecha = ? AND plataforma != 'shopify' AND ingresos > 0 LIMIT 1",
            (d["fecha"],)).fetchone()
        if otra:
            omitidos.append(d["fecha"])
            continue
        conn.execute(
            """INSERT INTO metricas_diarias (fecha, producto_id, plataforma, gasto_ads, ingresos, pedidos,
                                             cogs_pagado, notas, correlation_id)
               VALUES (?, NULL, 'shopify', 0, ?, ?, 0, 'Sincronizado de la API de Shopify', ?)
               ON CONFLICT(fecha, COALESCE(producto_id, 0), plataforma) DO UPDATE SET
                   ingresos=excluded.ingresos, pedidos=excluded.pedidos, correlation_id=excluded.correlation_id""",
            (d["fecha"], round(d["ingresos"] or 0, 2), d["pedidos"], cid))
        escritos += 1
    return {"escritos": escritos, "omitidos": omitidos}


def sync_si_configurada(db_path: str) -> Optional[Dict[str, Any]]:
    """Para el planificador: no hace nada si Shopify no está configurado o ya hay otra en curso."""
    if not estado_credenciales()["configurada"] or SYNC_LOCK.locked():
        return None
    ok = ultima_sync(db_path, solo_ok=True)
    h = horas_desde(ok["terminado_at"]) if ok else None
    dias = DIAS_SYNC_RAPIDA if h is not None and h < 24 * 10 else DIAS_SYNC_COMPLETA
    try:
        return sincronizar_shopify(db_path, ShopifyClient(), dias)
    except (ShopifyError, EnvironmentError, RuntimeError) as exc:
        logger.info("[TIENDA] Sincronización programada omitida: %s", exc)
        return None


def probar_conexion(cliente: Optional[ShopifyClient] = None) -> Dict[str, Any]:
    """Comprueba credenciales, tienda y permisos sin guardar nada. Nunca lanza: devuelve ok/mensaje."""
    est = estado_credenciales()
    if not est["configurada"]:
        return {"ok": False, "codigo": "config", "mensaje": est["aviso"] or
                ("Faltan en .env: " + ", ".join(est["faltan"])), "faltan": est["faltan"]}
    try:
        c = cliente or ShopifyClient()
        tienda = c.shop_info()
        scopes = c.scopes()
    except ShopifyError as e:
        return {"ok": False, "codigo": e.codigo, "mensaje": str(e)}
    except EnvironmentError as e:
        return {"ok": False, "codigo": "config", "mensaje": str(e)}
    faltan = [s for s in SCOPES_NECESARIOS if s not in scopes] if scopes else []
    return {"ok": not faltan, "codigo": "permiso" if faltan else "ok", "tienda": tienda, "scopes": scopes,
            "scopes_faltan": faltan, "modo": est["modo"],
            "mensaje": ("Conexión correcta." if not faltan else "Faltan permisos de lectura: " + ", ".join(faltan))}


# ── estadísticas ─────────────────────────────────────────────────────────────

def _solo_digitos(texto: str) -> str:
    return re.sub(r"\D", "", str(texto or ""))


def _costes_autods(conn: sqlite3.Connection) -> Dict[str, float]:
    """Coste real de proveedor + envío por pedido de la tienda (clave: dígitos del nº de pedido)."""
    out: Dict[str, float] = {}
    for r in conn.execute("SELECT pedido_tienda, coste_proveedor, coste_envio FROM autods_pedidos "
                          "WHERE pedido_tienda != '' AND coste_proveedor IS NOT NULL"):
        k = _solo_digitos(r["pedido_tienda"])
        if k:
            out[k] = out.get(k, 0.0) + (r["coste_proveedor"] or 0) + (r["coste_envio"] or 0)
    return out


def resumen(db_path: str, dias: int = 30, hoy: Optional[date] = None) -> Dict[str, Any]:
    """Estadísticas reales de la tienda en los últimos `dias` días (incluido hoy)."""
    dias = max(1, min(int(dias), 365))
    hoy = hoy or date.today()
    desde = (hoy - timedelta(days=dias - 1)).isoformat()
    hasta = hoy.isoformat()
    ok = ultima_sync(db_path, solo_ok=True)
    falta: List[str] = []

    with closing(_db(db_path)) as conn:
        peds = [dict(r) for r in conn.execute(
            "SELECT * FROM tienda_pedidos WHERE fecha BETWEEN ? AND ? ORDER BY fecha", (desde, hasta))]
        lineas = [dict(r) for r in conn.execute(
            """SELECT l.pedido_id, l.titulo, l.sku, l.cantidad, l.precio_unit, l.variante_id,
                      p.total AS pedido_total, p.reembolsado AS pedido_reembolsado,
                      v.coste AS coste, v.producto_id, v.producto
               FROM tienda_lineas l JOIN tienda_pedidos p ON p.pedido_id = l.pedido_id
               LEFT JOIN tienda_variantes v ON v.variante_id = l.variante_id
               WHERE p.fecha BETWEEN ? AND ? AND p.cancelado_at IS NULL""", (desde, hasta))]
        activos = {r["producto_id"] for r in conn.execute(
            "SELECT DISTINCT producto_id FROM tienda_variantes WHERE estado = 'active'")}
        cat = [dict(r) for r in conn.execute(
            """SELECT producto_id, MIN(producto) AS producto, MIN(precio) AS pvp, AVG(coste) AS coste,
                      SUM(COALESCE(stock, 0)) AS stock, COUNT(coste) AS con_coste, COUNT(*) AS variantes
               FROM tienda_variantes WHERE estado = 'active' GROUP BY producto_id ORDER BY producto""")]
        gasto = conn.execute(
            "SELECT COALESCE(SUM(gasto_ads), 0) FROM metricas_diarias WHERE fecha BETWEEN ? AND ? "
            "AND plataforma != 'shopify'", (desde, hasta)).fetchone()[0]
        costes_autods = _costes_autods(conn)
        autods_filas = conn.execute("SELECT COUNT(*) FROM autods_pedidos").fetchone()[0]

    validos = [p for p in peds if not p["cancelado_at"]]
    cancelados = [p for p in peds if p["cancelado_at"]]
    bruto = sum(p["total"] for p in validos)
    reembolsado = sum(p["reembolsado"] for p in validos)
    neto = bruto - reembolsado
    impuestos = sum(p["impuestos"] for p in validos)
    valor_cancelado = sum(p["total"] for p in cancelados)
    facturado = bruto + valor_cancelado
    perdida = (valor_cancelado + reembolsado) / facturado if facturado > 0 else None
    moneda = (ok or {}).get("moneda") or next((p["moneda"] for p in peds if p["moneda"]), "")

    # Por producto (coste de Shopify: unitCost de la variante, el ACTUAL, no el vigente el día de la venta)
    prods: Dict[str, Dict[str, Any]] = {}
    ingreso_lineas = ingreso_con_coste = 0.0
    for l in lineas:
        # El reembolso del pedido se reparte a prorrata entre sus líneas (Shopify no lo da por línea aquí)
        quedan = max(0.0, 1 - l["pedido_reembolsado"] / l["pedido_total"]) if l["pedido_total"] > 0 else 1.0
        ing = l["precio_unit"] * l["cantidad"] * quedan
        clave = l["producto_id"] or l["titulo"]
        d = prods.setdefault(clave, {"producto": l["producto"] or l["titulo"], "unidades": 0, "ingresos": 0.0,
                                     "ingresos_con_coste": 0.0, "coste": 0.0})
        d["unidades"] += l["cantidad"]
        d["ingresos"] += ing
        ingreso_lineas += ing
        if l["coste"] is not None:
            d["coste"] += l["coste"] * l["cantidad"]
            d["ingresos_con_coste"] += ing
            ingreso_con_coste += ing
    top = []
    for d in sorted(prods.values(), key=lambda x: x["ingresos"], reverse=True)[:5]:
        top.append({"producto": d["producto"], "unidades": d["unidades"], "ingresos": round(d["ingresos"], 2),
                    "margen_pct": (round((d["ingresos_con_coste"] - d["coste"]) / d["ingresos_con_coste"], 4)
                                   if d["ingresos_con_coste"] > 0 else None),
                    "cobertura_coste": round(d["ingresos_con_coste"] / d["ingresos"], 4) if d["ingresos"] else None})
    vendidos = {k for k in prods if k in activos}
    cobertura_shopify = round(ingreso_con_coste / ingreso_lineas, 4) if ingreso_lineas > 0 else None

    # Margen real por pedido: coste de AutoDS si lo hay; si no, solo si TODAS sus líneas tienen coste en Shopify
    por_pedido: Dict[str, List[Dict[str, Any]]] = {}
    for l in lineas:
        por_pedido.setdefault(l["pedido_id"], []).append(l)
    base = coste_total = 0.0
    conocidos = de_autods = 0
    for p in validos:
        coste = costes_autods.get(_solo_digitos(p["nombre"]))
        origen = "autods"
        if coste is None:
            ls = por_pedido.get(p["pedido_id"], [])
            if ls and not p["lineas_incompletas"] and all(l["coste"] is not None for l in ls):
                coste, origen = sum(l["coste"] * l["cantidad"] for l in ls), "shopify"
        if coste is None:
            continue
        conocidos += 1
        de_autods += origen == "autods"
        base += p["total"] - p["impuestos"] - p["reembolsado"]
        coste_total += coste
    fees = base * bm.FEES_PCT
    margen = None
    if conocidos:
        m = base - coste_total - fees
        margen = {"pedidos_con_coste": conocidos, "de_autods": de_autods, "de_shopify": conocidos - de_autods,
                  "ingresos_sin_impuestos": round(base, 2), "coste_producto_y_envio": round(coste_total, 2),
                  "fees_estimados": round(fees, 2), "margen": round(m, 2),
                  "margen_pct": round(m / base, 4) if base > 0 else None}
    cobertura_pedidos = round(conocidos / len(validos), 4) if validos else None

    # Economía del catálogo con el coste que AutoDS escribe en Shopify («coste por artículo»). El multiplicador de
    # las reglas se mide sobre coste LANDED (producto + envío): aquí falta el envío, así que es un techo.
    catalogo = []
    for c in cat:
        mult = round(c["pvp"] / c["coste"], 2) if c["coste"] and c["coste"] > 0 and c["pvp"] else None
        catalogo.append({"producto": c["producto"], "pvp": round(c["pvp"] or 0, 2),
                         "coste": round(c["coste"], 2) if c["coste"] else None, "multiplicador": mult,
                         "clasificacion": product_catalog.clasificar(mult) if mult is not None else None,
                         "stock": c["stock"], "variantes_sin_coste": c["variantes"] - c["con_coste"]})

    roas = round(neto / gasto, 2) if gasto > 0 and neto > 0 else None
    beneficio_tras_ads = (round(margen["margen"] - gasto, 2)
                          if margen and cobertura_pedidos is not None and cobertura_pedidos >= 0.95 else None)

    # Serie diaria y países
    por_dia: Dict[str, Dict[str, float]] = {}
    for p in validos:
        d = por_dia.setdefault(p["fecha"], {"pedidos": 0, "ingresos": 0.0})
        d["pedidos"] += 1
        d["ingresos"] += p["total"] - p["reembolsado"]
    serie = []
    for i in range(dias):
        f = (hoy - timedelta(days=dias - 1 - i)).isoformat()
        d = por_dia.get(f, {"pedidos": 0, "ingresos": 0.0})
        serie.append({"fecha": f, "pedidos": d["pedidos"], "ingresos": round(d["ingresos"], 2)})
    paises: Dict[str, int] = {}
    for p in validos:
        if p["pais"]:
            paises[p["pais"]] = paises.get(p["pais"], 0) + 1

    # Qué falta (nunca se estima en silencio)
    if not ok:
        falta.append("Shopify todavía no se ha sincronizado.")
    else:
        h = horas_desde(ok["terminado_at"])
        if h is not None and h > HORAS_OBSOLETO:
            falta.append(f"La última sincronización de Shopify es de hace {h:g} h.")
    if ok and not peds:
        falta.append("No hay pedidos en el periodo.")
    if validos and (cobertura_pedidos or 0) < 1:
        falta.append(f"Se conoce el coste real del {round((cobertura_pedidos or 0) * 100)} % de los pedidos: "
                     "añade el coste por artículo en Shopify o importa el export de AutoDS.")
    sin_coste = [c["producto"] for c in catalogo if c["coste"] is None]
    if sin_coste:
        falta.append(f"{len(sin_coste)} producto(s) activo(s) sin coste por artículo en Shopify: no se puede "
                     "calcular su multiplicador.")
    if margen and margen["de_shopify"]:
        falta.append(f"El coste de {margen['de_shopify']} pedido(s) sale del «coste por artículo» de Shopify (lo escribe "
                     "AutoDS): puede no incluir el envío del proveedor y AutoDS lo guarda en la divisa del proveedor (USD).")
    if validos and gasto <= 0:
        falta.append("No hay gasto en ads registrado en el periodo: sin él no hay ROAS real.")
    if not autods_filas:
        falta.append("AutoDS sin importar: no se conoce el coste de proveedor ni los envíos reales.")

    return {
        "periodo_dias": dias, "desde": desde, "hasta": hasta, "moneda": moneda,
        "sincronizado_at": ok["terminado_at"] if ok else None,
        "horas_desde_sync": horas_desde(ok["terminado_at"]) if ok else None,
        "pedidos": len(validos), "cancelados": len(cancelados), "unidades": sum(p["unidades"] for p in validos),
        "ingresos_brutos": round(bruto, 2), "reembolsado": round(reembolsado, 2), "ingresos_netos": round(neto, 2),
        "impuestos": round(impuestos, 2),
        "ticket_medio": round(neto / len(validos), 2) if validos else None,
        "fees_estimados": round(bruto * bm.FEES_PCT, 2),
        "cancelaciones_y_devoluciones": {
            "valor_cancelado": round(valor_cancelado, 2), "valor_reembolsado": round(reembolsado, 2),
            "pct_real": round(perdida, 4) if perdida is not None else None, "pct_referencia": bm.CANCELACIONES_PCT,
            "estado": (None if perdida is None else "POR_ENCIMA" if perdida > bm.CANCELACIONES_PCT else "DENTRO"),
        },
        "gasto_ads": round(gasto, 2), "roas_real": roas, "roas_estado": bm.estado_roas(roas),
        "margen_real": margen, "cobertura_coste_pedidos": cobertura_pedidos, "cobertura_coste_shopify": cobertura_shopify,
        "beneficio_tras_ads": beneficio_tras_ads,
        "top_productos": top, "productos_activos": len(activos), "activos_sin_ventas": len(activos - vendidos),
        "catalogo": catalogo,
        "paises": sorted(({"pais": k, "pedidos": v} for k, v in paises.items()), key=lambda x: -x["pedidos"])[:3],
        "serie": serie, "datos_que_faltan": falta,
    }


def estado(db_path: str) -> Dict[str, Any]:
    """Conexiones de un vistazo (para la pantalla Tienda). Nunca incluye secretos."""
    cred = estado_credenciales()
    ok, ultima = ultima_sync(db_path, solo_ok=True), ultima_sync(db_path)
    with closing(_db(db_path)) as conn:
        imp = [dict(r) for r in conn.execute(
            "SELECT id, archivo, tipo, filas, nuevas, importado_at FROM autods_importaciones ORDER BY id DESC LIMIT 5")]
        n_ped = conn.execute("SELECT COUNT(*) FROM autods_pedidos").fetchone()[0]
        n_prod = conn.execute("SELECT COUNT(*) FROM autods_productos").fetchone()[0]
        n_shop = conn.execute("SELECT COUNT(*) FROM tienda_pedidos").fetchone()[0]
    return {
        "shopify": {**cred, "pedidos_guardados": n_shop, "ultima_ok": ok, "ultima": ultima,
                    "sincronizando": SYNC_LOCK.locked(),
                    "obsoleta": bool(ok) and (horas_desde(ok["terminado_at"]) or 0) > HORAS_OBSOLETO},
        "autods": {"modo": "importacion", "pedidos": n_ped, "productos": n_prod, "importaciones": imp,
                   "api_oficial": "Requiere aprobación y pago de activación en AutoDS; sin credenciales no hay "
                                  "conexión directa. Mientras tanto se importan sus exportaciones (CSV/XLSX)."},
    }
