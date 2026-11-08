"""
business_metrics — los números del negocio: ROAS real, CPA, resultado, caja y escalado.

Reglas tomadas LITERALMENTE de los procedimientos del repo (no se inventa ningún umbral):
  - ai_workspace/skills/monitorear_flujo_caja/procedimiento.md  (caja, días de caja, ROAS)
  - ai_workspace/skills/escalar_campana/procedimiento.md        (árbol de escalado)
  - ai_workspace/skills/validar_financiero/procedimiento.md     (CPA máximo y objetivo)
  - CLAUDE.md: fees Shopify+divisa 4,0 % y cancelaciones/devoluciones 10,1 % de la facturación.

Todo es Python puro y determinista. Si falta un dato, se dice (DATA_GAP) en vez de suponerlo.
Los importes están en la divisa en la que los registres (la misma para todo).
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

FEES_PCT = 0.04              # Shopify + divisa (P&L real de Adrián Sáenz)
CANCELACIONES_PCT = 0.101    # cancelaciones y devoluciones
CPA_OBJETIVO_FACTOR = 0.70   # CPA objetivo = CPA máximo × 0.70 (reserva 30 % operativo)


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _num(valor: Any, nombre: str, obligatorio: bool = False, entero: bool = False) -> Optional[float]:
    if valor is None or valor == "":
        if obligatorio:
            raise ValueError(f"Falta {nombre}.")
        return None
    try:
        n = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{nombre} debe ser un número.")
    if n < 0:
        raise ValueError(f"{nombre} no puede ser negativo.")
    return int(n) if entero else n


def _fecha(valor: Any) -> str:
    try:
        return date.fromisoformat(str(valor)[:10]).isoformat()
    except ValueError:
        raise ValueError("La fecha debe tener el formato AAAA-MM-DD.")


# ── clasificaciones (tablas de los procedimientos) ───────────────────────────

def estado_caja(dias: Optional[float]) -> Dict[str, str]:
    if dias is None:
        return {"estado": "SIN_DATOS", "texto": "Faltan datos para calcular los días de caja."}
    if dias >= 7:
        return {"estado": "SALUDABLE", "texto": "≥ 7 días de caja."}
    if dias >= 4:
        return {"estado": "PRECAUCION", "texto": "4–6 días: reducir el presupuesto de ads un 20 %."}
    if dias >= 2:
        return {"estado": "ALERTA", "texto": "2–3 días: pausar ads hasta que la pasarela libere pagos."}
    return {"estado": "CRITICO", "texto": "< 2 días: pausar ads de inmediato y no hacer pedidos nuevos."}


def estado_roas(roas: Optional[float]) -> Dict[str, str]:
    if roas is None:
        return {"estado": "SIN_DATOS", "texto": "Sin gasto publicitario registrado."}
    if roas >= 3.0:
        return {"estado": "RENTABLE", "texto": "Campaña rentable: mantener o escalar."}
    if roas >= 2.0:
        return {"estado": "AJUSTADO", "texto": "Rentable pero ajustado: optimizar públicos."}
    if roas >= 1.0:
        return {"estado": "PERDIDA", "texto": "En pérdida: revisar CPA y producto."}
    return {"estado": "SANGRADO", "texto": "Sangrado: pausar inmediatamente."}


def cpa_producto(costo_origen: float, costo_envio: float, pvp: float) -> Dict[str, float]:
    """CPA máximo (punto de equilibrio) y objetivo. El equilibrio es el margen neto por
    unidad tras coste landed, fees (4,0 %) y cancelaciones (10,1 %)."""
    landed = (costo_origen or 0) + (costo_envio or 0)
    cpa_max = pvp - landed - pvp * FEES_PCT - pvp * CANCELACIONES_PCT
    return {"cpa_max": round(cpa_max, 2), "cpa_objetivo": round(cpa_max * CPA_OBJETIVO_FACTOR, 2)}


# ── escritura ────────────────────────────────────────────────────────────────

def registrar_dia(db_path: str, datos: Dict[str, Any]) -> Dict[str, Any]:
    """Guarda (o sustituye) las métricas de un día/producto/plataforma."""
    fecha = _fecha(datos.get("fecha") or date.today())
    plataforma = str(datos.get("plataforma") or "meta").lower()[:20]
    producto_id = datos.get("producto_id") or None
    fila = {
        "gasto_ads": _num(datos.get("gasto_ads", 0), "El gasto en ads") or 0.0,
        "ingresos": _num(datos.get("ingresos", 0), "Los ingresos") or 0.0,
        "pedidos": _num(datos.get("pedidos", 0), "Los pedidos", entero=True) or 0,
        "cogs_pagado": _num(datos.get("cogs_pagado", 0), "El coste de productos pagado") or 0.0,
        "devoluciones": _num(datos.get("devoluciones"), "Las devoluciones"),
        "visitantes": _num(datos.get("visitantes"), "Los visitantes", entero=True),
        "presupuesto_diario": _num(datos.get("presupuesto_diario"), "El presupuesto diario"),
    }
    cid = str(uuid.uuid4())
    with _db(db_path) as conn:
        if producto_id and not conn.execute("SELECT 1 FROM productos WHERE id = ?", (producto_id,)).fetchone():
            raise ValueError("Ese producto no existe.")
        conn.execute(
            """INSERT INTO metricas_diarias
                   (fecha, producto_id, plataforma, gasto_ads, ingresos, pedidos, cogs_pagado,
                    devoluciones, visitantes, presupuesto_diario, notas, correlation_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(fecha, COALESCE(producto_id, 0), plataforma) DO UPDATE SET
                   gasto_ads=excluded.gasto_ads, ingresos=excluded.ingresos, pedidos=excluded.pedidos,
                   cogs_pagado=excluded.cogs_pagado, devoluciones=excluded.devoluciones,
                   visitantes=excluded.visitantes, presupuesto_diario=excluded.presupuesto_diario,
                   notas=excluded.notas, correlation_id=excluded.correlation_id""",
            (fecha, producto_id, plataforma, fila["gasto_ads"], fila["ingresos"], fila["pedidos"],
             fila["cogs_pagado"], fila["devoluciones"], fila["visitantes"], fila["presupuesto_diario"],
             str(datos.get("notas") or "")[:500], cid))
        conn.commit()
    return {"fecha": fecha, "producto_id": producto_id, "plataforma": plataforma,
            "correlation_id": cid, **fila}


def registrar_caja(db_path: str, datos: Dict[str, Any]) -> Dict[str, Any]:
    fecha = _fecha(datos.get("fecha") or date.today())
    fila = {
        "saldo_cuenta": _num(datos.get("saldo_cuenta"), "El saldo de la cuenta", obligatorio=True),
        "liberaciones_pasarela": _num(datos.get("liberaciones_pasarela", 0), "Las liberaciones de pasarela") or 0.0,
        "pagos_proveedor_pendientes": _num(datos.get("pagos_proveedor_pendientes", 0), "Los pagos pendientes al proveedor") or 0.0,
    }
    cid = str(uuid.uuid4())
    with _db(db_path) as conn:
        conn.execute(
            """INSERT INTO caja_diaria (fecha, saldo_cuenta, liberaciones_pasarela,
                                        pagos_proveedor_pendientes, notas, correlation_id)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(fecha) DO UPDATE SET saldo_cuenta=excluded.saldo_cuenta,
                   liberaciones_pasarela=excluded.liberaciones_pasarela,
                   pagos_proveedor_pendientes=excluded.pagos_proveedor_pendientes,
                   notas=excluded.notas, correlation_id=excluded.correlation_id""",
            (fecha, fila["saldo_cuenta"], fila["liberaciones_pasarela"],
             fila["pagos_proveedor_pendientes"], str(datos.get("notas") or "")[:500], cid))
        conn.commit()
    return {"fecha": fecha, "correlation_id": cid, **fila}


def borrar_dia(db_path: str, metrica_id: int) -> bool:
    with _db(db_path) as conn:
        n = conn.execute("DELETE FROM metricas_diarias WHERE id = ?", (metrica_id,)).rowcount
        conn.commit()
    return n > 0


# ── lectura y cálculo ────────────────────────────────────────────────────────

def listar_metricas(db_path: str, dias: int = 30, producto_id: Optional[int] = None) -> List[Dict[str, Any]]:
    desde = (date.today() - timedelta(days=max(1, dias) - 1)).isoformat()
    sql = ("SELECT m.*, p.nombre AS producto FROM metricas_diarias m "
           "LEFT JOIN productos p ON p.id = m.producto_id WHERE m.fecha >= ?")
    params: List[Any] = [desde]
    if producto_id:
        sql += " AND m.producto_id = ?"
        params.append(producto_id)
    sql += " ORDER BY m.fecha DESC, m.id DESC"
    with _db(db_path) as conn:
        return [dict(r) for r in conn.execute(sql, params)]


def _ultima_caja(db_path: str) -> Optional[Dict[str, Any]]:
    with _db(db_path) as conn:
        r = conn.execute("SELECT * FROM caja_diaria ORDER BY fecha DESC LIMIT 1").fetchone()
    return dict(r) if r else None


def _dias_caja(db_path: str, filas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Caja disponible real y días de caja (Pasos 2 y 3 del procedimiento)."""
    caja = _ultima_caja(db_path)
    if not caja:
        return {"caja": None, "caja_disponible": None, "dias_de_caja": None}
    disponible = caja["saldo_cuenta"] + caja["liberaciones_pasarela"] - caja["pagos_proveedor_pendientes"]
    dias_con_datos = len({f["fecha"] for f in filas}) or 0
    gasto_diario = sum(f["gasto_ads"] for f in filas) / dias_con_datos if dias_con_datos else 0
    cogs_diario = sum(f["cogs_pagado"] for f in filas) / dias_con_datos if dias_con_datos else 0
    salida_diaria = gasto_diario + cogs_diario
    dias = round(disponible / salida_diaria, 1) if salida_diaria > 0 else None
    return {"caja": caja, "caja_disponible": round(disponible, 2), "dias_de_caja": dias,
            "gasto_diario": round(gasto_diario, 2), "cogs_diario": round(cogs_diario, 2)}


def resumen(db_path: str, dias: int = 7, producto_id: Optional[int] = None) -> Dict[str, Any]:
    """Estado de salud financiera del periodo (monitorear_flujo_caja)."""
    filas = listar_metricas(db_path, dias, producto_id)
    huecos: List[str] = []
    if not filas:
        huecos.append("No hay métricas registradas en este periodo.")
    ingresos = sum(f["ingresos"] for f in filas)
    gasto = sum(f["gasto_ads"] for f in filas)
    cogs = sum(f["cogs_pagado"] for f in filas)
    pedidos = sum(f["pedidos"] for f in filas)

    registradas = [f["devoluciones"] for f in filas if f["devoluciones"] is not None]
    devoluciones_estimadas = len(registradas) < len(filas)
    devoluciones = sum(registradas) + sum(f["ingresos"] * CANCELACIONES_PCT for f in filas if f["devoluciones"] is None)
    fees = ingresos * FEES_PCT

    resultado_periodo = ingresos - gasto - cogs
    margen_neto = ingresos - cogs - gasto - fees - devoluciones
    roas = round(ingresos / gasto, 2) if gasto > 0 else None
    cpa = round(gasto / pedidos, 2) if pedidos > 0 else None

    caja = _dias_caja(db_path, listar_metricas(db_path, 7))
    if caja["caja"] is None:
        huecos.append("Falta registrar la caja (saldo, liberaciones de pasarela y pagos pendientes al proveedor).")
    caja_est = estado_caja(caja["dias_de_caja"])
    roas_est = estado_roas(roas)

    # Señal general y acción (reglas de comportamiento del procedimiento)
    acciones: List[str] = []
    if caja_est["estado"] in ("CRITICO", "ALERTA") or roas_est["estado"] == "SANGRADO":
        senal = "CRITICO" if caja_est["estado"] == "CRITICO" or roas_est["estado"] == "SANGRADO" else "ADVERTENCIA"
    elif caja_est["estado"] in ("PRECAUCION",) or roas_est["estado"] in ("PERDIDA",):
        senal = "ADVERTENCIA"
    elif caja_est["estado"] == "SIN_DATOS" or roas_est["estado"] == "SIN_DATOS":
        senal = "SIN_DATOS"
    else:
        senal = "SALUDABLE"
    if caja_est["estado"] != "SIN_DATOS":
        acciones.append(caja_est["texto"])
    if roas_est["estado"] != "SIN_DATOS":
        acciones.append(roas_est["texto"])
    if roas and roas > 2.5 and caja["dias_de_caja"] is not None and caja["dias_de_caja"] < 4:
        acciones.append("ROAS alto pero poca caja: espera a la liberación de pagos antes de escalar.")
    acciones.append("Las pasarelas liberan en 2–3 días pero el proveedor cobra ahora: vigila ese desfase.")

    return {
        "periodo_dias": dias, "dias_con_datos": len({f["fecha"] for f in filas}),
        "ingresos": round(ingresos, 2), "gasto_ads": round(gasto, 2), "cogs_pagado": round(cogs, 2),
        "pedidos": pedidos, "resultado_periodo": round(resultado_periodo, 2),
        "fees": round(fees, 2), "devoluciones": round(devoluciones, 2),
        "devoluciones_estimadas": devoluciones_estimadas,
        "margen_neto": round(margen_neto, 2),
        "roas": roas, "roas_estado": roas_est, "cpa_real": cpa,
        **{k: caja[k] for k in ("caja", "caja_disponible", "dias_de_caja")},
        "caja_estado": caja_est, "senal": senal, "acciones": acciones, "datos_que_faltan": huecos,
    }


def serie_diaria(db_path: str, dias: int = 30, producto_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Totales por día (para el gráfico): ingresos, gasto, ROAS."""
    por_dia: Dict[str, Dict[str, float]] = {}
    for f in listar_metricas(db_path, dias, producto_id):
        d = por_dia.setdefault(f["fecha"], {"ingresos": 0.0, "gasto_ads": 0.0, "pedidos": 0})
        d["ingresos"] += f["ingresos"]
        d["gasto_ads"] += f["gasto_ads"]
        d["pedidos"] += f["pedidos"]
    out = []
    for fecha in sorted(por_dia):
        d = por_dia[fecha]
        out.append({"fecha": fecha, **{k: round(v, 2) for k, v in d.items()},
                    "roas": round(d["ingresos"] / d["gasto_ads"], 2) if d["gasto_ads"] > 0 else None})
    return out


# ── escalado (escalar_campana) ───────────────────────────────────────────────

def evaluar_escalado(db_path: str, producto: Dict[str, Any]) -> Dict[str, Any]:
    """Decisión ESCALAR / MANTENER / OPTIMIZAR / CORTAR para un producto con campaña,
    siguiendo el árbol de decisión del procedimiento."""
    filas = sorted(listar_metricas(db_path, 3650, producto["id"]), key=lambda f: f["fecha"])
    filas = [f for f in filas if f["gasto_ads"] > 0 or f["pedidos"] > 0]
    if not filas:
        return {"decision": "SIN_DATOS", "escenario": None, "dia": 0,
                "accion": "Registra las métricas diarias de este producto (gasto, ingresos, pedidos).",
                "advertencias": [], "metricas": {}}

    primero = date.fromisoformat(filas[0]["fecha"])
    ultimo = date.fromisoformat(filas[-1]["fecha"])
    dia = (ultimo - primero).days + 1
    ventas = sum(f["pedidos"] for f in filas)
    gasto = sum(f["gasto_ads"] for f in filas)
    ingresos = sum(f["ingresos"] for f in filas)
    visitantes = sum(f["visitantes"] or 0 for f in filas)
    roas = ingresos / gasto if gasto > 0 else 0.0
    cpa_real = gasto / ventas if ventas > 0 else None
    cr = ventas / visitantes * 100 if visitantes > 0 else None
    presupuesto = next((f["presupuesto_diario"] for f in reversed(filas) if f["presupuesto_diario"]), None)

    cpa = cpa_producto(producto.get("costo_origen") or 0, producto.get("costo_envio") or 0,
                       producto.get("pvp") or 0) if producto.get("pvp") else None
    cpa_max = cpa["cpa_max"] if cpa else None
    adv: List[str] = []
    if cpa_max is None:
        adv.append("El producto no tiene PVP/costes: no se puede comparar el CPA con el máximo.")
    if cr is None:
        adv.append("Faltan visitantes: no se puede calcular la tasa de conversión (CR).")

    metricas = {"ventas": ventas, "gasto": round(gasto, 2), "ingresos": round(ingresos, 2),
                "roas": round(roas, 2), "cpa_real": round(cpa_real, 2) if cpa_real is not None else None,
                "cpa_max": cpa_max, "cr": round(cr, 2) if cr is not None else None,
                "presupuesto_diario": presupuesto}

    if dia <= 2:   # periodo de aprendizaje: no tocar el presupuesto
        if ventas == 0:
            return {"decision": "MANTENER", "escenario": "APRENDIZAJE", "dia": dia, "metricas": metricas,
                    "accion": "Sin ventas todavía: espera al día 3 antes de decidir. No cambies el presupuesto.",
                    "advertencias": adv}
        if cpa_max is not None and cpa_real is not None and cpa_real > cpa_max * 1.5:
            return {"decision": "OPTIMIZAR", "escenario": "APRENDIZAJE", "dia": dia, "metricas": metricas,
                    "accion": "CPA por encima de 1,5× el máximo: pausa el conjunto de anuncios ineficiente.",
                    "advertencias": adv}
        return {"decision": "MANTENER", "escenario": "APRENDIZAJE", "dia": dia, "metricas": metricas,
                "accion": "Deja correr sin cambios: el algoritmo necesita datos.", "advertencias": adv}

    # Día 3 en adelante: escenarios sobre los resultados acumulados
    if ventas == 0 or roas < 1.0:
        escenario, decision = "NEGATIVO", "CORTAR"
        accion = ("Corta la campaña y vuelve a buscar producto. Cortar rápido es disciplina, no fracaso.")
    elif roas >= 2.5 and cpa_max is not None and cpa_real is not None and cpa_real <= cpa_max:
        escenario, decision = "WINNER", "ESCALAR"
        accion = (f"Sube el presupuesto un 20 %" +
                  (f": de {presupuesto:g} a {presupuesto * 1.2:.2f} por día." if presupuesto else "."))
    elif 1.8 <= roas < 2.5 and cr is not None and cr > 1.5:
        escenario, decision = "POSITIVO", "MANTENER"
        accion = "Mantén el presupuesto y optimiza públicos."
    elif roas >= 2.5:    # ROAS alto pero sin poder confirmar el CPA: no se escala a ciegas
        escenario, decision = "POSITIVO", "MANTENER"
        accion = "ROAS alto, pero el CPA no está confirmado frente al máximo: mantén y completa los datos."
    elif 1.8 <= roas < 2.5 and cr is None:
        escenario, decision = "POSITIVO", "MANTENER"
        accion = "ROAS 1,8–2,49 sin CR para confirmarlo: mantén y registra los visitantes."
    else:
        escenario, decision = "DUDOSO", "OPTIMIZAR"
        accion = "Pausa las creatividades peores y mantén el presupuesto 3 días más."

    if decision == "ESCALAR":   # condiciones adicionales del procedimiento
        dias_caja = _dias_caja(db_path, listar_metricas(db_path, 7))["dias_de_caja"]
        if dias_caja is None:
            decision, accion = "MANTENER", "No escales sin verificar los días de caja: registra la caja de hoy."
            adv.append("Falta la caja: nunca se escala sin comprobarla.")
        elif dias_caja < 4:
            decision, accion = "MANTENER", f"Días de caja {dias_caja} (< 4): espera a la liberación de pagos antes de escalar."
            adv.append("Días de caja < 4: no escalar.")
        else:
            ult = filas[-1]
            if cpa_max is not None and ult["pedidos"] > 0 and ult["gasto_ads"] / ult["pedidos"] > cpa_max:
                decision, accion = "MANTENER", "El CPA de hoy supera el máximo: no escales hoy, espera la recuperación."
                adv.append("CPA del último día por encima del máximo.")
            else:
                adv.append("Escala como máximo cada 2–3 días y nunca dupliques el presupuesto de golpe.")
    if (presupuesto or 0) and (presupuesto < 30) and dia < 5 and decision in ("CORTAR", "OPTIMIZAR"):
        adv.append("Con menos de 30 al día el criterio de 3 días puede necesitar hasta 5 días.")
    return {"decision": decision, "escenario": escenario, "dia": dia, "metricas": metricas,
            "accion": accion, "advertencias": adv}


# ── integraciones ────────────────────────────────────────────────────────────

_INTEGRACIONES = [
    ("openrouter", "OpenRouter (IA)", ["OPENROUTER_API_KEY"], "Agente, copys, guiones y extracción de la KB"),
    ("shopify", "Shopify", ["SHOPIFY_STORE_URL", "SHOPIFY_ACCESS_TOKEN"], "Borradores de producto y webhooks"),
    ("make", "Make.com · TikTok", ["MAKE_WEBHOOK_TIKTOK"], "Publicación automática de guiones"),
    ("make_carrito", "Make.com · carrito abandonado", ["MAKE_WEBHOOK_ABANDONED_CART"], "Recuperación de carritos"),
    ("klaviyo", "Klaviyo", ["KLAVIYO_API_KEY"], "Emails y listas"),
    ("sheets", "Google Sheets", ["GOOGLE_SHEETS_SPREADSHEET_ID"], "Dashboard de métricas"),
    ("removebg", "remove.bg", ["REMOVEBG_API_KEY"], "Fondo de imágenes de producto"),
    ("higgsfield", "Higgsfield", ["HIGGSFIELD_API_KEY"], "Vídeos TikTok con IA"),
    ("youtube_api", "YouTube Data API (opcional)", ["YOUTUBE_API_KEY"], "Búsqueda de vídeos por palabra clave"),
]


def estado_integraciones() -> List[Dict[str, Any]]:
    """Qué está configurado (solo sí/no y qué variables faltan; nunca se muestran los valores).
    Meta Ads no tiene integración: sus datos se registran a mano en /negocio."""
    import os
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    out = []
    for clave, nombre, variables, para in _INTEGRACIONES:
        faltan = [v for v in variables if not (os.getenv(v) or "").strip()]
        out.append({"id": clave, "nombre": nombre, "para": para, "configurada": not faltan,
                    "faltan": faltan, "nota": ""})
    out.append({"id": "meta_ads", "nombre": "Meta Ads / TikTok Ads", "para": "Gasto y ROAS de campañas",
                "configurada": False, "faltan": [], "nota": "Sin integración: registra los datos a mano en Negocio."})
    return out
