"""
import_playlist.py — Extrae todos los videos de la playlist personal del usuario,
detecta canales únicos de dropshipping/Shopify y los registra en la DB sin duplicar.

Uso:
    cd H:\\dropshipping_intelligence_suite
    python scripts/import_playlist.py
"""

import sys
import os
import json
import sqlite3
import subprocess
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.database.connection import DatabaseConnection

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLrs1PAk24jHeU8waSkHzgQTHmduOk9xMn"

# Handles alternativos que deben fusionarse con el handle canónico
# clave = handle de la playlist  →  valor = handle canónico ya en DB
HANDLE_ALIASES = {
    "@soyivancaicedo": "@soyivancaicedo",   # ya canónico (el canal real es @soyivancaicedo)
    "@javiecomm":      "@javiecom",
    "@ecomilions":     "@ecomilions",   # ya canónico (el canal real es @ecomilions)
    "@marcverdu":      "@marcverdu",   # ya canónico, solo por claridad
    "@adriansaenz":    "@adriansaenz",
}

# Palabras clave para clasificar contenido de dropshipping/Shopify
KEYWORDS_DS_SHOPIFY = [
    "dropshipping", "shopify", "drop shipping", "ecommerce", "e-commerce",
    "tienda online", "online store", "product research", "winning product",
    "producto ganador", "producto ganador", "fulfillment", "aliexpress",
    "dsers", "autods", "oberlo", "vender online", "venta online",
    "negocio online", "online business", "tiktok shop", "facebook ads",
    "google ads", "tiktok ads", "meta ads", "advertising", "publicidad",
    "conversiones", "conversion", "revenue", "ventas", "scaling",
    "supplier", "proveedor", "niche", "nicho", "trending product",
    "producto tendencia", "print on demand", "pod", "wholesale",
]

# Palabras clave para idioma
TAGS_ES = ["es", "español", "spanish", "habla hispana"]


def es_relevante(titulo: str, canal: str) -> bool:
    t = titulo.lower()
    for kw in KEYWORDS_DS_SHOPIFY:
        if kw in t:
            return True
    return False


def detectar_idioma(canal: str, titulo: str) -> str:
    texto = (canal + " " + titulo).lower()
    # Heurística: si tiene caracteres españoles o palabras clave ES
    if any(c in texto for c in "áéíóúñ¿¡"):
        return "es"
    # Canales conocidos en español
    canales_es = ["adrián", "adrian", "iván", "ivan", "javi", "marc", "vic",
                  "pablo", "zahlut", "caicedo"]
    if any(c in texto for c in canales_es):
        return "es"
    return "en"


def inferir_tags(titulo: str) -> str:
    t = titulo.lower()
    tags = []
    if "shopify" in t:
        tags.append("shopify")
    if "dropshipping" in t or "drop shipping" in t:
        tags.append("dropshipping")
    if "tiktok" in t:
        tags.append("tiktok")
    if "facebook" in t or "meta ads" in t:
        tags.append("facebook-ads")
    if "google ads" in t:
        tags.append("google-ads")
    if "product" in t or "producto" in t:
        tags.append("productos")
    if "ads" in t or "advertising" in t or "publicidad" in t:
        tags.append("ads")
    if "scaling" in t or "scale" in t or "escal" in t:
        tags.append("scaling")
    return ",".join(tags) if tags else "dropshipping"


def fetch_playlist():
    """Llama yt-dlp y retorna lista de dicts con los videos."""
    print(f"[→] Extrayendo playlist ({PLAYLIST_URL})...")
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        PLAYLIST_URL,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    videos = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            videos.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    print(f"[✓] {len(videos)} videos extraídos de la playlist.\n")
    return videos


