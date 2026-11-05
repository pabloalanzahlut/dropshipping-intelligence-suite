"""
BulkUrlImporter — Importación Masiva de Productos desde URLs
=============================================================
Flujo: URLs → scrape básico → validación 3x → draft Shopify → BD
Plataformas soportadas: AliExpress, CJDropshipping, Temu
"""

import hashlib
import json
import logging
import os
import re
import time
import urllib.request
import uuid
from typing import Dict, List, Optional
from urllib.parse import urlparse

from app.database.connection import DatabaseConnection
from app.services.financial_validator import FinancialValidator
from app.services.shopify_client import ShopifyClient

logger = logging.getLogger(__name__)

PLATFORM_PATTERNS = {
    "aliexpress": re.compile(r"aliexpress\.com", re.I),
    "cjdropshipping": re.compile(r"cjdropshipping\.com", re.I),
    "temu": re.compile(r"temu\.com", re.I),
}

# User-Agent genérico para scraping básico
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def detectar_plataforma(url: str) -> str:
    for nombre, patron in PLATFORM_PATTERNS.items():
        if patron.search(url):
            return nombre
    return "desconocida"


def extraer_product_id(url: str, plataforma: str) -> str:
    """Extrae el ID del producto de la URL según la plataforma."""
    if plataforma == "aliexpress":
        m = re.search(r"/item/(\d+)", url)
        return m.group(1) if m else ""
    if plataforma == "cjdropshipping":
        m = re.search(r"[?&]id=([A-Za-z0-9\-]+)", url)
        return m.group(1) if m else ""
    if plataforma == "temu":
        m = re.search(r"-(\d+)\.html", url)
        return m.group(1) if m else ""
    return ""


def scrape_titulo_basico(url: str) -> str:
    """Extrae el título de la página mediante <title> tag. Fallback a URL si falla."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read(32768).decode("utf-8", errors="ignore")
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        if m:
            titulo = re.sub(r"\s+", " ", m.group(1)).strip()
            # Limpiar sufijos de plataforma
            titulo = re.sub(r"\s*[\|–\-]\s*(AliExpress|Temu|CJDropshipping).*$", "", titulo, flags=re.I)
            return titulo[:200]
    except Exception as e:
        logger.warning(f"[SCRAPE] No se pudo obtener título de {url}: {e}")
    return urlparse(url).path.split("/")[-1][:100]


class BulkUrlImporter:
    """Importa una lista de URLs como borradores en Shopify con validación financiera."""

    def __init__(self, db: Optional[DatabaseConnection] = None):
        self.db = db or DatabaseConnection()
        self.validator = FinancialValidator(self.db)

    def importar_lote(self, urls: List[str],
                      costo_origen: Optional[float] = None,
                      peso_kg: float = 0.3) -> List[Dict]:
        """
        Importa una lista de URLs como borradores en Shopify.

        Args:
            urls: Lista de URLs de productos
            costo_origen: Costo de origen en USD. Si None → DATA_GAP_REQUEST (skipped)
            peso_kg: Peso estimado en kg (default 0.3 kg)

        Returns:
            Lista de resultados por URL con campos:
            url, plataforma, product_id, status, shopify_draft_id, error
        """
        if costo_origen is None:
            logger.warning("[BULK] DATA_GAP_REQUEST: costo_origen requerido para validar regla 3x")
            return [
                {
                    "url": u,
                    "plataforma": detectar_plataforma(u),
                    "product_id": "",
                    "status": "skipped",
                    "shopify_draft_id": None,
                    "error": "DATA_GAP_REQUEST: se necesita costo_origen para aplicar regla 3x",
                }
                for u in urls
            ]

        try:
            shopify = ShopifyClient()
        except EnvironmentError as e:
            logger.error(f"[BULK] Shopify no configurado: {e}")
            return [
                {"url": u, "plataforma": detectar_plataforma(u), "product_id": "",
                 "status": "error", "shopify_draft_id": None, "error": str(e)}
                for u in urls
            ]

        resultados = []
        for url in urls:
            url = url.strip()
            if not url:
                continue
            resultado = self._importar_uno(url, costo_origen, peso_kg, shopify)
            resultados.append(resultado)
            self._guardar_en_bd(resultado, costo_origen)
            time.sleep(0.5)  # cortesía hacia Shopify API rate limit

        exitosos = sum(1 for r in resultados if r["status"] == "success")
        logger.info(f"[BULK] Lote finalizado: {exitosos}/{len(resultados)} exitosos")
        return resultados

    def _importar_uno(self, url: str, costo_origen: float,
                       peso_kg: float, shopify: ShopifyClient) -> Dict:
        plataforma = detectar_plataforma(url)
        product_id = extraer_product_id(url, plataforma)

        # 1. Validación financiera
        sku = product_id or hashlib.md5(url.encode()).hexdigest()[:12]
        validacion = self.validator.validar_producto(sku, costo_origen, peso_kg)
        if not validacion.get("validado"):
            return {
                "url": url,
                "plataforma": plataforma,
                "product_id": product_id,
                "status": "skipped",
                "shopify_draft_id": None,
                "error": validacion.get("nota_auditoria", "No cumple reglas financieras"),
                "validacion": validacion,
            }

        # 2. Scrape título básico
        titulo = scrape_titulo_basico(url)
        pvp = validacion["pvp_calculado"]
        descripcion = (
            f"<p>Importado desde {plataforma.capitalize()}. "
            f"PVP sugerido (regla 3x): ${pvp:.2f} USD. "
            f"<a href='{url}' target='_blank'>Ver producto original</a></p>"
        )
        tags = f"gem-os,{plataforma},importacion-masiva"

        # 3. Crear borrador en Shopify
        try:
            draft_id = shopify.create_draft_product(
                titulo=titulo,
                descripcion=descripcion,
                precio=pvp,
                tags=tags,
            )
            return {
                "url": url,
                "plataforma": plataforma,
                "product_id": product_id,
                "status": "success",
                "shopify_draft_id": draft_id,
                "error": None,
                "validacion": validacion,
            }
        except Exception as e:
            logger.error(f"[BULK] Error creando borrador para {url}: {e}")
            return {
                "url": url,
                "plataforma": plataforma,
                "product_id": product_id,
                "status": "error",
                "shopify_draft_id": None,
                "error": str(e),
                "validacion": validacion,
            }

    def _guardar_en_bd(self, resultado: Dict, costo_origen: float):
        correlation_id = str(uuid.uuid4())
        validacion_json = json.dumps(resultado.get("validacion", {}))
        try:
            with self.db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO importaciones_masivas
                        (correlation_id, url_origen, plataforma, product_id_externo,
                         shopify_draft_id, status, validacion_financiera, error_msg)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        correlation_id,
                        resultado["url"],
                        resultado["plataforma"],
                        resultado.get("product_id", ""),
                        resultado.get("shopify_draft_id"),
                        resultado["status"],
                        validacion_json,
                        resultado.get("error"),
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"[BULK] Error guardando en BD: {e}")
