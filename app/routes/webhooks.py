"""
Endpoints Flask para recibir webhooks de Shopify.
Registrar en la app principal con: app.register_blueprint(webhooks_bp)
"""

import json
import logging
from flask import Blueprint, request, jsonify
from app.services.abandoned_cart_handler import AbandonedCartHandler

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/webhooks")
logger = logging.getLogger(__name__)

_handler = AbandonedCartHandler()


@webhooks_bp.route("/shopify/abandoned-cart", methods=["POST"])
def shopify_abandoned_cart():
    """
    Recibe webhook checkouts/create o checkouts/update de Shopify.
    Shopify firma cada request con X-Shopify-Hmac-Sha256.
    """
    body_bytes = request.get_data()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")

    if not _handler.verificar_firma(body_bytes, hmac_header):
        logger.warning("Webhook de carrito abandonado con firma inválida rechazado")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON"}), 400

    resultado = _handler.enviar(payload)

    if resultado["ok"]:
        logger.info("Carrito abandonado enviado a Make.com | correlation_id=%s", resultado.get("correlation_id"))
        return jsonify(resultado), 200
    else:
        logger.error("Error enviando carrito abandonado | %s", resultado.get("error"))
        return jsonify(resultado), 500


@webhooks_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "make_configured": _handler.esta_configurado()}), 200
