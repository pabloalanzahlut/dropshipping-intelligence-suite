"""
seed_favoritos.py — Inicializa videos, playlist y metadatos extendidos en GEM OS.

Uso:
    cd H:\\dropshipping_intelligence_suite
    python scripts/seed_favoritos.py
"""

import sys
import os
import json
import sqlite3

# Asegurar que el root del proyecto esté en sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.database.connection import DatabaseConnection

DB = DatabaseConnection()


def _conn() -> sqlite3.Connection:
    return DB.get_connection()


def seed_videos_favoritos():
    videos = [
        ("4j7Vi60WUrU",
         "Tutorial Completo De TikTok Ads Para Principiantes (2026)",
         "Adrián Sáenz",
         "https://www.youtube.com/watch?v=4j7Vi60WUrU",
         "Tutorial ads TikTok 2026",
         "tiktok,ads,principiantes"),
        ("AsHQy6lAiig",
         "Curso Gratis De Google Ads Para Principiantes (2026)",
         "Adrián Sáenz",
         "https://www.youtube.com/watch?v=AsHQy6lAiig",
         "Curso Google Ads gratuito 2026",
         "google-ads,principiantes"),
        ("FgWCRB0YWPk",
         "CÓMO VENDER USANDO FACEBOOK ADS | 4 Errores Al Hacer Dropshipping con Shopify",
         "Adrián Sáenz",
         "https://www.youtube.com/watch?v=FgWCRB0YWPk",
         "Errores clave Facebook Ads + Shopify",
         "facebook-ads,shopify,errores"),
    ]
    insertados = 0
    with _conn() as conn:
        for video_id, titulo, canal, url, razon, tags in videos:
            cur = conn.execute(
                "INSERT OR IGNORE INTO videos_favoritos (video_id, titulo, canal, url, razon, tags) VALUES (?,?,?,?,?,?)",
                (video_id, titulo, canal, url, razon, tags)
            )
            if cur.rowcount:
                insertados += 1
                print(f"  [+] Video: {titulo[:60]}")
            else:
                print(f"  [=] Ya existe: {titulo[:60]}")
    print(f"  → {insertados} videos nuevos / {len(videos) - insertados} ya existían\n")


def seed_playlists():
    playlists = [
        ("PLrs1PAk24jHeU8waSkHzgQTHmduOk9xMn",
         "DROPSHIPPING - NEGOCIO 2",
         "Personal",
         "https://www.youtube.com/playlist?list=PLrs1PAk24jHeU8waSkHzgQTHmduOk9xMn",
         True,
         "dropshipping,shopify,personal"),
    ]
    insertadas = 0
    with _conn() as conn:
        for playlist_id, titulo, canal, url, es_privada, tags in playlists:
            cur = conn.execute(
                "INSERT OR IGNORE INTO playlists_favoritas (playlist_id, titulo, canal, url, es_privada, tags) VALUES (?,?,?,?,?,?)",
                (playlist_id, titulo, canal, url, int(es_privada), tags)
            )
            if cur.rowcount:
                insertadas += 1
                print(f"  [+] Playlist: {titulo}")
            else:
                print(f"  [=] Ya existe: {titulo}")
    print(f"  → {insertadas} playlists nuevas\n")


def seed_canales_favoritos():
    canales = [
        ("@adriansaenz",   "Adrián Sáenz",   "https://www.youtube.com/@adriansaenz",   "es", "general", "shopify,ads,dropshipping", 1),
        ("@ivancaicedo",   "Iván Caicedo",   "https://www.youtube.com/@ivancaicedo",   "es", "general", "dropshipping,productos",   2),
        ("@javiecom",      "JaviEcom",       "https://www.youtube.com/@javiecom",      "es", "general", "shopify,ecom",             2),
        ("@marcverdu",     "Marc Verdú",     "https://www.youtube.com/@marcverdu",     "es", "general", "shopify,productos",        3),
        ("@vicecomilions", "Vic Ecomilions", "https://www.youtube.com/@vicecomilions", "es", "general", "dropshipping,scaling",     3),
    ]
    insertados = 0
    with _conn() as conn:
        for handle, nombre, url, idioma, especialidad, tags, prioridad in canales:
            cur = conn.execute(
                "INSERT OR IGNORE INTO canales_favoritos (handle, nombre, url, idioma, especialidad, tags, prioridad) VALUES (?,?,?,?,?,?,?)",
                (handle, nombre, url, idioma, especialidad, tags, prioridad)
            )
            if cur.rowcount:
                insertados += 1
                print(f"  [+] Canal: {nombre}")
            else:
                print(f"  [=] Ya existe: {nombre}")
    print(f"  → {insertados} canales nuevos / {len(canales) - insertados} ya existían\n")


def verify_resumen():
    with _conn() as conn:
        try:
            rows = conn.execute("SELECT nombre, handle, tags, prioridad, videos_descargados FROM v_resumen_canales ORDER BY prioridad").fetchall()
            print("  Vista v_resumen_canales:")
            print(f"  {'Canal':<20} {'Handle':<18} {'Tags':<30} {'Prio':>4} {'Videos':>6}")
            print("  " + "-" * 82)
            for r in rows:
                print(f"  {r[0]:<20} {r[1]:<18} {r[2]:<30} {r[3]:>4} {r[4]:>6}")
        except Exception as e:
            print(f"  [WARN] Vista no disponible: {e}")


if __name__ == "__main__":
    print("\n=== GEM OS — Seed Favoritos ===\n")

    print("[1] Canales favoritos:")
    seed_canales_favoritos()

    print("[2] Videos favoritos:")
    seed_videos_favoritos()

    print("[3] Playlists favoritas:")
    seed_playlists()

    print("[4] Verificación:")
    verify_resumen()

    print("\n✓ Seed completado.\n")
