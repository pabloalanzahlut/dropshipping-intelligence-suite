"""
BulkUrlImporter — Importación masiva de productos desde URLs
=============================================================
Flujo por producto: datos de coste → validación sobre coste LANDED (producto + envío, convertido a la
divisa de la tienda) → verificación determinista → borrador en Shopify → registro en BD.

Regla suprema: no se inventan datos. Cada producto trae SU coste y SU envío; si falta cualquiera de
los dos el producto queda `skipped` con DATA_GAP_REQUEST y no se crea nada en Shopify.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import urllib.request
import uuid
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

from app.database.connection import DatabaseConnection
from app.services.deterministic_gate import verificar_copy, verificar_validacion_financiera
from app.services.financial_validator import FinancialValidator

logger = logging.getLogger(__name__)

PLATFORM_PATTERNS = {
    "aliexpress": re.compile(r"aliexpress\.com", re.I),
    "cjdropshipping": re.compile(r"cjdropshipping\.com", re.I),
    "temu": re.compile(r"temu\.com", re.I),
}

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
_TITULO_BASURA = re.compile(r"captcha|robot|access denied|verify|just a moment|404|not found", re.I)

# Descripción neutra: el borrador puede acabar publicado, así que no lleva proveedor, URL de origen
# ni cálculos internos. La ficha real se redacta después con /redactar-ficha-shopify.
DESCRIPCION_BORRADOR = "<p>Borrador pendiente de ficha de producto.</p>"


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
    """Título de la página (<title>). Devuelve '' si la plataforma sirve captcha o falla."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read(32768).decode("utf-8", errors="ignore")
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        if m:
            titulo = re.sub(r"\s+", " ", m.group(1)).strip()
            titulo = re.sub(r"\s*[\|–\-]\s*(AliExpress|Temu|CJDropshipping).*$", "", titulo, flags=re.I)
            if titulo and not _TITULO_BASURA.search(titulo):
                return titulo[:200]
    except Exception as e:
        logger.warning(f"[SCRAPE] No se pudo obtener título de {url}: {e}")
    return ""


