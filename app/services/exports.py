"""
exports — consultas de historial y exportación a CSV.

Un mismo formato {columnas, filas, total} sirve a la pantalla Historial y a las descargas CSV.
El CSV va en UTF-8 con BOM (Excel lo abre con los acentos bien) y neutraliza la "inyección
de fórmulas": una celda que empiece por = + - @ se prefija con una comilla simple.
"""
from __future__ import annotations

import csv
import io
import sqlite3
from typing import Any, Dict, List, Optional, Sequence, Tuple

Columna = Tuple[str, str]   # (campo, título)

# tipo -> (tabla, columnas, orden, columnas donde buscar)
DATASETS: Dict[str, Tuple[str, List[Columna], str, List[str]]] = {
    "productos": ("productos",
                  [("id", "ID"), ("nombre", "Producto"), ("estado", "Estado"), ("clasificacion", "Clasif."),
                   ("costo_origen", "Coste origen"), ("costo_envio", "Envío"), ("pvp", "PVP"),
                   ("multiplicador", "Multiplicador"), ("veredicto_refutacion", "Veredicto refutación"),
                   ("actualizado_at", "Actualizado")],
                  "actualizado_at DESC, id DESC", ["nombre", "categoria", "notas"]),
    "validaciones": ("productos_validados",
                     [("id", "ID"), ("sku", "SKU / producto"), ("costo_origen", "Coste origen"), ("pvp", "PVP"),
                      ("margen_bruto", "Margen bruto %"), ("status_validacion", "Estado"),
                      ("nota_auditoria", "Nota"), ("creada_at", "Fecha")],
                     "id DESC", ["sku", "nota_auditoria"]),
    "copys": ("copys_generados",
              [("id", "ID"), ("titulo_copy", "Título"), ("descripcion", "Descripción"),
               ("promedio_score", "Score AIDA"), ("sin_superlativos", "Sin superlativos"), ("creada_at", "Fecha")],
              "id DESC", ["titulo_copy", "descripcion"]),
    "guiones": ("guiones_tiktok",
                [("id", "ID"), ("titulo", "Título"), ("hook", "Hook"), ("cuerpo", "Cuerpo"), ("cta", "CTA"),
                 ("patron_hook", "Patrón"), ("duracion_segundos", "Duración (s)"), ("creada_at", "Fecha")],
                "id DESC", ["titulo", "hook", "cuerpo", "cta"]),
    "metricas": ("metricas_diarias",
                 [("fecha", "Fecha"), ("plataforma", "Plataforma"), ("gasto_ads", "Gasto ads"),
                  ("ingresos", "Ingresos"), ("pedidos", "Pedidos"), ("cogs_pagado", "Coste pagado"),
                  ("devoluciones", "Devoluciones"), ("visitantes", "Visitantes"),
                  ("presupuesto_diario", "Presupuesto/día")],
                 "fecha DESC, id DESC", ["plataforma", "notas"]),
    "transcripciones": ("transcripciones_youtube",
                        [("id", "ID"), ("titulo", "Título"), ("canal", "Canal"), ("fecha", "Fecha"),
                         ("idioma", "Idioma"), ("tokens_original", "Tokens orig."), ("tokens_limpios", "Tokens limpios")],
                        "id DESC", ["titulo", "canal"]),
}
TIPOS = list(DATASETS) + ["insights", "canales"]
MAX_FILAS_CSV = 50000


