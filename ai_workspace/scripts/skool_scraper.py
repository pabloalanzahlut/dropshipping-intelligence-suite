"""
Skool Community Scraper — GEM OS v2.2
Extrae posts de productos ganadores de Comunidad Ecommerce (Adrián Sáenz)
Requiere cookies de sesión activas de Skool.

Uso:
  python skool_scraper.py --cookies cookies.json --output productos.json
  python skool_scraper.py --cookies cookies.json --post-url "https://..."
"""

import json
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Instala dependencias: pip install requests beautifulsoup4")
    sys.exit(1)

SKOOL_BASE = "https://www.skool.com"
COMMUNITY = "comunidad-ecommerce"
KB_PATH = Path(__file__).parent.parent / "knowledge_base" / "skool_productos.json"
HISTORIAL_PATH = Path(__file__).parent.parent / "knowledge_base" / "productos_ganadores_historial.md"

KEYWORDS_GANADOR = [
    "producto ganador", "winning product", "producto del mes",
    "roas", "conversiones", "está vendiendo", "está petando",
    "cpa", "aliexpress", "cj dropshipping", "temu", "€/día", "$/día"
]

PESO_MAXIMO_KG = 1.2
MULTIPLICADOR_MINIMO = 3.0


def cargar_cookies(ruta: str) -> dict:
    """Carga cookies desde archivo JSON (exportado con extensión EditThisCookie)."""
    with open(ruta) as f:
        cookies_lista = json.load(f)
    return {c["name"]: c["value"] for c in cookies_lista}


def construir_session(cookies: dict) -> requests.Session:
    s = requests.Session()
    s.cookies.update(cookies)
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": SKOOL_BASE,
    })
    return s


def extraer_precio(texto: str) -> float | None:
    """Extrae primer precio mencionado en texto (€ o $)."""
    match = re.search(r'[€$]\s*(\d+(?:[.,]\d+)?)', texto)
    if match:
        return float(match.group(1).replace(",", "."))
    return None


def es_post_relevante(titulo: str, contenido: str) -> bool:
    texto = (titulo + " " + contenido).lower()
    return any(kw in texto for kw in KEYWORDS_GANADOR)


def validar_regla_3x(precio_venta: float, costo: float) -> dict:
    if costo <= 0:
        return {"valida": False, "razon": "Costo desconocido"}
    multiplicador = precio_venta / costo
    margen = (precio_venta - costo) / precio_venta * 100
    return {
        "valida": multiplicador >= MULTIPLICADOR_MINIMO and margen >= 70,
        "multiplicador": round(multiplicador, 2),
        "margen_bruto": round(margen, 1),
        "clasificacion": "HOT" if multiplicador >= 5 else "WARM" if multiplicador >= 3 else "COLD"
    }


def parsear_post(html_post: str, url: str) -> dict:
    soup = BeautifulSoup(html_post, "html.parser")
    titulo = soup.find("h1") or soup.find("h2")
    titulo_texto = titulo.get_text(strip=True) if titulo else ""

    cuerpo = soup.find("div", class_=re.compile(r"post|content|body", re.I))
    contenido = cuerpo.get_text(" ", strip=True) if cuerpo else ""

    precio_venta = extraer_precio(contenido)

    # Buscar links de proveedores
    links = soup.find_all("a", href=True)
    link_proveedor = next(
        (a["href"] for a in links if any(
            p in a["href"] for p in ["aliexpress", "cjdropshipping", "temu", "amazon"]
        )), ""
    )

    return {
        "fecha_extraccion": datetime.now().isoformat(),
        "url": url,
        "titulo": titulo_texto,
        "contenido_preview": contenido[:300],
        "precio_venta_detectado": precio_venta,
        "link_proveedor": link_proveedor,
        "relevante": es_post_relevante(titulo_texto, contenido),
    }


def obtener_posts_comunidad(session: requests.Session, paginas: int = 3) -> list[dict]:
    """Obtiene posts recientes de la comunidad."""
    posts = []
    for pagina in range(1, paginas + 1):
        url = f"{SKOOL_BASE}/{COMMUNITY}?s=newest&p={pagina}"
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"Error {resp.status_code} en página {pagina}")
            break
        soup = BeautifulSoup(resp.text, "html.parser")

        # Skool renderiza con JS — si el contenido está vacío, se necesita Playwright
        articulos = soup.find_all("article") or soup.find_all("div", class_=re.compile(r"post", re.I))
        for art in articulos:
            enlace = art.find("a", href=True)
            if enlace:
                posts.append({"url": SKOOL_BASE + enlace["href"], "html": str(art)})
    return posts


def guardar_kb(productos: list[dict]):
    KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    existentes = []
    if KB_PATH.exists():
        with open(KB_PATH) as f:
            existentes = json.load(f)

    urls_existentes = {p["url"] for p in existentes}
    nuevos = [p for p in productos if p.get("url") not in urls_existentes]

    todos = existentes + nuevos
    with open(KB_PATH, "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)

    print(f"✅ KB actualizada: {len(nuevos)} nuevos posts | {len(todos)} total")
    return nuevos


def main():
    parser = argparse.ArgumentParser(description="Skool Scraper — GEM OS")
    parser.add_argument("--cookies", required=True, help="Ruta al archivo cookies.json")
    parser.add_argument("--post-url", help="URL de un post específico a analizar")
    parser.add_argument("--output", default=str(KB_PATH), help="Ruta de salida JSON")
    parser.add_argument("--paginas", type=int, default=3, help="Páginas a escanear")
    args = parser.parse_args()

    print("🔍 GEM OS — Skool Market Intelligence")
    print("   Agente: Dr. Marcus Chen | 32 años de experiencia")
    print("=" * 50)

    cookies = cargar_cookies(args.cookies)
    session = construir_session(cookies)

    if args.post_url:
        resp = session.get(args.post_url, timeout=15)
        post = parsear_post(resp.text, args.post_url)
        print(json.dumps(post, ensure_ascii=False, indent=2))
    else:
        print(f"📡 Escaneando {args.paginas} páginas de posts recientes...")
        posts = obtener_posts_comunidad(session, args.paginas)
        relevantes = []
        for p in posts:
            datos = parsear_post(p["html"], p["url"])
            if datos["relevante"]:
                relevantes.append(datos)

        nuevos = guardar_kb(relevantes)
        print(f"\n🎯 Posts relevantes encontrados: {len(relevantes)}")
        print(f"📥 Nuevos en KB: {len(nuevos)}")


if __name__ == "__main__":
    main()
