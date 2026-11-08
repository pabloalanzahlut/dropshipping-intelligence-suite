"""
GEM OS — Pipeline Automático Skool (método Google Docs)
========================================================
Descarga los documentos "PRODUCTOS GANADORES [MES]" publicados por
Vic Ecomilions en Comunidad Ecommerce y los almacena en la KB.

Estrategia:
  1. Descarga los Google Docs de cada mes conocido via requests (sin login)
  2. Parsea nombres + links AutoDS de cada documento
  3. Detecta nuevos meses scrapeando el feed de Skool con cookies (opcional)
  4. Guarda todo en skool_productos.json
  5. Genera reporte Dr. Marcus Chen

Uso:
    python ai_workspace/scripts/auto_pipeline_skool.py
    python ai_workspace/scripts/auto_pipeline_skool.py --solo-reporte
    python ai_workspace/scripts/auto_pipeline_skool.py --nuevo-mes YYYY-MM <doc_id>
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

# ── Rutas ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent.parent
SCRIPTS_DIR = Path(__file__).parent
ENV_PATH    = ROOT / ".env"
COOKIES_PATH = SCRIPTS_DIR / "skool_cookies.json"
KB_PATH     = ROOT / "ai_workspace" / "knowledge_base" / "skool_productos.json"
LOG_PATH    = ROOT / "ai_workspace" / "knowledge_base" / "skool_sync.log"
DOCS_INDEX_PATH = SCRIPTS_DIR / "skool_docs_index.json"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(
            open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
        ),
    ],
)
log = logging.getLogger("GEM_SKOOL")

# ── Dependencias ──────────────────────────────────────────────────────────────
def _instalar(dep):
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", dep, "-q"], check=True)

try:
    import requests
except ImportError:
    _instalar("requests"); import requests

try:
    from dotenv import load_dotenv
except ImportError:
    _instalar("python-dotenv"); from dotenv import load_dotenv

load_dotenv(ENV_PATH)

# ── Índice de documentos conocidos ───────────────────────────────────────────
# Mapa mes_clave → Google Doc ID (documentos de Vic Ecomilions)
DOCS_CONOCIDOS: dict[str, str] = {
    "octubre_2026":    "10FtHS3Q2hqlH1x4w4e1PitzysQ_ADkw5RLtEDiaa0NI",
    "septiembre_2026": "1s17rrmngUwtJYxWT-5-hGBUesIfaC2Hi-rfQxilwcvA",
    "agosto_2026":     "16ynsvGCw4Lw000XpZZ_owMSWfExw8Q2TpVwXa5PyrWI",
    "julio_2026":      "1Xg-D0-jIsoFz88bbBEOtyuoKE9ulyExTep-QwhAyWQc",
    "mayo_2026":       "1XMY-jNCecp_kxYAQ7O1t-TdCExivjc9gAghKnNMfKe0",
    "abril_2026":      "1wncbmYd08RF0zyiHkepeV0l8dqTbUrlb3eHTFUiy208",
    "marzo_2026":      "1g-ET_KOgIUJvQiBdMX-yLj6U2pLxeoPKmA0vMBzCMVY",
    "febrero_2026":    "1s3tUwJKMRssVNJ9WxJrMMidg7t65iNnI6Gap59-9x1E",
}


def cargar_docs_index() -> dict[str, str]:
    """Carga el índice de docs: combina los conocidos + los guardados en disco."""
    guardados: dict[str, str] = {}
    if DOCS_INDEX_PATH.exists():
        try:
            guardados = json.loads(DOCS_INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    merged = {**DOCS_CONOCIDOS, **guardados}
    return merged


def guardar_docs_index(docs: dict[str, str]):
    DOCS_INDEX_PATH.write_text(
        json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── PASO 1: Descarga y parseo de Google Docs ──────────────────────────────────

def descargar_doc(doc_id: str, session: requests.Session) -> str | None:
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    try:
        r = session.get(url, timeout=15)
        if r.status_code == 200:
            return r.text.strip()
        log.warning(f"Doc {doc_id}: HTTP {r.status_code}")
        return None
    except Exception as e:
        log.warning(f"Doc {doc_id}: {e}")
        return None


def parsear_productos(texto: str, mes: str) -> list[dict]:
    """Extrae pares (nombre, link_autods) de un texto de Google Doc."""
    lineas = [l.strip().lstrip("﻿") for l in texto.split("\n") if l.strip()]
    productos = []
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        # Saltar cabeceras, notas, URLs sueltas
        if (
            linea.upper().startswith("PRODUCTOS GANADORES")
            or linea.startswith("Nota:")
            or linea.startswith("Utiliza")
            or linea.startswith("http")
            or len(linea) > 150
        ):
            i += 1
            continue

        nombre = linea.rstrip(":")
        link = ""
        if i + 1 < len(lineas) and lineas[i + 1].startswith("https://"):
            link = lineas[i + 1]
            i += 2
        else:
            i += 1

        if len(nombre) >= 8 and not nombre.startswith("https"):
            productos.append({
                "mes": mes,
                "fecha_extraccion": datetime.now().isoformat(),
                "fuente": "Vic Ecomilions — Comunidad Ecommerce Skool",
                "nombre": nombre,
                "link_autods": link,
                "clasificacion_gem": "HOT",
                "validado_por": "Vic Ecomilions (mentor Adrián Sáenz)",
            })
    return productos


# ── PASO 2: Detectar docs nuevos en el feed de Skool ─────────────────────────

GDOC_RE = re.compile(
    r"docs\.google\.com/document/d/([-\w]{20,})"
)
FEED_URL = "https://www.skool.com/comunidad-ecommerce?s=newest&fl="


def detectar_nuevos_docs(docs_conocidos: dict[str, str]) -> dict[str, str]:
    """
    Accede al feed de Skool con cookies guardadas y busca posts que contengan
    links de Google Docs nuevos. Devuelve {mes_clave: doc_id} para docs nuevos.
    """
    if not COOKIES_PATH.exists():
        log.info("Sin cookies de Skool — omitiendo detección de docs nuevos")
        return {}

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _instalar("playwright")
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium", "--with-deps"],
            check=True,
        )
        from playwright.sync_api import sync_playwright

    nuevos: dict[str, str] = {}
    ids_conocidos = set(docs_conocidos.values())

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120"
            )
            cookies = json.loads(COOKIES_PATH.read_text())
            if cookies:
                ctx.add_cookies(cookies)
            page = ctx.new_page()

            log.info("Escaneando feed Skool en busca de nuevos docs...")
            page.goto(FEED_URL, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(3000)

            # Scroll 5 veces para cargar más posts
            for _ in range(5):
                page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                page.wait_for_timeout(1500)

            html = page.content()
            browser.close()

        # Buscar todos los Google Doc IDs en el HTML
        encontrados = GDOC_RE.findall(html)
        for doc_id in set(encontrados):
            if doc_id in ids_conocidos:
                continue
            # Intentar descargar y ver si es un doc de productos ganadores
            session = requests.Session()
            session.headers["User-Agent"] = "Mozilla/5.0 Chrome/120"
            texto = descargar_doc(doc_id, session)
            if not texto:
                continue
            if "PRODUCTOS GANADORES" in texto.upper():
                # Extraer el mes del contenido
                m = re.search(
                    r"PRODUCTOS GANADORES\s+(\w+)\s+(\d{4})", texto.upper()
                )
                if m:
                    mes_nombre = m.group(1).lower()
                    anio = m.group(2)
                    mes_clave = f"{mes_nombre}_{anio}"
                    nuevos[mes_clave] = doc_id
                    log.info(f"Nuevo doc encontrado: {mes_clave} → {doc_id}")

    except Exception as e:
        log.warning(f"Detección de nuevos docs fallida: {e}")

    return nuevos


# ── PASO 3: Knowledge Base ────────────────────────────────────────────────────

def cargar_kb() -> list[dict]:
    if KB_PATH.exists():
        try:
            return json.loads(KB_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def guardar_kb(todos: list[dict]):
    KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    KB_PATH.write_text(json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8")


def meses_en_kb(kb: list[dict]) -> set[str]:
    return {p.get("mes", "") for p in kb}


# ── PASO 4: Reporte Dr. Marcus Chen ──────────────────────────────────────────

def generar_reporte(kb: list[dict]) -> str:
    if not kb:
        return "KB vacia — ejecuta el pipeline primero."

    por_mes: Counter = Counter(p.get("mes", "?") for p in kb)
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")

    lineas = [
        "",
        "=" * 55,
        f"REPORTE SKOOL — {hoy}",
        "Dr. Marcus Chen | 32 años · GEM OS Intelligence",
        "=" * 55,
        "",
        f"Total productos en KB : {len(kb)}",
        f"Meses cubiertos       : {len(por_mes)}",
        "",
        "PRODUCTOS POR MES:",
    ]

    for mes, n in sorted(por_mes.items(), reverse=True):
        lineas.append(f"  {mes:<22} {n:>2} productos")

    lineas += [
        "",
        "MUESTRA — OCTUBRE 2026:",
    ]
    for p in [x for x in kb if x.get("mes") == "octubre_2026"][:5]:
        lineas.append(f"  - {p['nombre']}")

    lineas += [
        "",
        "ANALISIS DR. MARCUS CHEN:",
        f"  {len(kb)} productos validados por mentores del curso Adrián Sáenz.",
        "  Todos clasificados HOT (curación humana experta).",
        "  Fuente: posts mensuales Vic Ecomilions — Comunidad Ecommerce.",
        "  Recomendación: validar regla 3x con /validar-financiero antes de lanzar.",
        "",
        "=" * 55,
        "",
    ]
    return "\n".join(lineas)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GEM OS — Pipeline Skool")
    parser.add_argument("--solo-reporte", action="store_true",
                        help="Solo genera el reporte, sin descargar nada")
    parser.add_argument("--forzar-todo", action="store_true",
                        help="Re-descarga todos los meses aunque ya estén en KB")
    parser.add_argument("--nuevo-mes", nargs=2, metavar=("MES_CLAVE", "DOC_ID"),
                        help="Añade un nuevo mes al índice y lo descarga")
    args = parser.parse_args()

    log.info("=" * 55)
    log.info("GEM OS — Pipeline Automatico Skool")
    log.info("=" * 55)

    kb = cargar_kb()

    # Modo solo-reporte
    if args.solo_reporte:
        print(generar_reporte(kb))
        return

    # Añadir mes nuevo al índice si se pasa por CLI
    docs_index = cargar_docs_index()
    if args.nuevo_mes:
        mes_clave, doc_id = args.nuevo_mes
        docs_index[mes_clave] = doc_id
        guardar_docs_index(docs_index)
        log.info(f"Mes añadido al índice: {mes_clave}")

    # Detectar nuevos docs en el feed (requiere cookies Skool)
    nuevos_detectados = detectar_nuevos_docs(docs_index)
    if nuevos_detectados:
        docs_index.update(nuevos_detectados)
        guardar_docs_index(docs_index)

    # Determinar qué meses descargar
    meses_en_kb_actual = meses_en_kb(kb) if not args.forzar_todo else set()
    meses_a_descargar = {
        mes: doc_id
        for mes, doc_id in docs_index.items()
        if mes not in meses_en_kb_actual
    }

    if not meses_a_descargar:
        log.info("KB al dia — no hay meses nuevos que descargar")
        print(generar_reporte(kb))
        return

    log.info(f"Descargando {len(meses_a_descargar)} mes(es): {list(meses_a_descargar)}")

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 Chrome/120"

    nuevos_productos: list[dict] = []
    for mes, doc_id in meses_a_descargar.items():
        texto = descargar_doc(doc_id, session)
        if not texto:
            log.warning(f"No se pudo descargar {mes} ({doc_id})")
            continue
        productos = parsear_productos(texto, mes)
        log.info(f"  {mes}: {len(productos)} productos")
        nuevos_productos.extend(productos)

    # Actualizar KB evitando duplicados por (mes, nombre)
    existentes = {(p.get("mes"), p.get("nombre")) for p in kb}
    realmente_nuevos = [
        p for p in nuevos_productos
        if (p["mes"], p["nombre"]) not in existentes
    ]
    kb.extend(realmente_nuevos)
    guardar_kb(kb)

    log.info(f"KB actualizada: +{len(realmente_nuevos)} productos | {len(kb)} total")

    print(generar_reporte(kb))
    log.info("Pipeline completado.")


if __name__ == "__main__":
    main()
