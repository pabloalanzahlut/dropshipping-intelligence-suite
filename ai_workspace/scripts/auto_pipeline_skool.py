"""
GEM OS — Pipeline Automático Skool (100% sin intervención)
===========================================================
Ejecuta el ciclo completo:
  1. Login automático con credenciales de .env (refresca cookies)
  2. Scraping de posts relevantes
  3. Análisis Dr. Marcus Chen (HOT/WARM/COLD)
  4. Actualización de Knowledge Base
  5. Reporte a Google Sheets

Uso:
    python ai_workspace/scripts/auto_pipeline_skool.py
    python ai_workspace/scripts/auto_pipeline_skool.py --solo-reporte
    python ai_workspace/scripts/auto_pipeline_skool.py --forzar-login
"""

import json
import os
import re
import sys
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

# ── Setup paths ───────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent.parent  # H:/dropshipping_intelligence_suite
SCRIPTS_DIR = Path(__file__).parent
ENV_PATH = ROOT / ".env"
COOKIES_PATH = SCRIPTS_DIR / "skool_cookies.json"
KB_PATH = ROOT / "ai_workspace" / "knowledge_base" / "skool_productos.json"
LOG_PATH = ROOT / "ai_workspace" / "knowledge_base" / "skool_sync.log"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False))
    ]
)
log = logging.getLogger("GEM_SKOOL")

# ── Dependencias ─────────────────────────────────────────────────────────────
def instalar_deps():
    import subprocess
    deps = ["playwright", "python-dotenv"]
    for dep in deps:
        try:
            __import__(dep.replace("-", "_"))
        except ImportError:
            log.info(f"Instalando {dep}...")
            subprocess.run([sys.executable, "-m", "pip", "install", dep, "-q"], check=True)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.executable_path  # verifica que existe
    except Exception:
        log.info("Instalando navegador Chromium...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"], check=True)

instalar_deps()

from dotenv import load_dotenv
load_dotenv(ENV_PATH)
from playwright.sync_api import sync_playwright

# ── Configuración ─────────────────────────────────────────────────────────────
COMMUNITY_URL  = "https://www.skool.com/comunidad-ecommerce"
POST_FEED_URL  = "https://www.skool.com/comunidad-ecommerce?s=newest"
SKOOL_EMAIL    = os.getenv("SKOOL_EMAIL", "")
SKOOL_PASSWORD = os.getenv("SKOOL_PASSWORD", "")
SHEETS_ID      = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
COOKIES_MAX_AGE_HOURS = 20  # Refresca cookies si tienen más de 20h

KEYWORDS = [
    "producto ganador", "winning product", "producto del mes", "está petando",
    "está vendiendo", "roas", "conversiones", "cpa", "resultados reales",
    "facturé", "€/día", "$/día", "aliexpress", "cjdropshipping", "temu",
    "primera venta", "primer pedido", "recomiendo este", "lo probé", "testeé",
    "está funcionando", "escalé", "desactivé", "maté el anuncio", "ganador"
]

# ── PASO 1: Login automático ──────────────────────────────────────────────────

def cookies_vigentes() -> bool:
    """Verifica si las cookies guardadas son recientes."""
    if not COOKIES_PATH.exists():
        return False
    mtime = datetime.fromtimestamp(COOKIES_PATH.stat().st_mtime)
    edad = datetime.now() - mtime
    return edad < timedelta(hours=COOKIES_MAX_AGE_HOURS)


def login_automatico(page) -> bool:
    """Login headless con credenciales de .env."""
    if not SKOOL_EMAIL or not SKOOL_PASSWORD:
        log.warning("SKOOL_EMAIL / SKOOL_PASSWORD no configurados en .env — usando cookies existentes")
        return False

    log.info(f"Iniciando login automático como {SKOOL_EMAIL}...")
    page.goto("https://www.skool.com/login", wait_until="networkidle", timeout=20_000)
    page.wait_for_timeout(1500)

    try:
        # Rellenar email
        email_input = page.locator("input[type='email'], input[name='email'], input[placeholder*='mail']").first
        email_input.fill(SKOOL_EMAIL)
        page.wait_for_timeout(500)

        # Rellenar password
        pass_input = page.locator("input[type='password']").first
        pass_input.fill(SKOOL_PASSWORD)
        page.wait_for_timeout(500)

        # Enviar
        btn = page.locator("button[type='submit'], button:has-text('Accedi'), button:has-text('Sign in'), button:has-text('Log in')").first
        btn.click()
        page.wait_for_timeout(3000)

        # Verificar login exitoso
        if "login" not in page.url and "error" not in page.content().lower()[:200]:
            log.info("✓ Login exitoso")
            return True
        else:
            log.warning("Login fallido — verificar credenciales en .env")
            return False
    except Exception as e:
        log.warning(f"Error en login: {e}")
        return False


