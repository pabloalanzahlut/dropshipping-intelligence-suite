"""
GEM OS — Skool Session Setup
=============================
Ejecutar UNA SOLA VEZ para guardar tu sesión de Skool.

Uso:
    python ai_workspace/scripts/setup_skool_session.py

Qué hace:
    1. Abre Chrome con una ventana REAL (tú ves la pantalla)
    2. Navega a Skool → tú te logueas manualmente
    3. Detecta cuando ya estás dentro
    4. Guarda las cookies en skool_cookies.json
    5. Las próximas ejecuciones del scraper usan esas cookies (sin pedir login)
"""

import json
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Instalando playwright...")
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    from playwright.sync_api import sync_playwright

COOKIES_PATH = Path(__file__).parent / "skool_cookies.json"
COMMUNITY_URL = "https://www.skool.com/comunidad-ecommerce"


def setup_session():
    print("=" * 55)
    print("  GEM OS — Configuración de sesión Skool")
    print("  Agente: Dr. Marcus Chen | Market Intelligence")
    print("=" * 55)
    print()
    print("Se abrirá una ventana de Chrome.")
    print("→ Haz login en Skool con tu cuenta")
    print("→ Una vez dentro de la comunidad, cierra la ventana")
    print()
    input("Presiona ENTER para abrir el navegador...")

    with sync_playwright() as p:
        # Abre navegador VISIBLE (no headless) para que el usuario se loguee
        browser = p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto(COMMUNITY_URL)

        print()
        print("✓ Navegador abierto. Haz login en Skool.")
        print("  Esperando que entres a la comunidad...")
        print("  (Cierra la ventana del navegador cuando estés dentro)")
        print()

        # Esperar hasta que el usuario esté dentro (URL cambia de /about a otro path)
        # o hasta que cierre el navegador
        try:
            # Esperar máximo 5 minutos a que el usuario se loguee
            page.wait_for_url(
                lambda url: "skool.com/comunidad-ecommerce" in url and "/about" not in url,
                timeout=300_000
            )
            print("✓ Login detectado. Guardando cookies...")
        except Exception:
            # Si no detecta cambio de URL, igual intenta guardar lo que hay
            print("⚠ Tiempo agotado o URL no cambió. Guardando cookies actuales...")

        # Dar 2 segundos para que cargue bien
        time.sleep(2)

        cookies = context.cookies()
        browser.close()

    if not cookies:
        print("✗ No se encontraron cookies. ¿Completaste el login?")
        return False

    # Guardar cookies
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)

    print(f"✓ {len(cookies)} cookies guardadas en:")
    print(f"  {COOKIES_PATH}")
    print()
    print("🎯 Listo. Ahora puedes ejecutar el scraper automático:")
    print("   python ai_workspace/scripts/skool_scraper.py")
    return True


if __name__ == "__main__":
    setup_session()
