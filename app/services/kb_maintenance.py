"""
kb_maintenance — limpieza segura de la base de conocimiento (KB).

Todas las operaciones hacen primero una COPIA de la base de datos (backups/) y admiten
`aplicar=False` para ver qué harían sin tocar nada.

  - deduplicar_kb():         quita filas repetidas de product_trends / conversion_formulas /
                             operations_traffic (el mismo insight guardado dos veces).
  - depurar_fuera_de_tema(): quita de la KB los vídeos de canales con "filtro_tema" que no son
                             de ecommerce / dropshipping / Shopify.
  - corregir_idiomas():      etiqueta las transcripciones con su idioma real.

Uso:  python -m app.services.kb_maintenance            (simulación)
      python -m app.services.kb_maintenance --aplicar  (con copia de seguridad previa)
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services import topic_filter, transcript_store

PLATFORM_FUERA_DE_TEMA = "fuera_de_tema"
PLACEHOLDER_PRODUCTO = "Producto Extraído por IA"


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def backup_db(db_path: str, etiqueta: str = "mantenimiento_kb") -> str:
    """Copia consistente de la BD (API de backup de SQLite) en backups/. Devuelve la ruta."""
    destino_dir = Path(db_path).resolve().parent.parent / "backups"
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"{Path(db_path).stem}_{etiqueta}_{datetime.now():%Y%m%d_%H%M%S}.db"
    origen = sqlite3.connect(db_path)
    copia = sqlite3.connect(str(destino))
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()
    return str(destino)


# ── duplicados ───────────────────────────────────────────────────────────────

# (tabla, columnas que definen "el mismo insight")
_CLAVES_DUPLICADO = {
    "product_trends": "video_id, lower(product_name)",
    "conversion_formulas": "video_id, category, coalesce(framework_name,''), substr(raw_structure, 1, 120)",
    "operations_traffic": "video_id, traffic_source, substr(coalesce(scaling_strategy,''), 1, 120)",
}


def deduplicar_kb(db_path: str, aplicar: bool = False) -> Dict[str, Any]:
    """Conserva la primera fila (menor id) de cada insight repetido. Los productos sin nombre
    (placeholder) no se fusionan: pueden ser productos distintos del mismo vídeo."""
    informe: Dict[str, Any] = {"aplicado": aplicar, "tablas": {}}
    if aplicar:
        informe["backup"] = backup_db(db_path, "dedup_kb")
    with _db(db_path) as conn:
        for tabla, clave in _CLAVES_DUPLICADO.items():
            extra = f"WHERE product_name != '{PLACEHOLDER_PRODUCTO}'" if tabla == "product_trends" else ""
            sobrantes = [r[0] for r in conn.execute(
                f"""SELECT id FROM {tabla}
                    WHERE id NOT IN (SELECT MIN(id) FROM {tabla} {extra} GROUP BY {clave})
                    {'AND product_name != ' + repr(PLACEHOLDER_PRODUCTO) if tabla == 'product_trends' else ''}""")]
            informe["tablas"][tabla] = len(sobrantes)
            if aplicar and sobrantes:
                conn.executemany(f"DELETE FROM {tabla} WHERE id = ?", [(i,) for i in sobrantes])
        if aplicar:
            conn.commit()
    return informe


# ── fuera de tema ────────────────────────────────────────────────────────────

def canales_con_filtro(config_path: str) -> List[str]:
    """Nombres de los canales con "filtro_tema": true en youtube_channels.json."""
    try:
        datos = json.loads(Path(config_path).read_text(encoding="utf-8"))
    except Exception:
        return []
    return [c["nombre"] for c in datos if isinstance(c, dict) and c.get("filtro_tema") and c.get("nombre")]


def _es_del_tema(conn: sqlite3.Connection, video_id: str, titulo: str) -> bool:
    """Título con el tema, o transcripción guardada que lo trate de verdad."""
    if topic_filter.contar_menciones(titulo):
        return True
    fila = conn.execute(
        "SELECT titulo, transcripcion_texto FROM transcripciones_youtube WHERE video_id = ?",
        (video_id,)).fetchone()
    return bool(fila and topic_filter.evaluar(fila["titulo"], fila["transcripcion_texto"])[0])


def depurar_fuera_de_tema(db_path: str, config_path: str, descartados_path: Optional[str] = None,
                          kb_dir: Optional[str] = None, aplicar: bool = False) -> Dict[str, Any]:
    """Quita de la KB los vídeos fuera de tema de los canales con filtro.

    Se borran sus filas de las 3 tablas KB; la fuente (video_sources) NO se borra: se marca
    platform='fuera_de_tema' para que la ingesta no los vuelva a procesar. Los .md exportados
    se mueven a backups/, no se borran."""
    informe: Dict[str, Any] = {"aplicado": aplicar, "canales": canales_con_filtro(config_path),
                               "fuera_de_tema": [], "en_tema": 0, "filas_borradas": {}}
    if not informe["canales"]:
        return informe
    with _db(db_path) as conn:
        marcas = ",".join("?" * len(informe["canales"]))
        videos = conn.execute(
            f"""SELECT video_id, title, channel_name FROM video_sources
                WHERE channel_name IN ({marcas}) AND platform NOT IN (?, ?)""",
            informe["canales"] + [transcript_store.TRANSCRIPT_PLATFORM, PLATFORM_FUERA_DE_TEMA]).fetchall()
        fuera = [v for v in videos if not _es_del_tema(conn, v["video_id"], v["title"])]
        informe["en_tema"] = len(videos) - len(fuera)
        informe["fuera_de_tema"] = [{"video_id": v["video_id"], "titulo": v["title"], "canal": v["channel_name"]}
                                    for v in fuera]
        if not aplicar or not fuera:
            return informe

        informe["backup"] = backup_db(db_path, "fuera_de_tema")
        ids = [v["video_id"] for v in fuera]
        for tabla in ("product_trends", "conversion_formulas", "operations_traffic"):
            n = 0
            for vid in ids:
                n += conn.execute(f"DELETE FROM {tabla} WHERE video_id = ?", (vid,)).rowcount
            informe["filas_borradas"][tabla] = n
        conn.executemany("UPDATE video_sources SET platform = ? WHERE video_id = ?",
                         [(PLATFORM_FUERA_DE_TEMA, i) for i in ids])
        conn.commit()

    if descartados_path:
        ruta = Path(descartados_path)
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
        except Exception:
            datos = {}
        for v in fuera:
            datos[v["video_id"]] = {"titulo": v["title"], "canal": v["channel_name"],
                                    "motivo": "depuración de la KB: fuera de tema",
                                    "fecha": datetime.now().isoformat(timespec="seconds")}
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    if kb_dir:
        destino = Path(db_path).resolve().parent.parent / "backups" / f"kb_md_fuera_de_tema_{datetime.now():%Y%m%d}"
        movidos = 0
        for i in ids:
            for md in Path(kb_dir).glob(f"kb_{i}.md"):
                destino.mkdir(parents=True, exist_ok=True)
                shutil.move(str(md), str(destino / md.name))
                movidos += 1
        informe["md_movidos"] = movidos
    return informe


# ── idiomas ──────────────────────────────────────────────────────────────────

def corregir_idiomas(db_path: str, aplicar: bool = False) -> Dict[str, Any]:
    """Etiqueta cada transcripción con su idioma real (antes llevaba el del canal)."""
    cambios = []
    with _db(db_path) as conn:
        for f in conn.execute("SELECT id, titulo, idioma, transcripcion_texto FROM transcripciones_youtube"):
            real = transcript_store.detectar_idioma(f["transcripcion_texto"], f["idioma"] or "es")
            if real != (f["idioma"] or "es"):
                cambios.append({"id": f["id"], "titulo": f["titulo"], "de": f["idioma"], "a": real})
                if aplicar:
                    conn.execute("UPDATE transcripciones_youtube SET idioma = ? WHERE id = ?", (real, f["id"]))
        if aplicar:
            conn.commit()
    return {"aplicado": aplicar, "cambios": cambios}


def main(argv: Optional[List[str]] = None) -> int:
    from app.config.path_manager import PathManager
    argv = sys.argv[1:] if argv is None else argv
    aplicar = "--aplicar" in argv
    rutas = PathManager.get_paths()
    db, cfg = str(rutas["db"]), str(rutas["config"])
    descartados = str(Path(cfg).with_name("videos_descartados.json"))
    kb_dir = str(rutas["ai_workspace"] / "knowledge_base")
    informe = {
        "modo": "APLICAR (con copia de seguridad)" if aplicar else "SIMULACIÓN (no se cambia nada)",
        "duplicados": deduplicar_kb(db, aplicar),
        "fuera_de_tema": depurar_fuera_de_tema(db, cfg, descartados, kb_dir, aplicar),
        "idiomas": corregir_idiomas(db, aplicar),
    }
    print(json.dumps(informe, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