def guardar_cookies(context):
    cookies = context.cookies()
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)
    log.info(f"OK: {len(cookies)} cookies guardadas")


def cargar_cookies(context):
    if not COOKIES_PATH.exists():
        return False
    with open(COOKIES_PATH) as f:
        cookies = json.load(f)
    if cookies:
        context.add_cookies(cookies)
        log.info(f"OK: {len(cookies)} cookies cargadas")
        return True
    return False


# ── PASO 2: Scraping ──────────────────────────────────────────────────────────

def es_relevante(texto: str) -> bool:
    t = texto.lower()
    return any(kw in t for kw in KEYWORDS)


def extraer_precio(texto: str) -> float | None:
    m = re.search(r'[€$]\s*(\d+(?:[.,]\d+)?)', texto)
    return float(m.group(1).replace(",", ".")) if m else None


def extraer_link_proveedor(texto: str) -> str:
    for proveedor in ["aliexpress.com", "cjdropshipping.com", "temu.com", "amazon.com"]:
        m = re.search(rf'https?://[^\s]*{re.escape(proveedor)}[^\s]*', texto)
        if m:
            return m.group(0)
    return ""


def clasificar_gem(texto: str, precio: float | None) -> str:
    """Clasificación Dr. Marcus Chen con señales cualitativas y cuantitativas."""
    texto_l = texto.lower()
    score = 0

    # Señales de alta conversión
    if any(kw in texto_l for kw in ["roas", "conversiones", "facturé", "escalé"]):
        score += 3
    if any(kw in texto_l for kw in ["€/día", "$/día", "resultados reales"]):
        score += 2
    if any(kw in texto_l for kw in ["ganador", "está petando", "está vendiendo"]):
        score += 2
    if precio and precio > 30:
        score += 1  # ticket alto = mejor margen potencial

    if score >= 6: return "HOT"
    if score >= 3: return "WARM"
    if score >= 1: return "COLD"
    return "PENDIENTE"


