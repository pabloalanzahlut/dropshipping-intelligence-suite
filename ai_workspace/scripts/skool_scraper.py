"""
GEM OS — Skool Market Intelligence Scraper
==========================================
Extrae posts de productos ganadores de Comunidad Ecommerce (Adrián Sáenz).
Usa las cookies guardadas por setup_skool_session.py.

Uso:
    python ai_workspace/scripts/skool_scraper.py          # extrae posts nuevos
    python ai_workspace/scripts/skool_scraper.py --reporte # genera reporte mensual
"""

import json
import re
import sys
import argparse
from datetime import datetime, date
from pathlib import Path
from collections import Counter

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    from playwright.sync_api import sync_playwright

# ── Rutas ────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
COOKIES_PATH = Path(__file__).parent / "skool_cookies.json"
KB_PATH = BASE / "knowledge_base" / "skool_productos.json"
HISTORIAL_PATH = BASE / "knowledge_base" / "productos_ganadores_historial.md"

# ── Configuración ─────────────────────────────────────────────────────────────
COMMUNITY_URL = "https://www.skool.com/comunidad-ecommerce"
POST_URL = "https://www.skool.com/comunidad-ecommerce?c=84d2c047f1ce41a5a0fa42c7952169fc&s=newest&fl="

KEYWORDS_GANADOR = [
    "producto ganador", "winning product", "producto del mes", "está petando",
    "está vendiendo", "roas", "conversiones", "cpa", "gané", "resultados",
    "facturé", "€/día", "$/día", "aliexpress", "cjdropshipping", "temu",
    "primera venta", "primer pedido", "recomiendo", "lo probé", "testeé"
]

MULTIPLICADOR_MINIMO = 2.0  # Regla Adrián Sáenz: mínimo 2x coste landed


# ── Helpers ───────────────────────────────────────────────────────────────────

def cargar_cookies() -> list:
    if not COOKIES_PATH.exists():
        print("✗ No hay cookies guardadas.")
        print("  Ejecuta primero: python ai_workspace/scripts/setup_skool_session.py")
        sys.exit(1)
    with open(COOKIES_PATH) as f:
        return json.load(f)


def es_relevante(texto: str) -> bool:
    texto_lower = texto.lower()
    return any(kw in texto_lower for kw in KEYWORDS_GANADOR)


def extraer_precio(texto: str) -> float | None:
    match = re.search(r'[€$]\s*(\d+(?:[.,]\d+)?)', texto)
    if match:
        return float(match.group(1).replace(",", "."))
    return None


def clasificar_gem(precio_venta: float | None, costo: float | None) -> str:
    if not precio_venta or not costo or costo <= 0:
        return "DESCONOCIDO"
    mult = precio_venta / costo
    if mult >= 5:   return "HOT"
    if mult >= 3:   return "WARM"
    if mult >= 2:   return "COLD"
    return "DISCARD"


def extraer_posts_playwright(page, url: str, max_scroll: int = 10) -> list[dict]:
    """Extrae posts de una página de Skool con scroll infinito."""
    page.goto(url, wait_until="networkidle", timeout=30_000)
    page.wait_for_timeout(2000)

    posts = []
    seen_ids = set()

    for _ in range(max_scroll):
        # Extraer posts visibles
        elementos = page.query_selector_all("[data-postid], article, [class*='post']")
        for el in elementos:
            try:
                post_id = el.get_attribute("data-postid") or el.get_attribute("id") or ""
                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                texto = el.inner_text() or ""
                if not es_relevante(texto):
                    continue

                # Intentar extraer autor y fecha
                autor_el = el.query_selector("[class*='author'], [class*='name'], h3, h4")
                autor = autor_el.inner_text().strip() if autor_el else "Desconocido"

                fecha_el = el.query_selector("time, [class*='date'], [class*='time']")
                fecha = fecha_el.get_attribute("datetime") or fecha_el.inner_text() if fecha_el else ""

                # Link al post
                link_el = el.query_selector("a[href*='/comunidad-ecommerce']")
                link = link_el.get_attribute("href") if link_el else ""
                if link and not link.startswith("http"):
                    link = "https://www.skool.com" + link

                precio = extraer_precio(texto)

                posts.append({
                    "id": post_id,
                    "fecha_extraccion": datetime.now().isoformat(),
                    "fecha_post": fecha,
                    "autor": autor,
                    "url": link,
                    "contenido_preview": texto[:500].strip(),
                    "precio_detectado": precio,
                    "clasificacion_gem": "PENDIENTE",
                    "keywords_match": [kw for kw in KEYWORDS_GANADOR if kw in texto.lower()],
                    "engagement": {"likes": 0, "comentarios": 0}
                })
            except Exception:
                continue

        # Scroll para cargar más posts
        prev_height = page.evaluate("document.body.scrollHeight")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000)
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == prev_height:
            break  # No hay más contenido

    return posts


