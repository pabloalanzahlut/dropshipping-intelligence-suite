"""
ShopifyClient — Cliente Shopify Admin API para GEM OS
======================================================
Crea borradores de productos en Shopify directamente.
Credenciales: SHOPIFY_STORE_URL + SHOPIFY_ACCESS_TOKEN en .env
"""

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ShopifyClient:
    """Cliente para la Shopify Admin API (REST)."""

    API_VERSION = "2024-01"

    def __init__(self):
        store_url = os.getenv("SHOPIFY_STORE_URL", "").rstrip("/")
        token = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
        if not store_url or not token:
            raise EnvironmentError(
                "SHOPIFY_STORE_URL y SHOPIFY_ACCESS_TOKEN deben estar configurados en .env"
            )
        self._base = f"{store_url}/admin/api/{self.API_VERSION}"
        self._headers = {
            "X-Shopify-Access-Token": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> dict:
        url = f"{self._base}{path}"
        data = json.dumps(payload).encode() if payload else None
        req = urllib.request.Request(url, data=data, headers=self._headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            logger.error(f"[SHOPIFY] {method} {path} → HTTP {e.code}: {body}")
            raise

    def create_draft_product(self, titulo: str, descripcion: str, precio: float,
                              imagenes: list[str] | None = None,
                              vendor: str = "GEM OS Import",
                              tags: str = "") -> str:
        """
        Crea un producto como borrador en Shopify.

        Returns:
            ID del producto creado (string)
        """
        payload = {
            "product": {
                "title": titulo,
                "body_html": descripcion,
                "vendor": vendor,
                "tags": tags,
                "status": "draft",
                "variants": [{"price": f"{precio:.2f}", "inventory_management": None}],
            }
        }
        if imagenes:
            payload["product"]["images"] = [{"src": url} for url in imagenes[:10]]

        resp = self._request("POST", "/products.json", payload)
        product_id = str(resp["product"]["id"])
        logger.info(f"[SHOPIFY] Borrador creado: id={product_id} titulo='{titulo}'")
        return product_id

    def get_product(self, product_id: str) -> dict:
        """Obtiene metadatos de un producto existente."""
        resp = self._request("GET", f"/products/{product_id}.json")
        return resp.get("product", {})
