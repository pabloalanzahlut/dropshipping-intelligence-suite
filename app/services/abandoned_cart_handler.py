"""
AbandonedCartHandler - Recibe webhooks de Shopify (checkout abandonado)
y los reenvía a Make.com para recuperación por email en horario nocturno.
Requiere MAKE_WEBHOOK_ABANDONED_CART y SHOPIFY_WEBHOOK_SECRET en .env.
"""

import os
import json
import hmac
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone
import uuid
from dotenv import load_dotenv

load_dotenv()


class AbandonedCartHandler:
    """Procesa checkouts abandonados de Shopify y los envía a Make.com."""

    def __init__(self):
        self.webhook_url = os.getenv("MAKE_WEBHOOK_ABANDONED_CART", "").strip()
        self.webhook_secret = os.getenv("SHOPIFY_WEBHOOK_SECRET", "").strip()

    def esta_configurado(self) -> bool:
        return bool(self.webhook_url)

    def verificar_firma(self, body_bytes: bytes, hmac_header: str) -> bool:
        """Verifica que el webhook proviene genuinamente de Shopify."""
        if not self.webhook_secret:
            return True  # sin secret configurado, aceptar (solo para dev)
        digest = hmac.new(
            self.webhook_secret.encode("utf-8"),
            body_bytes,
            hashlib.sha256,
        ).digest()
        import base64
        expected = base64.b64encode(digest).decode()
        return hmac.compare_digest(expected, hmac_header or "")

    def extraer_variables(self, payload: dict) -> dict:
        """
        Extrae las variables clave del payload JSON de Shopify checkout.

        Rutas:
          email              → payload["email"]
          nombre             → payload["customer"]["first_name"]
          articulos          → payload["line_items"]
          total_precio       → payload["total_price"]
          moneda             → payload["currency"]
          recovery_url       → payload["abandoned_checkout_url"]
          timestamp_abandono → payload["created_at"]
          articulo_principal → payload["line_items"][0]["title"]
          imagen_principal   → payload["line_items"][0]["image"]["src"]
        """
        line_items = payload.get("line_items", [])
        primer_item = line_items[0] if line_items else {}
        imagen = primer_item.get("image") or {}

        return {
            "email": payload.get("email", ""),
            "nombre": (payload.get("customer") or {}).get("first_name", ""),
            "articulos": line_items,
            "total_precio": payload.get("total_price", "0.00"),
            "moneda": payload.get("currency", "USD"),
            "recovery_url": payload.get("abandoned_checkout_url", ""),
            "timestamp_abandono": payload.get("created_at", ""),
            "articulo_principal": primer_item.get("title", ""),
            "imagen_principal": imagen.get("src", ""),
            "checkout_token": payload.get("token", payload.get("id", "")),
        }

    def construir_payload_make(self, vars_extraidas: dict) -> dict:
        """Construye el JSON que se envía a Make.com."""
        return {
            "source": "GEM_OS_ABANDONED_CART",
            "correlation_id": f"{vars_extraidas['checkout_token']}_{int(datetime.now(timezone.utc).timestamp())}",
            "to": vars_extraidas["email"],
            "subject": f"{vars_extraidas['nombre']}, dejaste algo olvidado",
            "template_vars": {
                "nombre": vars_extraidas["nombre"],
                "articulo_principal": vars_extraidas["articulo_principal"],
                "imagen_principal": vars_extraidas["imagen_principal"],
                "total": f"{vars_extraidas['total_precio']} {vars_extraidas['moneda']}",
                "recovery_url": vars_extraidas["recovery_url"],
                "articulos_lista": vars_extraidas["articulos"],
            },
            "metadata": {
                "shopify_checkout_token": vars_extraidas["checkout_token"],
                "timestamp_abandono": vars_extraidas["timestamp_abandono"],
                "timestamp_enviado": datetime.now(timezone.utc).isoformat(),
            },
        }

    def enviar(self, payload_shopify: dict) -> dict:
        """
        Extrae variables, construye payload Make.com y lo envía vía webhook.

        Returns:
            {"ok": True, "correlation_id": "..."} o {"ok": False, "error": "..."}
        """
        if not self.esta_configurado():
            return {"ok": False, "error": "[DATA_GAP] MAKE_WEBHOOK_ABANDONED_CART no está configurado en .env"}

        email = payload_shopify.get("email", "")
        if not email:
            return {"ok": False, "error": "Checkout sin email — no se puede recuperar"}

        vars_extraidas = self.extraer_variables(payload_shopify)
        payload_make = self.construir_payload_make(vars_extraidas)

        data = json.dumps(payload_make).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                status = resp.status
                body = resp.read().decode("utf-8", errors="ignore")
                if status in (200, 201, 202):
                    return {
                        "ok": True,
                        "correlation_id": payload_make["correlation_id"],
                        "mensaje": f"Enviado a Make.com (HTTP {status}): {body[:200]}",
                    }
                return {"ok": False, "error": f"HTTP {status}: {body[:200]}"}
        except urllib.error.URLError as e:
            # retry 1x tras timeout
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    return {"ok": True, "correlation_id": payload_make["correlation_id"], "mensaje": "Reintento exitoso"}
            except Exception:
                return {"ok": False, "error": f"Error de red tras reintento: {e.reason}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


# --- CLI de prueba ---
if __name__ == "__main__":
    import sys

    PAYLOAD_TEST = {
        "id": "test_checkout_001",
        "token": "test_checkout_001",
        "email": "cliente@ejemplo.com",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_price": "49.99",
        "currency": "USD",
        "customer": {"id": 1, "first_name": "Ana", "last_name": "García", "email": "cliente@ejemplo.com"},
        "line_items": [
            {
                "id": "item_1",
                "title": "Masajeador Eléctrico Portátil",
                "quantity": 1,
                "price": "49.99",
                "variant_title": "Color: Negro",
                "image": {"src": "https://cdn.shopify.com/s/files/1/test/image.jpg"},
            }
        ],
        "abandoned_checkout_url": "https://tu-tienda.myshopify.com/checkout/recover?token=test_checkout_001",
    }

    handler = AbandonedCartHandler()
    if "--test" in sys.argv:
        vars_extraidas = handler.extraer_variables(PAYLOAD_TEST)
        payload_make = handler.construir_payload_make(vars_extraidas)
        print("=== Variables extraídas ===")
        print(json.dumps(vars_extraidas, indent=2, ensure_ascii=False, default=str))
        print("\n=== Payload Make.com ===")
        print(json.dumps(payload_make, indent=2, ensure_ascii=False, default=str))
        if handler.esta_configurado():
            resultado = handler.enviar(PAYLOAD_TEST)
            print("\n=== Resultado envío ===")
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
        else:
            print("\n[INFO] MAKE_WEBHOOK_ABANDONED_CART no configurado — solo mostrando payload")
