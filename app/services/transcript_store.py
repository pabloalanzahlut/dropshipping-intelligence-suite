"""
transcript_store — acceso compartido a las transcripciones guardadas.

Lo usan la app de escritorio (Tkinter) y la web (FastAPI) para que ambas
listen, busquen, guarden, exporten y borren exactamente igual.

Reglas:
  - Una transcripción se identifica por video_id y por hash MD5 del texto crudo.
  - Se guarda el texto ORIGINAL completo (sin recortar) y el texto limpio.
  - Las filas de video_sources creadas aquí llevan platform='youtube_transcript'
    para que la ingesta de IA (KB) NO las dé por procesadas: ver
    KBCacheValidator.check_video_exists.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

TRANSCRIPT_PLATFORM = "youtube_transcript"
MAX_LIMIT = 500
MIN_CHARS = 50

_VIDEO_ID_RE = re.compile(r"^[\w-]{11}$")
_URL_ID_RE = re.compile(
    r"(?:v=|youtu\.be/|/shorts/|/embed/|/live/)([\w-]{11})(?![\w-])"
)


# ── utilidades ───────────────────────────────────────────────────────────────

@contextmanager
def _db(db_path: str) -> Iterator[sqlite3.Connection]:
    """Conexión que hace commit al salir bien, rollback si falla y SIEMPRE cierra
    (el `with sqlite3.connect()` por sí solo no cierra: en Windows deja el archivo bloqueado)."""
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _like(term: str) -> str:
    """Patrón LIKE con %, _ y \\ escapados (se usa con ESCAPE '\\')."""
    esc = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{esc}%"


def parse_video_id(url_or_id: str) -> Optional[str]:
    """Extrae el id de 11 caracteres de una URL de YouTube (o de un id suelto)."""
    value = (url_or_id or "").strip()
    if _VIDEO_ID_RE.match(value):
        return value
    m = _URL_ID_RE.search(value)
    return m.group(1) if m else None


def hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# ── lectura ──────────────────────────────────────────────────────────────────

def list_transcripts(
    db_path: str,
    buscar: str = "",
    solo_procesadas: Optional[bool] = None,
    canal: str = "",
    limite: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Lista paginada. Devuelve {"items": [...], "total": n}. Busca también en el
    texto original, así las pendientes (sin texto limpio) son encontrables."""
    limite = max(1, min(int(limite), MAX_LIMIT))
    offset = max(0, int(offset))
    conditions: List[str] = []
    params: List[Any] = []
    if buscar.strip():
        like = _like(buscar.strip())
        conditions.append(
            "(t.titulo LIKE ? ESCAPE '\\' OR t.canal LIKE ? ESCAPE '\\' "
            "OR t.transcripcion_limpia LIKE ? ESCAPE '\\' "
            "OR t.transcripcion_texto LIKE ? ESCAPE '\\')"
        )
        params += [like, like, like, like]
    if solo_procesadas is not None:
        conditions.append("t.procesada = ?")
        params.append(1 if solo_procesadas else 0)
    if canal.strip():
        conditions.append("t.canal LIKE ? ESCAPE '\\'")
        params.append(_like(canal.strip()))
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    with _db(db_path) as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM transcripciones_youtube t {where}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"""SELECT t.id, t.video_id, t.titulo, t.canal, t.fecha,
                       t.tokens_original, t.tokens_limpios, t.procesada,
                       t.creada_at,
                       substr(COALESCE(NULLIF(t.transcripcion_limpia, ''),
                                       t.transcripcion_texto), 1, 300) AS preview
                FROM transcripciones_youtube t
                {where}
                ORDER BY t.id DESC LIMIT ? OFFSET ?""",
            params + [limite, offset],
        ).fetchall()
    return {"items": [dict(r) for r in rows], "total": total}


def get_transcript(db_path: str, transcripcion_id: int) -> Optional[Dict[str, Any]]:
    with _db(db_path) as conn:
        row = conn.execute(
            """SELECT t.id, t.video_id, t.titulo, t.canal, t.fecha,
                      t.transcripcion_texto, t.transcripcion_limpia,
                      t.hash_md5, t.tokens_original, t.tokens_limpios,
                      t.procesada, t.creada_at, t.actualizada_at, t.idioma,
                      v.platform, v.processed_at
               FROM transcripciones_youtube t
               LEFT JOIN video_sources v ON t.video_id = v.video_id
               WHERE t.id = ?""",
            (transcripcion_id,),
        ).fetchone()
    return dict(row) if row else None


