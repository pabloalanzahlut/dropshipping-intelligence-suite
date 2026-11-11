# /importar-masivo

Lee `ai_workspace/skills/importar_masivo/procedimiento.md` y procesa productos de AliExpress/CJ/Temu → valida sobre coste landed → crea BORRADORES en Shopify (Admin API, `shopify_client.py`).

## Datos que debe dar el usuario (regla suprema: no inventar)
Una línea por producto: `URL  coste  envío`. Si falta el coste o el envío de cualquier producto → `DATA_GAP_REQUEST`: pedirlo, no estimarlo (envío `0` solo si el proveedor lo da gratis).

## Conectores a activar automáticamente
- **Google Sheets** (`mcp__69f3b6ec`): tras la importación, escribir en Dashboard tab "Pipeline" — URL, coste_landed, PVP_mínimo (2x), PVP_objetivo (3x), estado, borrador Shopify
- **Stripe** (`mcp__1cc6d3ec`): si ya hay productos activos, `stripe_analytics` para comparar márgenes reales vs proyectados

## Skills Claude a cargar
- `dataviz` → tabla visual válidos vs omitidos
- `artifact-design` → si se genera un informe como artefacto

## Flujo
1. `BulkUrlImporter.importar_lote(items, moneda_costo, etiqueta_lote)` (`app/services/bulk_url_importer.py`)
2. Por producto: coste landed = (producto + envío) × tipo de cambio del día → divisa REAL de la tienda (se lee de Shopify, no se asume)
3. Mínimo x2 rechaza; x3 es el objetivo (Adrián Sáenz `Q4Ykcwh5Osc 24:40`)
4. `deterministic_gate` recalcula el multiplicador; si no cuadra → error, no se crea nada
5. Borrador con descripción neutra (sin proveedor ni URL de origen); la ficha real va después con `/redactar-ficha-shopify`
6. URLs ya importadas se omiten (duplicado); todo queda en `importaciones_masivas`

Pantalla de escritorio: **Tienda → Importación masiva**.

## Antes de importar (pipeline, sin saltar pasos)
El producto debe haber pasado `/clasificar-producto` → `/refutar-producto` → `/validar-financiero` → creativo validado.