def _like(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def consultar(db_path: str, tipo: str, buscar: str = "", limite: int = 100, offset: int = 0) -> Dict[str, Any]:
    """Filas de un dataset basado en tabla. Lanza KeyError si el tipo no existe."""
    tabla, columnas, orden, buscables = DATASETS[tipo]
    limite = max(1, min(int(limite), MAX_FILAS_CSV))
    campos = ", ".join(c for c, _ in columnas)
    where, params = "", []
    if buscar.strip():
        where = "WHERE " + " OR ".join(f"{c} LIKE ? ESCAPE '\\'" for c in buscables)
        params = [_like(buscar.strip())] * len(buscables)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM {tabla} {where}", params).fetchone()[0]
        filas = [dict(r) for r in conn.execute(
            f"SELECT {campos} FROM {tabla} {where} ORDER BY {orden} LIMIT ? OFFSET ?",
            params + [limite, max(0, int(offset))])]
    finally:
        conn.close()
    return {"tipo": tipo, "columnas": [{"k": c, "t": t} for c, t in columnas], "filas": filas, "total": total}


def _celda(valor: Any) -> Any:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "sí" if valor else "no"
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + valor        # neutraliza fórmulas de hoja de cálculo
    return valor


def a_csv(columnas: Sequence[Dict[str, str]], filas: Sequence[Dict[str, Any]]) -> bytes:
    salida = io.StringIO()
    w = csv.writer(salida, lineterminator="\r\n")
    w.writerow([c["t"] for c in columnas])
    for f in filas:
        w.writerow([_celda(f.get(c["k"])) for c in columnas])
    return ("﻿" + salida.getvalue()).encode("utf-8")


# ── historial unificado (lo comparten la web y el escritorio) ────────────────

def dataset(db_path: str, config_path: str, tipo: str, buscar: str = "", limite: int = 50,
            offset: int = 0) -> Dict[str, Any]:
    """Filas en el formato común {columnas, filas, total} para cualquier tipo de historial,
    incluidos `insights` y `canales`. Lanza KeyError si el tipo no existe."""
    from app.services import channel_store, insights_service
    if tipo in DATASETS:
        return consultar(db_path, tipo, buscar, limite, offset)
    if tipo == "insights":
        res = insights_service.query_insights(db_path, buscar=buscar, limite=min(limite, 200), offset=offset,
                                              preview_chars=400)
        cols = [("source_table", "Tipo"), ("titulo", "Insight"), ("subtitulo", "Nicho / marco"),
                ("content_preview", "Contenido"), ("channel_name", "Canal"), ("video_title", "Vídeo"),
                ("created_at", "Fecha")]
        return {"tipo": tipo, "columnas": [{"k": k, "t": t} for k, t in cols], "filas": res["items"],
                "total": res["total"]}
    if tipo == "canales":
        todos = channel_store.listar(config_path, db_path)
        if buscar.strip():
            q = buscar.strip().lower()
            todos = [c for c in todos if q in (c["nombre"] + " " + c["url"]).lower()]
        cols = [("nombre", "Canal"), ("url", "URL"), ("activo", "Activo"), ("prioridad", "Prioridad"),
                ("idioma", "Idioma"), ("filtro_tema", "Solo ecommerce"), ("transcripciones", "Transcripciones"),
                ("ultimo_estado", "Última verificación")]
        return {"tipo": tipo, "columnas": [{"k": k, "t": t} for k, t in cols],
                "filas": todos[offset:offset + limite], "total": len(todos)}
    raise KeyError(tipo)


def todas_las_filas(db_path: str, config_path: str, tipo: str, buscar: str = "") -> Dict[str, Any]:
    """Todas las filas de un historial (hasta MAX_FILAS_CSV) listas para `a_csv`.
    `insights` se pide de 200 en 200 porque su consulta tiene ese tope."""
    from app.services import insights_service
    if tipo != "insights":
        return dataset(db_path, config_path, tipo, buscar, MAX_FILAS_CSV, 0)
    datos = dataset(db_path, config_path, tipo, buscar, 200, 0)
    filas, offset = list(datos["filas"]), 200
    while len(filas) < datos["total"] and offset < MAX_FILAS_CSV:
        filas += insights_service.query_insights(db_path, buscar=buscar, limite=200, offset=offset,
                                                 preview_chars=400)["items"]
        offset += 200
    datos["filas"] = filas
    return datos
