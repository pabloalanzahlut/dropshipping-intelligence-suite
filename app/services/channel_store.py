"""
channel_store — gestión de canales de YouTube (listar, editar, activar, borrar, verificar).

Los canales viven en dos sitios que hay que mantener a la vez:
  - data/youtube_channels.json : los mentores (con sus reglas: rol, max_videos_scan, filtro_tema)
  - tabla canales_favoritos     : la lista completa de favoritos (29)
Una URL puede estar en uno o en los dos; aquí se trata como UN solo canal.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

CAMPOS_EDITABLES = {"nombre", "activo", "prioridad", "idioma", "tags", "filtro_tema", "max_videos_scan"}
_CANAL_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?youtube\.com/"
    r"(?:@[A-Za-z0-9._-]+|channel/UC[A-Za-z0-9_-]+|c/[A-Za-z0-9_.-]+|user/[A-Za-z0-9_.-]+)/?$"
)


def normalizar_url(url: str) -> str:
    u = (url or "").strip().lower().rstrip("/")
    return re.sub(r"^https?://(www\.)?", "", u)


def _leer_json(config_path: str) -> List[Dict[str, Any]]:
    try:
        datos = json.loads(Path(config_path).read_text(encoding="utf-8"))
        return [c for c in datos if isinstance(c, dict)] if isinstance(datos, list) else []
    except Exception:
        return []


def _guardar_json(config_path: str, canales: List[Dict[str, Any]]) -> None:
    ruta = Path(config_path)
    tmp = ruta.with_suffix(ruta.suffix + ".tmp")
    tmp.write_text(json.dumps(canales, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, ruta)


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _tags_a_lista(tags: Any) -> List[str]:
    if isinstance(tags, (list, tuple)):
        return [str(t).strip() for t in tags if str(t).strip()]
    return [t.strip() for t in str(tags or "").split(",") if t.strip()]


def listar(config_path: str, db_path: str) -> List[Dict[str, Any]]:
    """Canales unificados, con cuántas transcripciones tiene cada uno y su último estado."""
    por_url: Dict[str, Dict[str, Any]] = {}
    for c in _leer_json(config_path):
        clave = normalizar_url(c.get("url", ""))
        por_url[clave] = {
            "nombre": c.get("nombre", ""), "url": c.get("url", ""), "activo": bool(c.get("activo", True)),
            "prioridad": c.get("prioridad", 5), "idioma": c.get("idioma", "es"),
            "tags": _tags_a_lista(c.get("tags")), "filtro_tema": bool(c.get("filtro_tema", False)),
            "max_videos_scan": c.get("max_videos_scan", 15), "rol": c.get("rol", ""),
            "ultimo_estado": None, "ultimo_check": None, "origen": "json",
        }
    try:
        with _db(db_path) as conn:
            for r in conn.execute("SELECT * FROM canales_favoritos WHERE url IS NOT NULL AND url != ''"):
                clave = normalizar_url(r["url"])
                existente = por_url.get(clave)
                if existente:
                    existente["origen"] = "ambos"
                    existente["ultimo_estado"] = r["ultimo_estado"]
                    existente["ultimo_check"] = r["ultimo_check"]
                    continue
                por_url[clave] = {
                    "nombre": r["nombre"], "url": r["url"], "activo": bool(r["activo"]),
                    "prioridad": r["prioridad"] or 5, "idioma": r["idioma"] or "es",
                    "tags": _tags_a_lista(r["tags"]), "filtro_tema": bool(r["filtro_tema"]),
                    "max_videos_scan": 15, "rol": "", "ultimo_estado": r["ultimo_estado"],
                    "ultimo_check": r["ultimo_check"], "origen": "db",
                }
            conteos = {r["canal"]: r["n"] for r in conn.execute(
                "SELECT canal, COUNT(*) AS n FROM transcripciones_youtube GROUP BY canal")}
    except sqlite3.Error:
        conteos = {}
    canales = sorted(por_url.values(), key=lambda c: (c["prioridad"], c["nombre"].lower()))
    for c in canales:
        c["transcripciones"] = conteos.get(c["nombre"], 0)
    return canales


def actualizar(config_path: str, db_path: str, url: str, cambios: Dict[str, Any]) -> Dict[str, Any]:
    """Aplica cambios al canal en el JSON y/o la BD. Devuelve el canal actualizado.

    Raises: KeyError si el canal no existe; ValueError si algún dato no es válido."""
    cambios = {k: v for k, v in cambios.items() if k in CAMPOS_EDITABLES and v is not None}
    if "prioridad" in cambios:
        cambios["prioridad"] = int(cambios["prioridad"])
        if not 1 <= cambios["prioridad"] <= 10:
            raise ValueError("La prioridad va de 1 (alta) a 10 (baja).")
    if "idioma" in cambios and cambios["idioma"] not in ("es", "en", "pt", "it"):
        raise ValueError("Idioma no soportado (es, en, pt, it).")
    if "nombre" in cambios and not str(cambios["nombre"]).strip():
        raise ValueError("El nombre no puede estar vacío.")

    clave = normalizar_url(url)
    encontrado = False
    canales = _leer_json(config_path)
    for c in canales:
        if normalizar_url(c.get("url", "")) == clave:
            encontrado = True
            for k, v in cambios.items():
                c[k] = _tags_a_lista(v) if k == "tags" else (bool(v) if k in ("activo", "filtro_tema") else v)
    if encontrado:
        _guardar_json(config_path, canales)

    columnas_db = {"nombre", "activo", "prioridad", "idioma", "tags", "filtro_tema"}
    with _db(db_path) as conn:
        fila = conn.execute(
            "SELECT id FROM canales_favoritos WHERE lower(rtrim(url, '/')) = ? "
            "OR lower(replace(replace(rtrim(url, '/'), 'https://', ''), 'www.', '')) = ?",
            (clave, clave)).fetchone()
        if fila:
            encontrado = True
            sets, vals = [], []
            for k, v in cambios.items():
                if k in columnas_db:
                    sets.append(f"{k} = ?")
                    vals.append(", ".join(_tags_a_lista(v)) if k == "tags"
                                else (int(bool(v)) if k in ("activo", "filtro_tema") else v))
            if sets:
                conn.execute(f"UPDATE canales_favoritos SET {', '.join(sets)} WHERE id = ?", vals + [fila["id"]])
                conn.commit()
    if not encontrado:
        raise KeyError("Canal no encontrado")
    return next(c for c in listar(config_path, db_path) if normalizar_url(c["url"]) == clave)


def eliminar(config_path: str, db_path: str, url: str) -> bool:
    """Quita el canal de la lista (JSON y BD). No borra sus transcripciones ni su KB."""
    clave = normalizar_url(url)
    hecho = False
    canales = _leer_json(config_path)
    restantes = [c for c in canales if normalizar_url(c.get("url", "")) != clave]
    if len(restantes) != len(canales):
        _guardar_json(config_path, restantes)
        hecho = True
    with _db(db_path) as conn:
        filas = conn.execute("SELECT id, url FROM canales_favoritos").fetchall()
        ids = [f["id"] for f in filas if normalizar_url(f["url"] or "") == clave]
        for i in ids:
            conn.execute("DELETE FROM canales_favoritos WHERE id = ?", (i,))
            hecho = True
        conn.commit()
    return hecho


def agregar(config_path: str, db_path: str, url: str, nombre: str, tags: str = "",
            idioma: str = "es", prioridad: int = 5, max_videos_scan: int = 30,
            filtro_tema: bool = True) -> Dict[str, Any]:
    """Alta de un canal en el JSON y la BD (por defecto con filtro de tema: solo ecommerce)."""
    url, nombre = (url or "").strip(), (nombre or "").strip()
    if not _CANAL_RE.match(url):
        raise ValueError("URL de canal no válida (ej: https://www.youtube.com/@canal).")
    if not nombre:
        raise ValueError("Falta el nombre del canal.")
    if any(normalizar_url(c["url"]) == normalizar_url(url) for c in listar(config_path, db_path)):
        raise FileExistsError("Canal ya registrado.")
    entrada = {"url": url, "nombre": nombre, "activo": True, "tags": _tags_a_lista(tags),
               "prioridad": int(prioridad), "idioma": idioma, "max_videos_scan": int(max_videos_scan),
               "filtro_tema": bool(filtro_tema)}
    canales = _leer_json(config_path)
    canales.append(entrada)
    _guardar_json(config_path, canales)
    handle = url.rstrip("/").split("/")[-1].lower()
    with _db(db_path) as conn:
        conn.execute(
            """INSERT OR IGNORE INTO canales_favoritos
               (handle, nombre, url, idioma, especialidad, tags, prioridad, filtro_tema)
               VALUES (?,?,?,?,?,?,?,?)""",
            (handle, nombre, url, idioma, "general", ", ".join(entrada["tags"]), int(prioridad), int(bool(filtro_tema))))
        conn.commit()
    return next(c for c in listar(config_path, db_path) if normalizar_url(c["url"]) == normalizar_url(url))


def verificar(db_path: str, url: str) -> Dict[str, Any]:
    """Comprueba que el canal existe y tiene vídeos (RSS o yt-dlp). Guarda el resultado.

    Estados: 'ok', 'sin_videos', 'no_encontrado'."""
    from app.services.youtube_rss_fetcher import fetch_channel_videos
    ahora = datetime.now().isoformat(timespec="seconds")
    try:
        videos = fetch_channel_videos(url, max_videos=1)
        estado = "ok" if videos else "no_encontrado"
    except Exception:
        estado = "no_encontrado"
    clave = normalizar_url(url)
    with _db(db_path) as conn:
        for f in conn.execute("SELECT id, url FROM canales_favoritos").fetchall():
            if normalizar_url(f["url"] or "") == clave:
                conn.execute("UPDATE canales_favoritos SET ultimo_estado = ?, ultimo_check = ? WHERE id = ?",
                             (estado, ahora, f["id"]))
        conn.commit()
    return {"url": url, "estado": estado, "ultimo_check": ahora}