def stats(db_path: str) -> Dict[str, Any]:
    with _db(db_path) as conn:
        row = conn.execute(
            """SELECT COUNT(*)                          AS total,
                      COALESCE(SUM(procesada = 1), 0)   AS procesadas,
                      COUNT(DISTINCT canal)             AS canales_unicos,
                      COALESCE(SUM(tokens_limpios), 0)  AS tokens_totales,
                      COALESCE(SUM(tokens_original), 0) AS tokens_originales
               FROM transcripciones_youtube"""
        ).fetchone()
    d = dict(row)
    d["pendientes"] = d["total"] - d["procesadas"]
    d["tokens_ahorrados"] = max(0, d["tokens_originales"] - d["tokens_totales"])
    return d


def video_ids_guardados(db_path: str) -> set:
    """IDs de vídeo que ya tienen transcripción (para no volver a descargarlos)."""
    with _db(db_path) as conn:
        return {r[0] for r in conn.execute("SELECT video_id FROM transcripciones_youtube")}


# ── escritura ────────────────────────────────────────────────────────────────

def save_transcript(
    db_path: str,
    video_id: str,
    titulo: str,
    canal: str,
    raw: str,
    cleaner: Any,
    idioma: str = "es",
) -> Dict[str, Any]:
    """Limpia y guarda una transcripción. Idempotente por video_id y por hash.

    Raises:
        ValueError: texto vacío/demasiado corto o contenido duplicado de otro vídeo.
    """
    raw = (raw or "").strip()
    titulo = (titulo or "").strip() or "(sin título)"
    canal = (canal or "").strip() or "Manual"
    if len(raw) < MIN_CHARS:
        raise ValueError(f"La transcripción es demasiado corta (mínimo {MIN_CHARS} caracteres).")

    digest = hash_text(raw)
    with _db(db_path) as conn:
        dup = conn.execute(
            "SELECT id FROM transcripciones_youtube WHERE video_id = ? OR hash_md5 = ?",
            (video_id, digest),
        ).fetchone()
        if dup:
            return {"duplicado": True, "id": dup["id"], "video_id": video_id,
                    "hash_md5": digest, "mensaje": "Transcripción ya guardada"}

        cleaned = cleaner.clean(raw, log_stats=False)
        conn.execute(
            """INSERT OR IGNORE INTO video_sources
                   (video_id, platform, title, channel_name, content_hash)
               VALUES (?, ?, ?, ?, ?)""",
            (video_id, TRANSCRIPT_PLATFORM, titulo, canal, digest),
        )
        if not conn.execute(
            "SELECT 1 FROM video_sources WHERE video_id = ?", (video_id,)
        ).fetchone():
            raise ValueError("Contenido idéntico a otra fuente ya registrada.")

        cur = conn.execute(
            """INSERT INTO transcripciones_youtube
                   (video_id, titulo, canal, fecha, transcripcion_texto,
                    transcripcion_limpia, hash_md5, tokens_original,
                    tokens_limpios, procesada, idioma)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (video_id, titulo, canal, datetime.now().isoformat(timespec="seconds"),
             raw, cleaned["text_limpio"], digest,
             cleaned["tokens_original"], cleaned["tokens_limpio"], idioma),
        )
        conn.execute(
            "UPDATE videos_favoritos SET transcripcion_procesada = 1 WHERE video_id = ?",
            (video_id,),
        )
        conn.commit()
        new_id = cur.lastrowid

    return {
        "duplicado": False, "id": new_id, "video_id": video_id, "titulo": titulo,
        "canal": canal, "hash_md5": digest,
        "tokens_original": cleaned["tokens_original"],
        "tokens_limpio": cleaned["tokens_limpio"],
        "reduccion_pct": cleaned["reduccion_pct"],
        "mensaje": "Transcripción guardada",
    }


def delete_transcript(db_path: str, transcripcion_id: int) -> bool:
    """Borra la transcripción. Si su fuente la creó este módulo y ya no tiene más
    transcripciones, borra también esa fila de video_sources."""
    with _db(db_path) as conn:
        row = conn.execute(
            "SELECT video_id FROM transcripciones_youtube WHERE id = ?",
            (transcripcion_id,),
        ).fetchone()
        if not row:
            return False
        vid = row["video_id"]
        conn.execute("DELETE FROM transcripciones_youtube WHERE id = ?", (transcripcion_id,))
        restantes = conn.execute(
            "SELECT COUNT(*) FROM transcripciones_youtube WHERE video_id = ?", (vid,)
        ).fetchone()[0]
        if restantes == 0:
            conn.execute(
                "DELETE FROM video_sources WHERE video_id = ? AND platform = ?",
                (vid, TRANSCRIPT_PLATFORM),
            )
            conn.execute(
                "UPDATE videos_favoritos SET transcripcion_procesada = 0 WHERE video_id = ?",
                (vid,),
            )
        conn.commit()
    return True


# ── ingesta manual ───────────────────────────────────────────────────────────

def ingest_text(db_path: str, titulo: str, canal: str, texto: str,
                cleaner: Any, idioma: str = "es") -> Dict[str, Any]:
    """Guarda texto pegado a mano (id sintético estable derivado del contenido)."""
    video_id = "manual_" + hash_text((texto or "").strip())[:12]
    return save_transcript(db_path, video_id, titulo, canal or "Manual", texto, cleaner, idioma)


def ingest_url(db_path: str, url: str, cleaner: Any, idioma: str = "es") -> Dict[str, Any]:
    """Descarga los subtítulos de un vídeo de YouTube y los guarda.

    Raises:
        ValueError: URL inválida o vídeo sin subtítulos disponibles.
    """
    from app.services.youtube_rss_fetcher import _run_ytdlp, download_transcript

    video_id = parse_video_id(url)
    if not video_id:
        raise ValueError("URL de YouTube no válida.")

    with _db(db_path) as conn:
        dup = conn.execute(
            "SELECT id FROM transcripciones_youtube WHERE video_id = ?", (video_id,)
        ).fetchone()
    if dup:
        return {"duplicado": True, "id": dup["id"], "video_id": video_id,
                "mensaje": "Transcripción ya guardada"}

    meta = _run_ytdlp(
        ["--skip-download", "--no-warnings", "--print", "%(title)s\t%(channel)s",
         f"https://www.youtube.com/watch?v={video_id}"],
        timeout=60,
    ) or ""
    titulo, _, canal = (meta.strip().splitlines()[0] if meta.strip() else "").partition("\t")
    texto = download_transcript(video_id, lang=idioma)
    if not texto:
        raise ValueError("Este vídeo no tiene subtítulos disponibles.")
    return save_transcript(db_path, video_id, titulo or video_id, canal or "YouTube",
                           texto, cleaner, idioma)


# ── exportación ──────────────────────────────────────────────────────────────

def to_markdown(t: Dict[str, Any], limpia: bool = True) -> str:
    """Documento Markdown de una transcripción (para descargar o copiar)."""
    cuerpo = (t.get("transcripcion_limpia") if limpia else t.get("transcripcion_texto")) or ""
    url = (f"https://www.youtube.com/watch?v={t['video_id']}"
           if _VIDEO_ID_RE.match(t.get("video_id") or "") else "")
    cab = [f"# {t.get('titulo') or '(sin título)'}", "",
           f"- Canal: {t.get('canal') or '—'}",
           f"- Fecha: {(t.get('fecha') or '')[:10] or '—'}",
           f"- Versión: {'texto limpio' if limpia else 'texto original'}"]
    if url:
        cab.append(f"- Vídeo: {url}")
    return "\n".join(cab) + "\n\n" + cuerpo.strip() + "\n"


def safe_filename(titulo: str, ext: str = "md") -> str:
    base = re.sub(r"[^\w\- ]+", "", titulo or "transcripcion", flags=re.UNICODE).strip()
    return (re.sub(r"\s+", "_", base)[:80] or "transcripcion") + f".{ext}"