def guardar_kb(nuevos_posts: list[dict]) -> int:
    """Guarda posts nuevos en la KB, evitando duplicados."""
    KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    existentes = []
    if KB_PATH.exists():
        with open(KB_PATH) as f:
            try:
                existentes = json.load(f)
            except json.JSONDecodeError:
                existentes = []

    ids_existentes = {p.get("id", "") or p.get("url", "") for p in existentes}
    nuevos = [p for p in nuevos_posts
              if (p.get("id") or p.get("url")) not in ids_existentes]

    todos = existentes + nuevos
    with open(KB_PATH, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)

    return len(nuevos)


def generar_reporte(mes: str | None = None) -> str:
    """Genera reporte mensual del Dr. Marcus Chen."""
    if not KB_PATH.exists():
        return "KB vacía — ejecuta el scraper primero."

    with open(KB_PATH) as f:
        todos = json.load(f)

    if not todos:
        return "No hay posts en la KB todavía."

    # Filtrar por mes si se especifica
    if mes:
        posts = [p for p in todos if mes.lower() in p.get("fecha_post", "").lower()]
    else:
        posts = todos

    # Análisis
    clasificaciones = Counter(p.get("clasificacion_gem", "PENDIENTE") for p in posts)
    autores = Counter(p.get("autor", "?") for p in posts)
    keywords = Counter()
    for p in posts:
        for kw in p.get("keywords_match", []):
            keywords[kw] += 1

    hoy = date.today().strftime("%B %Y")
    reporte = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 REPORTE SKOOL — {mes or hoy}
   Dr. Marcus Chen | 32 años · GEM OS Intelligence
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📥 POSTS ANALIZADOS: {len(posts)} relevantes de Comunidad Ecommerce

🔥 CLASIFICACIÓN GEM OS:
"""
    for cls, count in clasificaciones.most_common():
        emoji = {"HOT": "🔥", "WARM": "⚡", "COLD": "❄️", "DISCARD": "🗑️"}.get(cls, "❓")
        reporte += f"   {emoji} {cls}: {count} posts\n"

    reporte += f"""
📈 TEMAS MÁS MENCIONADOS:
"""
    for kw, count in keywords.most_common(5):
        reporte += f"   · '{kw}': {count} veces\n"

    reporte += f"""
👥 USUARIOS MÁS ACTIVOS:
"""
    for autor, count in autores.most_common(3):
        reporte += f"   · {autor}: {count} posts relevantes\n"

    # Posts HOT destacados
    hot = [p for p in posts if p.get("clasificacion_gem") == "HOT"]
    if hot:
        reporte += f"\n🏆 PRODUCTOS HOT DETECTADOS:\n"
        for p in hot[:3]:
            reporte += f"   → {p.get('contenido_preview', '')[:120]}...\n"
            reporte += f"      {p.get('url', '')}\n"

    reporte += f"""
🎯 ANÁLISIS DR. MARCUS CHEN:
   Con {len(posts)} posts relevantes este período, la comunidad muestra
   actividad {'alta' if len(posts) > 20 else 'moderada' if len(posts) > 5 else 'baja'}.
   Los temas dominantes sugieren {'oportunidades activas' if keywords.get('roas', 0) > 2 else 'exploración de nuevos productos'}.
   Recomendación: priorizar posts con evidencia real de ventas (ROAS + capturas).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return reporte


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GEM OS — Skool Scraper")
    parser.add_argument("--reporte", action="store_true", help="Genera reporte mensual")
    parser.add_argument("--mes", help="Mes para el reporte (ej: 'noviembre')")
    parser.add_argument("--scroll", type=int, default=8, help="Veces a hacer scroll (default: 8)")
    args = parser.parse_args()

    if args.reporte:
        print(generar_reporte(args.mes))
        return

    print("🔍 GEM OS — Skool Market Intelligence")
    print("   Agente: Dr. Marcus Chen | 32 años de experiencia")
    print("=" * 50)

    cookies = cargar_cookies()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        # Cargar cookies de sesión guardadas
        context.add_cookies(cookies)
        page = context.new_page()

        print(f"📡 Accediendo a Skool con sesión guardada...")
        posts = extraer_posts_playwright(page, POST_URL, max_scroll=args.scroll)
        browser.close()

    print(f"✅ Posts relevantes encontrados: {len(posts)}")
    nuevos = guardar_kb(posts)
    print(f"📥 Nuevos en KB: {nuevos}")

    if nuevos > 0:
        print(f"\n🎯 {nuevos} posts nuevos guardados en:")
        print(f"   {KB_PATH}")

    # Reporte rápido
    if posts:
        print(f"\n--- Vista previa ---")
        for p in posts[:3]:
            print(f"  · {p['contenido_preview'][:100]}...")


if __name__ == "__main__":
    main()
