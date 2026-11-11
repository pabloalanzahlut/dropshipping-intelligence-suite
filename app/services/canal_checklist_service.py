"""
canal_checklist_service — checklist + copy guiado para canales pagados (Google Ads,
TikTok Ads, Amazon, TikTok Shop). Fase 6 del plan — la de menor prioridad, "1000%"
opcional: sin integración de API en vivo, sin OAuth. Mismo patrón que
hook_matrix_service/anuncios_meta_service: llm_router.chat() + deterministic_gate.verificar_copy.

Los checklists son estáticos, extraídos de los procedimientos reales del curso
(`ai_workspace/skills/{google_ads,tiktok_ads,amazon_dropshipping,tiktok_shop}/procedimiento.md`),
no los inventa el LLM — solo el copy se genera con IA.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services import deterministic_gate
from app.services.llm_router import chat

CANALES = ("google_ads", "tiktok_ads", "amazon", "tiktok_shop")

_CHECKLISTS: Dict[str, List[str]] = {
    "google_ads": [
        "Cuenta creada con email del negocio + conversión «Compra» configurada y verificada (24-48h)",
        "Google Merchant Center vinculado y feed de Shopify sincronizado (título, descripción, precio, imagen, GTIN)",
        "Palabras clave negativas desde el día 1: gratis, segunda mano, cómo hacer, DIY, tutorial",
        "Presupuesto inicial 10-15€/día · CPC manual los primeros 7 días · no tocar pujas en fase de aprendizaje",
        "Extensiones de anuncio activas: sitelinks, texto destacado (envío, devolución, pago seguro), precio",
        "ROAS mínimo 2 (medido en Shopify Analytics, no el que declara Google) antes de escalar presupuesto",
    ],
    "tiktok_ads": [
        "Business Manager + cuenta de empresa verificada · pago con tarjeta de crédito, no débito",
        "Pixel instalado vía app de Shopify (no código manual) y verificado con TikTok Pixel Helper",
        "Eventos disparando: ViewContent, AddToCart, InitiateCheckout, CompletePayment",
        "Zona horaria y moneda del mercado objetivo, no las tuyas",
        "CPA objetivo < 1/3 del PVP · ROAS mínimo 2, objetivo 3+ — contrastar siempre con Shopify Analytics",
        "Plan de apelación listo por si la cuenta se suspende (URL tienda, producto, últimos anuncios, 7 días de margen)",
    ],
    "amazon": [
        "Proveedor cumple los requisitos más estrictos de Amazon (plazos, sin marca ajena, stock real)",
        "Plantilla de envío configurada solo para países donde el proveedor llega en el plazo prometido",
        "Prime NO activado si el dropshipping es externo (penalización por incumplimiento)",
        "Flujo de devolución definido y con límite de 48h para procesar desde la solicitud",
        "AutoDS conectado vía SP-API/MWS, fulfillment automático y alertas de stock configuradas",
        "Regla 3x sobre coste landed respetada igual que en Shopify — Amazon no la relaja",
    ],
    "tiktok_shop": [
        "Cuenta de vendedor verificada (documentación + categoría de negocio, 1-5 días hábiles)",
        "Precio = coste proveedor × 3 mínimo (misma regla 3x que Shopify) y tiempo de envío declarado real",
        "Validación de demanda antes de listar: >10 vídeos con >100K vistas del producto + comentarios pidiendo comprarlo",
        "Canal de venta elegido (vídeo con producto etiquetado, LIVE, pestaña Shop o afiliados) según el objetivo",
        "Sin inversión en ads: validar primero con contenido orgánico antes de escalar con pauta",
    ],
}

_NOMBRES = {"google_ads": "Google Ads", "tiktok_ads": "TikTok Ads", "amazon": "Amazon",
           "tiktok_shop": "TikTok Shop"}

# Un contrato de JSON distinto y autocontenido por canal — nunca se mencionan los otros 3
# canales en el prompt, para que el modelo no devuelva una clave por canal (ya pasó: con los
# 4 descritos a la vez, el modelo generaba {"Google Ads": {...}, "TikTok Ads": {...}, ...}
# en vez de responder solo sobre el canal pedido).
_CONTRATOS: Dict[str, str] = {
    "google_ads": (
        "Genera 3 títulos (máx 30 caracteres cada uno) y 2 descripciones (máx 90 caracteres "
        "cada una) con intención de compra, a partir del producto que recibas.\n"
        'Responde EXCLUSIVAMENTE con este JSON, sin texto antes ni después:\n'
        '{"copy": {"titulo_1": "...", "titulo_2": "...", "titulo_3": "...", '
        '"descripcion_1": "...", "descripcion_2": "..."}}'
    ),
    "tiktok_ads": (
        "Genera 1 hook de vídeo (lo que se dice o se muestra en los primeros 3 segundos) y "
        "1 texto de anuncio corto, a partir del producto que recibas.\n"
        'Responde EXCLUSIVAMENTE con este JSON, sin texto antes ni después:\n'
        '{"copy": {"hook_video": "...", "texto_anuncio": "..."}}'
    ),
    "amazon": (
        "Genera 1 título de listado (formato Marca + Producto + Característica clave) y "
        "3 bullets de ficha de producto, a partir del producto que recibas.\n"
        'Responde EXCLUSIVAMENTE con este JSON, sin texto antes ni después:\n'
        '{"copy": {"titulo_listado": "...", "bullet_1": "...", "bullet_2": "...", "bullet_3": "..."}}'
    ),
    "tiktok_shop": (
        "Genera 1 caption de vídeo con producto etiquetado y 1 llamada a la acción para un "
        "TikTok LIVE, a partir del producto que recibas.\n"
        'Responde EXCLUSIVAMENTE con este JSON, sin texto antes ni después:\n'
        '{"copy": {"caption_video": "...", "cta_live": "..."}}'
    ),
}

SYSTEM_PROMPT_TPL = """Eres un redactor de copy para {nombre_canal} en GEM OS (dropshipping).

