# /importar-masivo

Lee `ai_workspace/skills/importar_masivo/procedimiento.md` y procesa productos de AliExpress/CJ/Temu → valida sobre coste landed → crea BORRADORES en Shopify (Admin API, `shopify_client.py`).

## Datos que debe dar el usuario (regla suprema: no inventar)
Una línea por producto: `URL  coste  envío  [img=URL]  [var=Color:Rojo/Azul]`. Si falta el coste o el envío de cualquier producto → `DATA_GAP_REQUEST`: pedirlo, no estimarlo (envío `0` solo si el proveedor lo da gratis). Imágenes y variantes: solo las que el usuario indique o las que aporte el conector AutoDS MCP; nunca se deducen.

## Conectores
- **Google Sheets**: la propia importación anota cada borrador creado en Pipeline (`sincronizar_hoja=True`); no hace falta escribirlo a mano. Solo usar el conector MCP (`mcp__69f3b6ec`) si el servicio responde `error:` en la columna Sheets.
- **Stripe** (`mcp__1cc6d3ec`): si ya hay productos activos, `stripe_analytics` para comparar márgenes reales vs proyectados

## Skills Claude a cargar
- `dataviz` → tabla visual válidos vs omitidos
- `artifact-design` → si se genera un informe como artefacto

## Flujo
1. `BulkUrlImporter.importar_lote(items, moneda_costo, etiqueta_lote)` (`app/services/bulk_url_importer.py`)
2. Por producto: coste landed = (producto + envío) × tipo de cambio del día → divisa REAL de la tienda (se lee de Shopify, no se asume)
3. Mínimo x2 rechaza; x3 es el objetivo (Adrián Sáenz `Q4Ykcwh5Osc 24:40`)
4. `deterministic_gate` recalcula el multiplicador; si no cuadra → error, no se crea nada
5. Precio ,99 (nunca por debajo del x3) y revalidación con el PVP final
6. Borrador con descripción neutra (sin proveedor ni URL de origen), imágenes y variantes; la ficha real va después con `/redactar-ficha-shopify`
7. URLs ya importadas se omiten (duplicado); todo queda en `importaciones_masivas`; se informa de cuántas imágenes aceptó Shopify de verdad

Pantallas: escritorio **Tienda → Importación masiva** · web **/importacion** (con «Previsualizar», que no crea nada).

## Antes de importar (pipeline, sin saltar pasos)
El producto debe haber pasado `/clasificar-producto` → `/refutar-producto` → `/validar-financiero` → creativo validado.