def _numero(valor: str) -> Optional[float]:
    try:
        return float(valor.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def parsear_lineas(texto: str) -> List[Dict[str, Any]]:
    """
    Una línea por producto: `URL  coste  envío` separados por espacios o tabuladores.
    El envío puede ser 0 si el proveedor lo da gratis, pero debe escribirse. Admite coma decimal.
    Lo que falte queda en None y el importador lo marca como DATA_GAP_REQUEST.
    """
    items: List[Dict[str, Any]] = []
    for linea in texto.splitlines():
        partes = linea.split()
        if not partes:
            continue
        numeros = [_numero(p) for p in partes[1:3]]
        numeros += [None] * (2 - len(numeros))
        items.append({"url": partes[0], "costo_origen": numeros[0], "costo_envio": numeros[1]})
    return items


class BulkUrlImporter:
    """Importa productos como borradores en Shopify con validación financiera y gate determinista."""

    def __init__(self, db: Optional[DatabaseConnection] = None, shopify: Any = None,
                 titulo_fn: Callable[[str], str] = scrape_titulo_basico, pausa: float = 0.5):
        self.db = db or DatabaseConnection()
        self.validator = FinancialValidator(self.db)
        self._shopify = shopify
        self._moneda: Optional[str] = None
        self._titulo_fn = titulo_fn
        self._pausa = pausa

    # ── API pública ──────────────────────────────────────────────────────────

    def importar_lote(self, items: List[Dict[str, Any]], moneda_costo: str = "USD",
                      etiqueta_lote: str = "") -> List[Dict]:
        """
        Args:
            items: dicts con `url`, `costo_origen`, `costo_envio` y opcionalmente `peso_kg`.
            moneda_costo: divisa en la que el proveedor da coste y envío (AliExpress/CJ: USD).
            etiqueta_lote: etiqueta Shopify común (p. ej. «test-2026-11») para filtrar o borrar el lote.
        """
        resultados = []
        for item in items:
            url = (item.get("url") or "").strip()
            if not url:
                continue
            r = self._importar_uno(url, item, moneda_costo, etiqueta_lote)
            resultados.append(r)
            if r["status"] != "skipped" or r.get("guardar"):
                self._guardar_en_bd(r)
            if r["status"] == "success" and self._pausa:
                time.sleep(self._pausa)
        exitosos = sum(1 for r in resultados if r["status"] == "success")
        logger.info(f"[BULK] Lote finalizado: {exitosos}/{len(resultados)} borradores creados")
        return resultados

    # ── interno ──────────────────────────────────────────────────────────────

    def _resultado(self, url: str, plataforma: str, pid: str, status: str, error: Optional[str] = None,
                   draft: Optional[str] = None, validacion: Optional[Dict] = None, guardar: bool = True) -> Dict:
        return {"url": url, "plataforma": plataforma, "product_id": pid, "status": status,
                "shopify_draft_id": draft, "error": error, "validacion": validacion or {}, "guardar": guardar}

    def _cliente(self):
        if self._shopify is None:
            from app.services.shopify_client import ShopifyClient
            self._shopify = ShopifyClient()
        return self._shopify

    def _moneda_tienda(self) -> str:
        """Divisa real de la tienda; si Shopify no la da, no se asume ninguna."""
        if self._moneda is None:
            moneda = (self._cliente().shop_info() or {}).get("moneda")
            if not moneda:
                raise RuntimeError("No se pudo leer la divisa de la tienda en Shopify")
            self._moneda = str(moneda).upper()
        return self._moneda

    def _ya_importada(self, url: str) -> bool:
        try:
            with self.db.get_connection() as conn:
                return conn.execute(
                    "SELECT 1 FROM importaciones_masivas WHERE url_origen = ? AND status = 'success' LIMIT 1",
                    (url,)).fetchone() is not None
        except Exception as e:
            logger.warning(f"[BULK] No se pudo comprobar duplicados: {e}")
            return False

    def _importar_uno(self, url: str, item: Dict[str, Any], moneda_costo: str, etiqueta_lote: str) -> Dict:
        plataforma = detectar_plataforma(url)
        pid = extraer_product_id(url, plataforma)
        costo, envio = item.get("costo_origen"), item.get("costo_envio")

        faltan = [n for n, v in (("coste del producto", costo), ("coste de envío", envio)) if v is None]
        if faltan:
            return self._resultado(url, plataforma, pid, "skipped", guardar=False,
                                   error=f"DATA_GAP_REQUEST: falta {' y '.join(faltan)} (el multiplicador "
                                         f"se mide sobre coste landed; escribe 0 si el envío es gratis)")
        if costo <= 0 or envio < 0:
            return self._resultado(url, plataforma, pid, "skipped", guardar=False,
                                   error="Coste debe ser > 0 y envío ≥ 0")
        if self._ya_importada(url):
            return self._resultado(url, plataforma, pid, "skipped", guardar=False,
                                   error="Duplicado: esta URL ya tiene un borrador creado")

        try:
            moneda_pvp = self._moneda_tienda()
        except Exception as e:
            return self._resultado(url, plataforma, pid, "error", error=str(e))

        sku = pid or hashlib.md5(url.encode()).hexdigest()[:12]
        validacion = self.validator.validar_producto(
            sku, costo, float(item.get("peso_kg") or 0.0), costo_envio=envio,
            moneda_costo=moneda_costo, moneda_pvp=moneda_pvp)
        if not validacion.get("validado"):
            return self._resultado(url, plataforma, pid, "skipped", validacion=validacion,
                                   error=validacion.get("nota_auditoria", "No cumple el multiplicador mínimo x2"))

        gate = verificar_validacion_financiera(validacion)
        if not gate["passed"]:
            return self._resultado(url, plataforma, pid, "error", validacion=validacion,
                                   error="Gate determinista: " + "; ".join(gate["violations"]))

        titulo = self._titulo_fn(url) or f"Producto {pid or sku} (revisar título)"
        gate_copy = verificar_copy(f"{titulo} {DESCRIPCION_BORRADOR}")
        if not gate_copy["passed"]:
            titulo = f"Producto {pid or sku} (revisar título)"

        tags = ",".join(t for t in ("gem-os", f"origen-{plataforma}", etiqueta_lote.strip()) if t)
        try:
            draft_id = self._cliente().create_draft_product(
                titulo=titulo, descripcion=DESCRIPCION_BORRADOR, precio=validacion["pvp_calculado"], tags=tags)
        except Exception as e:
            logger.error(f"[BULK] Error creando borrador para {url}: {e}")
            return self._resultado(url, plataforma, pid, "error", error=str(e), validacion=validacion)
        return self._resultado(url, plataforma, pid, "success", draft=draft_id, validacion=validacion)

    def _guardar_en_bd(self, r: Dict):
        try:
            with self.db.get_connection() as conn:
                conn.execute(
                    """INSERT INTO importaciones_masivas
                           (correlation_id, url_origen, plataforma, product_id_externo,
                            shopify_draft_id, status, validacion_financiera, error_msg)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (str(uuid.uuid4()), r["url"], r["plataforma"], r.get("product_id", ""),
                     r.get("shopify_draft_id"), r["status"], json.dumps(r.get("validacion", {})), r.get("error")))
                conn.commit()
        except Exception as e:
            logger.error(f"[BULK] Error guardando en BD: {e}")
