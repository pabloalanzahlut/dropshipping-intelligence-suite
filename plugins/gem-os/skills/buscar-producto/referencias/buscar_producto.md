# Skill: Buscar Producto Ganador

**ID:** `buscar_producto`
**Versión:** 2.0.0
**Actualizado:** 2026-11-11
**Propósito:** Descubrir candidatos a dropshipping aplicando pre-filtrado financiero correcto (coste landed, no coste suelto) antes de pasar al clasificador.

**Trigger:** Manual vía `/buscar-producto` o automático desde el Orchestrator Core.
**Output destino:** `clasificar_productos` (handoff directo) + `contexto/proyecto_activo/market_analysis.json`

---

## Reglas de Pre-filtrado (INMUTABLES)

Fuente: CLAUDE.md v3.0 — Adrián Sáenz `Q4Ykcwh5Osc 17:50 y 24:40`

| Criterio | Umbral | Acción si falla |
|----------|--------|-----------------|
| Multiplicador mínimo | PVP ≥ 2× **coste landed** (producto + envío) | DESCARTAR |
| Multiplicador objetivo | PVP ≥ 3× **coste landed** | Clasifica COLD si queda entre 2-3× |
| Coste de origen | $5–15 | DESCARTAR fuera de rango |
| Baterías de litio sueltas | Prohibido | DESCARTAR |
| Categorías prohibidas | Armas, adultos, medicamentos | DESCARTAR |

**Lo que el curso NO menciona (no aplicar):** umbral de margen %, límite de peso en kg.

**El multiplicador va sobre coste landed, nunca sobre el producto solo.**
Ejemplo: $5 producto + $2 envío = landed $7 → PVP mínimo 2× = $14 · objetivo 3× = $21.
Un coste $5 vendido a $15 aparenta 3× cuando es 2,14× sobre landed.

---

## Clasificación

| Clasificación | Multiplicador sobre landed |
|--------------|---------------------------|
| HOT          | ≥ 5×                      |
| WARM         | 3–5×                      |
| COLD         | 2–3×                      |
| DISCARD      | < 2×                      |

---

## Nichos objetivo

Fuente: `Q4Ykcwh5Osc 17:04:27` — confirmado por el usuario 2026-11-12

1. **Salud**
2. **Cuidado de las personas**
3. **Belleza**

Priorizar productos con factor WOW visual (se demuestran solos en video) y precio de venta < $40 para compra por impulso.

---

## Vía 1 — MCP oficial de AutoDS (preferente)

El MCP de AutoDS está disponible en esta sesión. Usar siempre que el conector responda; cubre 8M de productos sin scraping manual.

### Búsqueda de winning products

```
get_winning_products(
    offset=0,
    limit=20,
    sort="-orders_count",
    item_cost="5-15",
    orders=70
)
```

### Búsqueda por nicho en el catálogo

```
search_products(body={
    "order_by": {"name": "spv_param", "direction": "desc"},
    "filters": [
        {"name": "search_query", "value": "<nicho>", "value_type": "string", "op": "search"},
        {"name": "variations.variation_details.price", "value": "5,15", "value_type": "float", "op": "between"}
    ]
})
```

Pasar máximo **5 candidatos** a la Fase de Validación Financiera.

---

## Vía 2 — AutoDS Trending Products (si el MCP no responde)

### Filtros confirmados (probados el 2026-11-11)

| Filtro | Valor | Nota |
|--------|-------|------|
| **Sell Price Range** | **5-15** | Obligatorio |
| **Sold Range** | **More than 10 000** | Obligatorio |
| Likes | vacío | Combinarlo da 0 resultados |
| Impressions | vacío | Combinarlo da 0 resultados |
| Interaction Rate | vacío | Combinarlo da 0 resultados |
| Profit Range | vacío | — |
| Last Comment Time | vacío | — |

> Estos filtros se combinan con AND. Añadir más sin verificar puede dar 0 resultados.

**Sort By:** `Sold Growth % (last 7d)` — opción real de la interfaz; equivale a "más viral".

**Categorías a explorar (en orden):** Pets · Home & Garden · Sports & Fitness · Toys & Hobbies · Beauty & Personal Care.

### Señales de producto HOT en Trending

- Sold: >10 000 (ya garantizado por el filtro)
- Aparece en sección TikTok Analytics: sí
- Rating proveedor: ≥ 4,5 estrellas
- Stock disponible: >100 unidades

---

## Fase final — Validación financiera obligatoria

Antes de pasar al clasificador, calcular el multiplicador real sobre coste landed:

```python
from app.services.financial_validator import FinancialValidator
v = FinancialValidator()
r = v.validar_producto(
    sku,
    costo_origen=coste_producto,
    costo_envio=coste_envio_real,   # DATA_GAP si no se tiene
    pvp_sugerido=pvp,
    moneda_costo="USD",
    moneda_pvp="EUR"
)
```

**Si no se tiene el coste de envío al destino real (UE/Italia): DATA_GAP — no asumir $0 ni inventar.**

---

## Ad Spy (antes del handoff)

Para cada candidato que supera el filtro financiero:

1. AutoDS Ad Spy → buscar por nombre/categoría
2. Plataformas: Facebook Ads, TikTok Ads
3. Registrar:
   - Anuncio activo >30 días → mercado probado ✅
   - Solo 1–2 anunciantes → oportunidad de entrada ✅
   - Muchos anunciantes → evaluar diferenciación antes de continuar

---

## Output JSON

```json
{
  "busqueda_id": "BSQ-{YYYYMMDD}-{NNN}",
  "fecha": "YYYY-MM-DD",
  "via": "autods_mcp | autods_trending",
  "producto_candidato": {
    "nombre": "",
    "categoria": "",
    "pais_origen": "",
    "tiene_bateria_litio": false
  },
  "financiero": {
    "costo_producto_usd": 0.00,
    "costo_envio_usd": 0.00,
    "costo_landed_usd": 0.00,
    "pvp_eur": 0.00,
    "tipo_cambio_usado": 0.0,
    "multiplicador_x": 0.0,
    "data_gap_envio": false
  },
  "autods_metrics": {
    "ordenes_totales": 0,
    "rating_proveedor": 0.0,
    "stock_disponible": 0,
    "aparece_tiktok_analytics": false
  },
  "notas_ad_spy": {
    "anuncios_encontrados": 0,
    "plataformas": [],
    "anuncio_mas_antiguo_dias": 0,
    "hook_dominante": "",
    "nivel_competencia": "bajo | medio | alto"
  },
  "clasificacion_preliminar": "HOT | WARM | COLD | DISCARD",
  "apto_para_clasificador": true,
  "notas_operador": ""
}
```

### Regla de `clasificacion_preliminar` (siempre sobre coste landed)

- `HOT`: multiplicador_x ≥ 5,0
- `WARM`: multiplicador_x ≥ 3,0 y < 5,0
- `COLD`: multiplicador_x ≥ 2,0 y < 3,0
- `DISCARD`: multiplicador_x < 2,0 o falla cualquier regla de pre-filtrado

---

## Handoff al Clasificador

Si `apto_para_clasificador = true`:
1. Guardar el JSON en `contexto/proyecto_activo/market_analysis.json`
2. Trigger `/clasificar-producto`
3. Incluir: `busqueda_id`, `clasificacion_preliminar`, `notas_ad_spy`

Si `apto_para_clasificador = false`:
- Registrar en `ai_workspace/memory/productos_descartados.json` con motivo
- No avanzar en el pipeline
