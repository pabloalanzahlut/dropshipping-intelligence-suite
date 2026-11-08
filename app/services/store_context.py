"""
store_context — las cifras REALES de la tienda, listas para el agente IA.

El agente de la KB conoce lo que dicen los mentores (la Knowledge Base) pero no cómo va TU tienda. Este
módulo le da ese contexto sin dejarle margen para inventar:

  · Solo lee de SQLite (lo sincronizado de Shopify y lo importado de AutoDS). No hace red: preguntar al
    agente nunca depende de que Shopify esté disponible en ese momento.
  · Siempre indica de cuándo son los datos y de qué fuente; avisa si están obsoletos.
  · Lo que falta se escribe como DATA_GAP en vez de omitirse, para que el agente pregunte y no suponga
    (regla suprema del proyecto).
  · Es texto plano y corto (~1.500 caracteres): barato en tokens con cualquier modelo.

Lo usan el servidor web (/api/kb/query y /api/kb/stream) y el panel «Agente IA» del escritorio.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.services import autods_import, tienda_store

ETIQUETA = "TIENDA"

INSTRUCCION = (
    "Las cifras de ventas, márgenes, ROAS, costes, cancelaciones y productos de la tienda salen SOLO del bloque "
    "CONTEXTO TIENDA y se citan como [TIENDA]. Si el bloque marca un DATA_GAP o la cifra no está, dilo y pide el "
    "dato: no estimes ni uses cifras de otros contextos como si fueran de la tienda."
)


def _pct(x: Optional[float]) -> str:
    return "—" if x is None else f"{x * 100:.1f} %".replace(".", ",")


def _imp(x: Optional[float], moneda: str) -> str:
    return "—" if x is None else f"{x:,.2f} {moneda}".replace(",", " ").replace(".", ",").strip()


def construir(db_path: str, dias: int = 30) -> Dict[str, Any]:
    """{texto, conectada, obsoleto, datos}. `texto` es el bloque que se pega en el prompt del agente."""
    try:
        r = tienda_store.resumen(db_path, dias)
        a = autods_import.resumen(db_path, 90)
        est = tienda_store.estado(db_path)
    except Exception as exc:     # sin esquema / BD bloqueada: el agente sigue funcionando sin este bloque
        return {"texto": "", "conectada": False, "obsoleto": False, "datos": {}, "error": str(exc)}

    sh = est["shopify"]
    conectada = bool(r["sincronizado_at"])
    obsoleto = bool(sh["obsoleta"])
    m = r["moneda"] or ""
    if not conectada and not a["pedidos_importados_total"] and not a["productos_importados"]:
        estado = ("Shopify sin sincronizar y AutoDS sin importar" if sh["configurada"]
                  else "Shopify sin conectar (faltan credenciales) y AutoDS sin importar")
        return {"texto": f"DATA_GAP: {estado}. No hay cifras reales de la tienda: no inventes ventas, márgenes ni ROAS; "
                         "pide al operador que conecte la tienda en la pantalla Tienda.",
                "conectada": False, "obsoleto": False, "datos": {"resumen": r, "autods": a}}

    L = []
    cab = f"TIENDA REAL · Shopify sincronizado {r['sincronizado_at'][:16].replace('T', ' ')} UTC" if conectada \
        else "TIENDA REAL · Shopify sin sincronizar"
    L.append(f"{cab} · últimos {r['periodo_dias']} días ({r['desde']} → {r['hasta']})" + (f" · {m}" if m else ""))
    if obsoleto:
        L.append(f"AVISO: datos de hace {r['horas_desde_sync']:g} h; pueden no incluir los pedidos más recientes.")
    if conectada:
        L.append(f"Pedidos {r['pedidos']} (cancelados {r['cancelados']}) · unidades {r['unidades']} · "
                 f"ingresos netos {_imp(r['ingresos_netos'], m)} (bruto {_imp(r['ingresos_brutos'], m)}, "
                 f"reembolsado {_imp(r['reembolsado'], m)}) · ticket medio {_imp(r['ticket_medio'], m)}")
        cd = r["cancelaciones_y_devoluciones"]
        if cd["pct_real"] is not None:
            L.append(f"Cancelaciones+devoluciones {_pct(cd['pct_real'])} de lo facturado "
                     f"(referencia {_pct(cd['pct_referencia'])}: {cd['estado'].replace('_', ' ').lower()}) · "
                     f"fees estimados 4,0 % = {_imp(r['fees_estimados'], m)}")
        if r["gasto_ads"] > 0:
            L.append(f"Gasto en ads registrado {_imp(r['gasto_ads'], m)} · ROAS real "
                     f"{r['roas_real'] if r['roas_real'] is not None else '—'} "
                     f"({r['roas_estado']['estado'].lower()}; mínimo exigido 2)")
        mr = r["margen_real"]
        if mr:
            L.append(f"Margen real sobre {mr['pedidos_con_coste']} de {r['pedidos']} pedidos con coste conocido "
                     f"({mr['de_autods']} por AutoDS, {mr['de_shopify']} por Shopify): "
                     f"{_imp(mr['margen'], m)} = {_pct(mr['margen_pct'])} de ingresos sin impuestos"
                     + (f" · beneficio tras ads {_imp(r['beneficio_tras_ads'], m)}"
                        if r["beneficio_tras_ads"] is not None else ""))
        if r["top_productos"]:
            L.append("Top productos: " + "; ".join(
                f"{p['producto'][:40]} ({p['unidades']} ud, {_imp(p['ingresos'], m)}, margen {_pct(p['margen_pct'])})"
                for p in r["top_productos"][:3]))
        L.append(f"Catálogo activo {r['productos_activos']} productos, {r['activos_sin_ventas']} sin ventas en el periodo.")
    if a["pedidos"]:
        extra = f" · envío {_imp(a['coste_envio'], m)}" if a["coste_envio"] is not None else ""
        est_txt = ", ".join(f"{e['estado']} {e['n']}" for e in a["estados"][:4])
        L.append(f"AutoDS (importado {a['ultima_importacion'][:10]}): {a['pedidos']} líneas de pedido · coste proveedor "
                 f"{_imp(a['coste_proveedor'], m)}{extra} · estados: {est_txt}")
    for f in r["datos_que_faltan"]:
        L.append(f"DATA_GAP: {f}")
    return {"texto": "\n".join(L), "conectada": conectada, "obsoleto": obsoleto,
            "datos": {"resumen": r, "autods": a}}


def bloque_para_prompt(db_path: str, dias: int = 30) -> str:
    """Bloque listo para anteponer al prompt del agente ('' si no se pudo construir)."""
    c = construir(db_path, dias)
    if not c["texto"]:
        return ""
    return (f"CONTEXTO TIENDA (datos reales del negocio, cítalos como [{ETIQUETA}]):\n---\n{c['texto']}\n---\n"
            f"{INSTRUCCION}\n\n")