{contrato}

Reglas (las mismas de siempre en GEM OS):
- Prohibido superlativos vacíos (increíble, el mejor, revolucionario, etc.).
- Prohibido prometer envío en menos de 6 días sin confirmación del proveedor.
- No inventes especificaciones del producto que no te den.
- Todos los valores del JSON deben ser texto plano (nunca otro objeto JSON anidado)."""


def _db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def checklist(canal: str) -> List[str]:
    if canal not in CANALES:
        raise ValueError(f"Canal desconocido: {canal}")
    return list(_CHECKLISTS[canal])


def _parsear(bruto: Optional[str]) -> Dict[str, Any]:
    if not bruto:
        return {}
    try:
        inicio, fin = bruto.find("{"), bruto.rfind("}")
        datos = json.loads(bruto[inicio:fin + 1]) if inicio != -1 and fin != -1 else {}
    except (ValueError, TypeError):
        return {}
    copy = datos.get("copy") if isinstance(datos, dict) else None
    return copy if isinstance(copy, dict) else {}


def generar(canal: str, contexto_producto: str) -> Dict[str, Any]:
    if canal not in CANALES:
        raise ValueError(f"Canal desconocido: {canal}")
    system_prompt = SYSTEM_PROMPT_TPL.format(nombre_canal=_NOMBRES[canal])
    bruto = chat(task="copy_canal_pagado", system_prompt=system_prompt,
                 user_message=f"Producto:\n{contexto_producto.strip()[:2000]}", max_tokens=1024, temperature=0.4)
    copy = _parsear(bruto)
    texto_gate = " ".join(str(v) for v in copy.values() if isinstance(v, (str, int, float)))
    gate = deterministic_gate.verificar_copy(texto_gate)
    return {
        "canal": canal, "checklist": checklist(canal), "copy": copy,
        "gate_pass": gate["passed"], "gate_violations": gate["violations"], "generado": bool(bruto),
    }


def guardar(db_path: str, producto_id: Optional[int], resultado: Dict[str, Any]) -> int:
    with _db(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO checklists_canal (canal, producto_id, checklist_json, copy_json, gate_pass, "
            "gate_violations_json, creado_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (resultado["canal"], producto_id, json.dumps(resultado["checklist"], ensure_ascii=False),
             json.dumps(resultado["copy"], ensure_ascii=False), int(bool(resultado.get("gate_pass"))),
             json.dumps(resultado.get("gate_violations", []), ensure_ascii=False),
             datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        return cur.lastrowid


def listar(db_path: str, producto_id: Optional[int] = None, canal: str = "") -> List[Dict[str, Any]]:
    sql, params = "SELECT * FROM checklists_canal WHERE 1=1", []
    if producto_id is not None:
        sql += " AND producto_id = ?"
        params.append(producto_id)
    if canal:
        sql += " AND canal = ?"
        params.append(canal)
    sql += " ORDER BY creado_at DESC, id DESC"
    with _db(db_path) as conn:
        try:
            filas = [dict(r) for r in conn.execute(sql, params)]
        except sqlite3.OperationalError:
            return []
    for f in filas:
        f["checklist"] = json.loads(f.pop("checklist_json") or "[]")
        f["copy"] = json.loads(f.pop("copy_json") or "{}")
        f["gate_violations"] = json.loads(f.pop("gate_violations_json") or "[]")
        f["gate_pass"] = bool(f["gate_pass"])
    return filas