def scrape_posts(page, max_scroll: int = 10) -> list[dict]:
    log.info(f"Scrapeando {POST_FEED_URL}...")
    page.goto(POST_FEED_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(3000)

    posts = []
    seen = set()

    for i in range(max_scroll):
        # Capturar contenido de posts visibles
        raw_posts = page.evaluate("""
            () => {
                const posts = [];
                // Skool usa divs con clases dinámicas — capturamos por estructura
                document.querySelectorAll('[data-postid], [class*="PostCard"], [class*="post-card"]').forEach(el => {
                    const id = el.getAttribute('data-postid') || el.id || '';
                    const text = el.innerText || '';
                    const link = el.querySelector('a[href*="/comunidad-ecommerce/p/"]');
                    const timeEl = el.querySelector('time');
                    posts.push({
                        id: id,
                        texto: text.substring(0, 800),
                        url: link ? 'https://www.skool.com' + link.getAttribute('href') : '',
                        fecha: timeEl ? (timeEl.getAttribute('datetime') || timeEl.innerText) : ''
                    });
                });
                // Fallback: capturar cualquier bloque grande de texto
                if (posts.length === 0) {
                    document.querySelectorAll('article, [role="article"]').forEach(el => {
                        posts.push({
                            id: el.id || Math.random().toString(36).slice(2),
                            texto: (el.innerText || '').substring(0, 800),
                            url: '',
                            fecha: ''
                        });
                    });
                }
                return posts;
            }
        """)

        for rp in (raw_posts or []):
            uid = rp.get("id") or rp.get("url") or rp.get("texto", "")[:50]
            if uid in seen or not rp.get("texto"):
                continue
            if not es_relevante(rp["texto"]):
                continue
            seen.add(uid)

            precio = extraer_precio(rp["texto"])
            posts.append({
                "id": uid,
                "fecha_extraccion": datetime.now().isoformat(),
                "fecha_post": rp.get("fecha", ""),
                "url": rp.get("url", ""),
                "contenido_preview": rp["texto"][:500].strip(),
                "precio_detectado": precio,
                "link_proveedor": extraer_link_proveedor(rp["texto"]),
                "clasificacion_gem": clasificar_gem(rp["texto"], precio),
                "keywords_match": [kw for kw in KEYWORDS if kw in rp["texto"].lower()],
            })

        # Scroll para más posts
        prev_h = page.evaluate("document.documentElement.scrollHeight")
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        page.wait_for_timeout(2000)
        new_h = page.evaluate("document.documentElement.scrollHeight")
        if new_h == prev_h:
            log.info(f"Sin más contenido tras {i+1} scrolls")
            break

    log.info(f"OK: {len(posts)} posts relevantes extraídos")
    return posts


# ── PASO 3: Knowledge Base ────────────────────────────────────────────────────

def actualizar_kb(posts: list[dict]) -> int:
    KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    existentes = []
    if KB_PATH.exists():
        try:
            with open(KB_PATH) as f:
                existentes = json.load(f)
        except Exception:
            existentes = []

    ids_existentes = {p.get("id", "") or p.get("url", "") for p in existentes}
    nuevos = [p for p in posts if (p.get("id") or p.get("url", "")[:50]) not in ids_existentes]

    with open(KB_PATH, "w", encoding="utf-8") as f:
        json.dump(existentes + nuevos, f, ensure_ascii=False, indent=2)

    log.info(f"KB actualizada: +{len(nuevos)} nuevos | {len(existentes)+len(nuevos)} total")
    return len(nuevos)


# ── PASO 4: Reporte Dr. Marcus Chen ──────────────────────────────────────────

def generar_reporte(posts_nuevos: list[dict], total_kb: int) -> str:
    clasificaciones = Counter(p["clasificacion_gem"] for p in posts_nuevos)
    keywords_top = Counter()
    for p in posts_nuevos:
        keywords_top.update(p.get("keywords_match", []))

    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    lineas = [
        "",
        "━" * 50,
        f"📊 REPORTE SKOOL — {hoy}",
        "   Dr. Marcus Chen | GEM OS Intelligence",
        "━" * 50,
        f"",
        f"📥 Nuevos posts relevantes: {len(posts_nuevos)}",
        f"📚 Total en Knowledge Base: {total_kb}",
        f"",
        "🏷️  CLASIFICACIÓN:",
    ]
    for cls, n in [("HOT","🔥"), ("WARM","⚡"), ("COLD","❄️"), ("PENDIENTE","❓")]:
        c = clasificaciones.get(cls, 0)
        if c:
            lineas.append(f"   {n} {cls}: {c}")

    if keywords_top:
        lineas += ["", "📌 SEÑALES MÁS FRECUENTES:"]
        for kw, c in keywords_top.most_common(5):
            lineas.append(f"   · '{kw}' × {c}")

    hot = [p for p in posts_nuevos if p["clasificacion_gem"] == "HOT"]
    if hot:
        lineas += ["", "🏆 POSTS HOT PARA REVISAR:"]
        for p in hot[:3]:
            lineas.append(f"   → {p['contenido_preview'][:100]}...")
            if p.get("url"):
                lineas.append(f"      {p['url']}")

    lineas += ["", "━" * 50, ""]
    return "\n".join(lineas)


# ── PASO 5: Google Sheets ─────────────────────────────────────────────────────

def actualizar_sheets(posts_nuevos: list[dict]):
    """Escribe filas nuevas en Google Sheets si está configurado."""
    if not SHEETS_ID:
        log.info("Google Sheets no configurado — omitiendo")
        return
    try:
        import subprocess
        # Llama al script de actualización de Sheets si existe
        sheets_script = ROOT / "ai_workspace" / "scripts" / "actualizar_sheets_skool.py"
        if sheets_script.exists():
            subprocess.run([sys.executable, str(sheets_script)], check=True)
            log.info("✓ Google Sheets actualizado")
    except Exception as e:
        log.warning(f"Sheets: {e}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--solo-reporte", action="store_true")
    parser.add_argument("--forzar-login", action="store_true")
    parser.add_argument("--scroll", type=int, default=8)
    args = parser.parse_args()

    log.info("=" * 50)
    log.info("GEM OS — Pipeline Automático Skool")
    log.info("=" * 50)

    if args.solo_reporte:
        if KB_PATH.exists():
            with open(KB_PATH) as f:
                todos = json.load(f)
            print(generar_reporte(todos[-20:], len(todos)))
        else:
            print("KB vacía — ejecuta sin --solo-reporte primero")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120"
        )
        page = context.new_page()

        # Login o cargar cookies
        necesita_login = args.forzar_login or not cookies_vigentes()
        if necesita_login and SKOOL_EMAIL and SKOOL_PASSWORD:
            ok = login_automatico(page)
            if ok:
                guardar_cookies(context)
        else:
            cargar_cookies(context)

        # Scraping
        posts = scrape_posts(page, max_scroll=args.scroll)
        browser.close()

    # KB + reporte
    nuevos = actualizar_kb(posts)
    with open(KB_PATH) as f:
        total = len(json.load(f))

    reporte = generar_reporte(posts, total)
    print(reporte)

    # Google Sheets
    if nuevos > 0:
        actualizar_sheets(posts)

    log.info(f"Pipeline completado. +{nuevos} posts nuevos.")


if __name__ == "__main__":
    main()
