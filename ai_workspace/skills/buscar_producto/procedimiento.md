# Skill: Buscar Producto Ganador (Mobile-First)

**ID:** `buscar_producto`
**Versión:** 1.0.0
**Propósito:** Descubrir productos candidatos a dropshipping usando AutoDS Trending, Shopify Analytics móvil y Ad Spy, aplicando pre-filtrado financiero antes de pasar al clasificador.

**Trigger:** Manual vía `/buscar-producto` o automático desde el Orchestrator Core.
**Output destino:** `clasificar_productos` (handoff directo) + `ai_workspace/projects/producto_01/market_analysis.json`

---

## Reglas de Pre-filtrado (INMUTABLES — igual que clasificar_productos)

| Criterio | Umbral | Acción si falla |
|----------|--------|-----------------|
| Baterías de litio sueltas | Prohibido | DESCARTAR |
| Categorías prohibidas | Armas, adultos, medicamentos | DESCARTAR |

---

## Fase 1 — AutoDS Trending Products

### Pasos
1. Abrir AutoDS app móvil → sección **Trending Products** o **TikTok Analytics**
2. Aplicar filtros:
   - Categoría: Electronics / Home & Living / Fitness / Pet Supplies (únicas permitidas para HOT)
   - Tendencia: ordenar por "más viral" o "crecimiento últimas 24h"
   - Coste: filtrar $5-15 (Q4Ykcwh5Osc 17:50)
3. Para cada producto candidato, registrar:
   - Nombre del producto
   - Precio del proveedor (costo origen)
   - Precio de venta sugerido por AutoDS
   - Peso declarado por el proveedor
   - País de origen del proveedor
   - Número de pedidos últimos 30 días
4. Aplicar pre-filtrado: descartar cualquier producto que falle alguna regla de la tabla anterior
5. Pasar máximo **5 candidatos** a la Fase 2

### Señales de producto HOT en AutoDS
- Órdenes últimos 30 días: >500
- Aparece en sección TikTok Analytics
- Rating proveedor: ≥ 4.5 estrellas
- Stock disponible: >100 unidades

---

## Fase 2 — Shopify Analytics Móvil

### Propósito
Validar que el contexto actual de la tienda es compatible con los candidatos (tráfico disponible, categorías que ya convierten, AOV objetivo).

### Pasos
1. Abrir app Shopify → **Analytics** → panel del día
2. Registrar las siguientes métricas de contexto:
   - **Conversion rate actual** de la tienda (referencia de expectativa)
   - **AOV (Average Order Value)** — el precio de venta del candidato debe estar dentro del ±30% del AOV actual
   - **Top fuentes de tráfico** — confirmar que hay tráfico compatible con la categoría del candidato
   - **Categoría que más convierte hoy** — priorizar candidatos de esa categoría
3. Revisar **Shopify Inbox**: si hay preguntas frecuentes sobre un tipo de producto, ese pain point es señal de oportunidad
4. Ajustar la lista de candidatos: si el AOV del candidato supera AOV+30%, marcar como RIESGO_PRECIO

### Métricas de alerta
- Conversion rate < 1%: advertir, no descartar
- AOV candidato > AOV actual × 1.5: marcar RIESGO_PRECIO en el output

---

## Fase 3 — AutoDS Ad Spy (Espionaje de Anuncios)

### Propósito
Validar que el mercado ya tiene demanda probada analizando los anuncios activos de la competencia.

### Pasos
1. Para cada candidato que supera Fases 1 y 2:
   - Abrir AutoDS Ad Spy → buscar el producto por nombre/categoría
   - Plataformas a revisar: Facebook Ads, Instagram Ads, TikTok Ads
2. Para cada anuncio encontrado, registrar:
   - **Hook (primeros 3 segundos)**: ¿es visual o verbal? ¿problema o solución?
   - **Formato**: video corto (15-30s) / imagen / carrusel
   - **Copy principal**: ¿usa urgencia? ¿garantía? ¿comparación?
   - **CTA**: "Shop Now" / "Get Yours" / "Order Today" / otro
   - **Engagement estimado**: likes/comentarios si es visible
   - **Antigüedad del anuncio**: si lleva >30 días activo = producto probado
3. Señales de validación (mercado probado):
   - Anuncio activo hace >30 días: fuerte señal positiva
   - Múltiples anunciantes para el mismo producto: mercado saturado (revisar diferenciación)
   - Solo 1-2 anunciantes: oportunidad de entrar
4. Registrar `notas_ad_spy` con el resumen de hallazgos

---

## Output JSON

```json
{
  "busqueda_id": "BSQ-{YYYYMMDD}-{NNN}",
  "fecha": "YYYY-MM-DD",
  "fuente": "autods_trending | autods_adspy | shopify_analytics",
  "producto_candidato": {
    "nombre": "",
    "categoria": "",
    "pais_origen": "",
    "peso_kg": 0.0,
    "tiene_bateria_litio": false
  },
  "financiero": {
    "precio_proveedor_estimado": 0.00,
    "precio_competencia": 0.00,
    "margen_calculado": 0.0,
    "ratio_x": 0.0,
    "aov_tienda_actual": 0.00,
    "riesgo_precio": false
  },
  "autods_metrics": {
    "ordenes_30d": 0,
    "rating_proveedor": 0.0,
    "stock_disponible": 0,
    "aparece_tiktok_analytics": false
  },
  "notas_ad_spy": {
    "anuncios_encontrados": 0,
    "plataformas": [],
    "anuncio_mas_antiguo_dias": 0,
    "hook_dominante": "",
    "formato_dominante": "",
    "cta_dominante": "",
    "nivel_competencia": "bajo | medio | alto"
  },
  "clasificacion_preliminar": "HOT | WARM | COLD | DISCARD",
  "apto_para_clasificador": true,
  "notas_operador": ""
}
```

### Regla de `clasificacion_preliminar`
- `HOT`: ratio_x ≥ 5.0 y anuncios_encontrados ≥ 1 y anuncio_mas_antiguo_dias ≥ 30
- `WARM`: ratio_x ≥ 3.0 y ratio_x < 5.0
- `COLD`: ratio_x ≥ 1.5 y ratio_x < 3.0
- `DISCARD`: ratio_x < 1.5 o falla cualquier regla de pre-filtrado

---

## Handoff al Clasificador

Si `apto_para_clasificador = true`:
1. Guardar el JSON en `ai_workspace/projects/producto_01/market_analysis.json`
2. Notificar a Orchestrator Core → trigger `/clasificar-producto`
3. Incluir en el handoff: `busqueda_id`, `clasificacion_preliminar`, `notas_ad_spy`

Si `apto_para_clasificador = false`:
- Registrar en `ai_workspace/memory/productos_descartados.json` con motivo
- No avanzar en el pipeline



