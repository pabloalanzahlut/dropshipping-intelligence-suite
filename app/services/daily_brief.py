"""
daily_brief — resumen diario automático (sin IA: solo datos reales de la base de datos).

Responde a «¿cómo está mi negocio y qué hago hoy?» en una pantalla. Cada línea sale de un
dato registrado; si falta el dato, el resumen lo dice en vez de inventarlo (regla suprema de
GEM OS: no inventar). Se genera cada mañana (08:00) y queda guardado en `resumenes_diarios`.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services import alerts, business_metrics, product_catalog


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _eur(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _negocio(db_path: str) -> Dict[str, Any]:
    ayer = (date.today() - timedelta(days=1)).isoformat()
    filas_ayer = [f for f in business_metrics.listar_metricas(db_path, 3) if f["fecha"] == ayer]
    r7 = business_metrics.resumen(db_path, 7)
    lineas: List[str] = []
    if not filas_ayer:
        lineas.append(f"Ayer ({ayer}) no hay métricas registradas.")
    else:
        ing = sum(f["ingresos"] for f in filas_ayer)
        gasto = sum(f["gasto_ads"] for f in filas_ayer)
        ped = sum(f["pedidos"] for f in filas_ayer)
        roas = f"{ing / gasto:.2f}×" if gasto > 0 else "sin gasto"
        lineas.append(f"Ayer: ingresos {_eur(ing)} · gasto en anuncios {_eur(gasto)} · {ped} pedidos · ROAS {roas}.")
    if r7["dias_con_datos"]:
        lineas.append(f"Últimos 7 días ({r7['dias_con_datos']} con datos): ingresos {_eur(r7['ingresos'])}, "
                      f"margen neto {_eur(r7['margen_neto'])}"
                      + (f", ROAS {r7['roas']}×" if r7["roas"] is not None else "")
                      + (f", CPA {_eur(r7['cpa_real'])}" if r7["cpa_real"] is not None else "") + ".")
    if r7["caja"] is None:
        lineas.append("Caja: sin registrar.")
    else:
        d = r7["dias_de_caja"]
        lineas.append(f"Caja disponible {_eur(r7['caja_disponible'])}"
                      + (f" · {d} días de caja ({r7['caja_estado']['estado'].lower()})." if d is not None
                         else " · sin gasto diario para estimar los días de caja."))
    return {"titulo": "Negocio", "lineas": lineas, "senal": r7["senal"]}


def _productos(db_path: str) -> Dict[str, Any]:
    estados = product_catalog.resumen_estados(db_path)
    total = sum(estados.values())
    lineas: List[str] = []
    if total == 0:
        lineas.append("El catálogo está vacío: todavía no hay ningún producto en el recorrido.")
    else:
        orden = ["candidato", "clasificado", "refutado", "validado", "creativo", "tienda", "escalado", "descartado"]
        lineas.append(" · ".join(f"{e} {estados[e]}" for e in orden if estados.get(e)) + f" (total {total}).")
        for p in product_catalog.listar(db_path):
            if p["estado"] in ("tienda", "escalado"):
                dec = business_metrics.evaluar_escalado(db_path, p)
                lineas.append(f"{p['nombre']}: {dec['decision']} — {dec['accion']}")
    return {"titulo": "Productos", "lineas": lineas}


def _conocimiento(db_path: str) -> Dict[str, Any]:
    desde = (datetime.now() - timedelta(hours=24)).isoformat(timespec="seconds").replace("T", " ")
    lineas: List[str] = []
    with _db(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM transcripciones_youtube").fetchone()[0]
        nuevas = conn.execute("SELECT COUNT(*) FROM transcripciones_youtube WHERE creada_at >= ?", (desde,)).fetchone()[0]
        kb_vids = conn.execute("SELECT COUNT(*) FROM video_sources WHERE platform != 'youtube_transcript'").fetchone()[0]
        kb_nuevos = conn.execute("SELECT COUNT(*) FROM video_sources WHERE platform != 'youtube_transcript' "
                                 "AND processed_at >= ?", (desde,)).fetchone()[0]
        insights = conn.execute("SELECT COUNT(*) FROM product_trends").fetchone()[0]
    lineas.append(f"Transcripciones: {total} guardadas, {nuevas} nuevas en las últimas 24 h.")
    lineas.append(f"Base de conocimiento: {kb_vids} vídeos analizados ({kb_nuevos} nuevos en 24 h) · {insights} productos con insight.")
    return {"titulo": "Conocimiento", "lineas": lineas}


def _sistema(db_path: str, config_path: str) -> Dict[str, Any]:
    lineas: List[str] = []
    try:
        ult = json.loads(Path(config_path).with_name("last_sync.json").read_text(encoding="utf-8"))
        lineas.append(f"Última sincronización de canales: {str(ult.get('fecha_sincronizacion', ''))[:16].replace('T', ' ')} "
                      f"({ult.get('transcripciones_procesadas', 0)} transcripciones"
                      + (", limitada por YouTube" if ult.get("limitado") else "") + ").")
    except Exception:
        lineas.append("Todavía no se ha sincronizado ningún canal.")
    copias = sorted((Path(db_path).resolve().parent.parent / "backups").glob(f"{Path(db_path).stem}_auto_*.db"))
    if copias:
        lineas.append("Última copia de seguridad: "
                      + datetime.fromtimestamp(copias[-1].stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                      + f" ({len(copias)} guardada{'s' if len(copias) != 1 else ''}).")
    else:
        lineas.append("Sin copias de seguridad automáticas.")
    return {"titulo": "Sistema", "lineas": lineas}


def _prioridades(db_path: str, config_path: str) -> List[Dict[str, str]]:
    """Qué hacer hoy: alertas críticas → avisos → siguiente paso del recorrido."""
    out: List[Dict[str, str]] = []
    vigentes = sorted(alerts.calcular(db_path, config_path), key=lambda a: -alerts.NIVELES.get(a["nivel"], 1))
    for a in vigentes:
        if a["nivel"] in ("critico", "aviso"):
            out.append({"nivel": a["nivel"], "texto": a["titulo"] + (f" — {a['detalle']}" if a["detalle"] else ""),
                        "enlace": a["enlace"]})
    siguiente = {"candidato": "clasificarlo (HOT/WARM/COLD)", "clasificado": "refutarlo (8 intentos de matar la tesis)",
                 "refutado": "validar el financiero sobre coste landed", "validado": "probar demanda y crear el creativo",
                 "creativo": "montar la tienda con la oferta multiunidad"}
    catalogo = product_catalog.listar(db_path)
    for p in catalogo:
        if p["estado"] in siguiente:
            out.append({"nivel": "info", "texto": f"{p['nombre']}: toca {siguiente[p['estado']]}.", "enlace": "/productos"})
    if not catalogo:
        out.append({"nivel": "info", "texto": "Añade tu primer producto candidato: el recorrido empieza en Productos.",
                    "enlace": "/productos"})
    if not out:
        out.append({"nivel": "info", "texto": "Sin urgencias. Registra las métricas de hoy cuando cierre el día.", "enlace": "/negocio"})
    return out[:8]


def generar(db_path: str, config_path: str, guardar: bool = True) -> Dict[str, Any]:
    hoy = date.today().isoformat()
    secciones = [_negocio(db_path), _productos(db_path), _conocimiento(db_path), _sistema(db_path, config_path)]
    prioridades = _prioridades(db_path, config_path)
    resumen = {"fecha": hoy, "generado_at": datetime.now().isoformat(timespec="seconds"),
               "prioridades": prioridades, "secciones": secciones}
    resumen["texto"] = a_markdown(resumen)
    if guardar:
        with _db(db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO resumenes_diarios (fecha, contenido) VALUES (?, ?)",
                         (hoy, json.dumps(resumen, ensure_ascii=False)))
            conn.commit()
    return resumen


def a_markdown(r: Dict[str, Any]) -> str:
    partes = [f"# Resumen del día — {r['fecha']}", "", "## Hoy toca"]
    partes += [f"- {'🔴' if p['nivel'] == 'critico' else '🟠' if p['nivel'] == 'aviso' else '🔹'} {p['texto']}"
               for p in r["prioridades"]]
    for s in r["secciones"]:
        partes += ["", f"## {s['titulo']}"] + [f"- {l}" for l in s["lineas"]]
    return "\n".join(partes) + "\n"


def ultimo(db_path: str, regenerar_si_falta: bool = False, config_path: str = "") -> Optional[Dict[str, Any]]:
    """El resumen más reciente guardado (opcionalmente lo genera si no hay ninguno de hoy)."""
    with _db(db_path) as conn:
        fila = conn.execute("SELECT contenido FROM resumenes_diarios ORDER BY fecha DESC LIMIT 1").fetchone()
    r = json.loads(fila["contenido"]) if fila else None
    if regenerar_si_falta and config_path and (r is None or r["fecha"] != date.today().isoformat()):
        return generar(db_path, config_path)
    return r


def historial(db_path: str, limite: int = 14) -> List[Dict[str, str]]:
    with _db(db_path) as conn:
        return [{"fecha": f["fecha"], "creado_at": f["creado_at"]} for f in
                conn.execute("SELECT fecha, creado_at FROM resumenes_diarios ORDER BY fecha DESC LIMIT ?", (limite,))]
