"""
Endpoints FastAPI para recibir webhooks de Shopify.
Montar en la app principal con: app.include_router(webhooks_router)
"""

import json
import logging
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.services.abandoned_cart_handler import AbandonedCartHandler

webhooks_router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

_handler = AbandonedCartHandler()


@webhooks_router.post("/shopify/abandoned-cart")
async def shopify_abandoned_cart(
    request: Request,
    x_shopify_hmac_sha256: str = Header(default=""),
):
    """
    Recibe webhook checkouts/create o checkouts/update de Shopify.
    Shopify firma cada request con X-Shopify-Hmac-Sha256.
    """
    body_bytes = await request.body()

    if not _handler.verificar_firma(body_bytes, x_shopify_hmac_sha256):
        logger.warning("Webhook de carrito abandonado con firma inválida rechazado")
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    resultado = _handler.enviar(payload)

    if resultado["ok"]:
        logger.info(
            "Carrito abandonado enviado a Make.com | correlation_id=%s",
            resultado.get("correlation_id"),
        )
        return JSONResponse(content=resultado, status_code=200)
    else:
        logger.error("Error enviando carrito abandonado | %s", resultado.get("error"))
        return JSONResponse(content=resultado, status_code=500)


@webhooks_router.get("/health")
async def webhooks_health():
    return {"status": "ok", "make_configured": _handler.esta_configurado()}