def insertar_canales(conn: sqlite3.Connection, canales: dict) -> tuple:
    """Inserta canales nuevos en canales_favoritos. Retorna (nuevos, existentes)."""
    nuevos = 0
    existentes = 0
    for handle, data in canales.items():
        cur = conn.execute(
            """INSERT OR IGNORE INTO canales_favoritos
               (handle, nombre, url, idioma, especialidad, tags, prioridad, notas)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                handle,
                data["nombre"],
                data["url"],
                data["idioma"],
                "general",
                data["tags"],
                5,
                f"Importado desde playlist DROPSHIPPING - NEGOCIO 2 ({data['video_count']} videos)"
            )
        )
        if cur.rowcount:
            nuevos += 1
            print(f"  [+] Canal: {data['nombre']} ({handle})")
        else:
            existentes += 1
    return nuevos, existentes


def insertar_videos(conn: sqlite3.Connection, videos: list) -> tuple:
    """Inserta videos en videos_favoritos. Retorna (nuevos, existentes)."""
    nuevos = 0
    existentes = 0
    for v in videos:
        tags = inferir_tags(v["title"])
        url = f"https://www.youtube.com/watch?v={v['id']}"
        cur = conn.execute(
            """INSERT OR IGNORE INTO videos_favoritos
               (video_id, titulo, canal, url, razon, tags)
               VALUES (?,?,?,?,?,?)""",
            (
                v["id"],
                v["title"],
                v["channel"],
                url,
                "Playlist: DROPSHIPPING - NEGOCIO 2",
                tags,
            )
        )
        if cur.rowcount:
            nuevos += 1
        else:
            existentes += 1
    return nuevos, existentes


def main():
    print("\n=== GEM OS — Importar Playlist ===\n")

    videos_raw = fetch_playlist()

    if not videos_raw:
        print("[ERROR] No se obtuvieron videos. Abortando.")
        sys.exit(1)

    # --- Separar canales únicos ---
    canales_unicos = {}     # handle → {nombre, url, idioma, tags, video_count}
    videos_relevantes = []  # videos que hablan de dropshipping/shopify

    for v in videos_raw:
        handle   = (v.get("uploader_id") or "").lower()
        nombre   = v.get("channel") or v.get("uploader") or "Desconocido"
        ch_url   = v.get("uploader_url") or v.get("channel_url") or ""
        titulo   = v.get("title") or ""
        video_id = v.get("id") or ""

        if not handle or not video_id:
            continue

        idioma = detectar_idioma(nombre, titulo)
        tags   = inferir_tags(titulo)

        # Acumular canal
        # Normalizar handle: si es un alias conocido, usar el canónico
        handle = HANDLE_ALIASES.get(handle, handle)

        if handle not in canales_unicos:
            canales_unicos[handle] = {
                "nombre": nombre,
                "url": ch_url,
                "idioma": idioma,
                "tags": tags,
                "video_count": 0,
            }
        canales_unicos[handle]["video_count"] += 1

        # Filtrar solo dropshipping/Shopify para videos
        if es_relevante(titulo, nombre):
            videos_relevantes.append(v)

    print(f"[→] Canales únicos encontrados: {len(canales_unicos)}")
    print(f"[→] Videos relevantes (dropshipping/Shopify): {len(videos_relevantes)}\n")

    # --- Insertar en DB ---
    db = DatabaseConnection()
    with db.get_connection() as conn:
        print("[1] Insertando canales únicos:")
        c_nuevos, c_exist = insertar_canales(conn, canales_unicos)
        conn.commit()
        print(f"\n  → {c_nuevos} canales nuevos / {c_exist} ya existían\n")

        print("[2] Insertando videos relevantes:")
        v_nuevos, v_exist = insertar_videos(conn, videos_relevantes)
        conn.commit()
        print(f"  → {v_nuevos} videos nuevos / {v_exist} ya existían\n")

        # --- Actualizar playlist con conteo real ---
        conn.execute(
            "UPDATE playlists_favoritas SET video_count=? WHERE playlist_id=?",
            (len(videos_raw), "PLrs1PAk24jHeU8waSkHzgQTHmduOk9xMn")
        )
        conn.commit()

        # --- Resumen final ---
        print("=== RESUMEN ===")
        total_canales = conn.execute("SELECT COUNT(*) FROM canales_favoritos").fetchone()[0]
        total_videos  = conn.execute("SELECT COUNT(*) FROM videos_favoritos").fetchone()[0]
        print(f"  canales_favoritos : {total_canales} registros totales")
        print(f"  videos_favoritos  : {total_videos} registros totales")

        print("\n  Top canales por volumen en la playlist:")
        tops = sorted(canales_unicos.items(), key=lambda x: x[1]["video_count"], reverse=True)[:15]
        for handle, data in tops:
            print(f"    {data['nombre']:<28} {handle:<25} {data['video_count']:>3} videos  [{data['idioma']}]")

    print("\n✓ Importación completada.\n")


if __name__ == "__main__":
    main()
