"""
refutacion_debate — borrador de las 8 refutaciones de `.claude/commands/refutar-producto.md`.

NUNCA guarda nada por su cuenta: `redactar_debate()` solo propone un borrador. El humano
lo revisa/edita en la pantalla de refutaciones ya existente y lo confirma con el endpoint
que ya existe (`PUT /api/productos/{id}/refutaciones` → `product_catalog.guardar_refutaciones`,
que es quien aplica el veredicto real — incluidas las eliminatorias #1 y #6).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.services import product_catalog
from app.services.llm_router import chat

_VEREDICTOS_VALIDOS = ("pasa", "refutada", "sin_datos")

SYSTEM_PROMPT = """Eres un analista adversarial de GEM OS. Tu trabajo es intentar REFUTAR
(nunca confirmar) la tesis de que un producto de dropshipping es un ganador — exactamente
al revés de lo que hace el resto del pipeline.

Evalúa estas 8 refutaciones, en este orden, con los datos que recibas (nunca inventes
datos que no te dieron):

1. El margen no aguanta los costes reales (landed + fees 4% + cancelaciones 10,1% + CPA realista).
   Refutada si el neto por unidad no cubre el CPA esperado.
2. La demanda es estacional y vamos tarde. Refutada si el pico ya pasó.
3. Está más saturado de lo que parece. Refutada si hay más de 5 anunciantes activos con el mismo ángulo.
4. El producto genera devoluciones (categoría propensa, por encima del 10,1%). Refutada si la categoría es propensa.
5. El envío mata la conversión. Refutada si el plazo del proveedor supera 15 días en un mercado que espera 3.
6. Hay una barrera legal o aduanera (certificación, baterías sueltas, imitaciones). Refutada si falta esa certificación.
7. El wow factor no sobrevive al vídeo. Refutada si no se puede mostrar el antes/después en 3 segundos.
8. El competidor gana por algo que no podemos copiar (marca, exclusividad, stock local 48h). Refutada si su ventaja es estructural.

Para cada una, responde "pasa" (sobrevive, no la mata), "refutada" (la mata) o "sin_datos"
si no tienes evidencia suficiente — NUNCA marques "pasa" solo porque falta el dato en contra;
el skill es explícito: sin datos cuenta como pendiente, no como superada.

Responde EXCLUSIVAMENTE con este JSON, sin texto antes ni después:
{"refutaciones": [{"numero": 1, "veredicto": "pasa"|"refutada"|"sin_datos", "evidencia": "una frase con el dato o la falta de dato"}, ... 8 elementos, numero 1 a 8]}"""


def _contexto_producto(p: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "nombre": p.get("nombre"), "categoria": p.get("categoria"),
        "costo_origen": p.get("costo_origen"), "costo_envio": p.get("costo_envio"), "pvp": p.get("pvp"),
        "calculo": p.get("calculo"), "notas": p.get("notas"),
    }


def _parsear(bruto: Optional[str]) -> List[Dict[str, Any]]:
    datos: Dict[str, Any] = {}
    if bruto:
        try:
            inicio, fin = bruto.find("{"), bruto.rfind("}")
            if inicio != -1 and fin != -1:
                datos = json.loads(bruto[inicio:fin + 1])
        except (ValueError, TypeError):
            datos = {}
    items = datos.get("refutaciones") if isinstance(datos, dict) else None

    vistos: Dict[int, Dict[str, Any]] = {}
    for item in (items or []):
        if not isinstance(item, dict):
            continue
        try:
            n = int(item.get("numero"))
        except (TypeError, ValueError):
            continue
        if n not in product_catalog.REFUTACIONES or n in vistos:
            continue
        veredicto = str(item.get("veredicto", "")).strip().lower()
        if veredicto not in _VEREDICTOS_VALIDOS:
            veredicto = "sin_datos"
        vistos[n] = {"numero": n, "veredicto": veredicto, "evidencia": str(item.get("evidencia", ""))[:500]}

    for n in product_catalog.REFUTACIONES:
        vistos.setdefault(n, {"numero": n, "veredicto": "sin_datos", "evidencia": ""})
    return [vistos[n] for n in sorted(vistos)]


def redactar_debate(db_path: str, producto_id: int) -> Dict[str, Any]:
    """Genera el borrador; no toca `productos` — devuelve algo que pre-rellenar en el
    formulario de refutaciones ya existente."""
    p = product_catalog.obtener(db_path, producto_id)
    if not p:
        raise KeyError("Producto no encontrado")

    contexto = _contexto_producto(p)
    bruto = chat(
        task="refutar_producto",
        system_prompt=SYSTEM_PROMPT,
        user_message="Datos del producto:\n" + json.dumps(contexto, ensure_ascii=False),
        max_tokens=1536,
        temperature=0.1,
    )
    refutaciones = _parsear(bruto)
    sin_datos = sum(1 for r in refutaciones if r["veredicto"] == "sin_datos")
    return {
        "producto_id": producto_id,
        "refutaciones": refutaciones,
        "completo": sin_datos == 0,
        "sin_datos": sin_datos,
        "generado": bool(bruto),
    }
