# Skill: Importación Masiva de Productos (`/importar-masivo`)

## Propósito
Importar varios productos de AliExpress, CJ Dropshipping o Temu en un paso: valida cada uno sobre su coste landed y crea BORRADORES en Shopify. Los borradores no se publican hasta tener la ficha real.

## Entrada (una línea por producto)
```
URL  coste  envío  [img=URL …]  [var=Opción:valor/valor …]
```
| Campo | Regla |
|-------|-------|
| `coste` | Precio del producto en la divisa del proveedor (USD por defecto). Obligatorio |
| `envío` | Coste de envío del proveedor. Obligatorio; `0` solo si el envío es gratis |
| `img=URL` | Opcional, repetible. Manda sobre las imágenes que se lean de la página (máx. 10, solo http/https) |
| `var=Color:Rojo/Azul` | Opcional, hasta 3 opciones y 100 variantes (producto cartesiano), todas al mismo precio. `_` = espacio |
| divisa | Se convierte al tipo del día (`fx_rates`) a la divisa REAL de la tienda, leída de Shopify |

Falta coste o envío → `DATA_GAP_REQUEST` (status `skipped`), no se estima.

**Imágenes y variantes — qué es automático y qué no.** AliExpress y Temu devuelven captcha a los scripts
(comprobado), así que sin `img=` normalmente no hay imágenes automáticas, y las variantes NUNCA se deducen del
HTML (sería inventar datos): vienen de `var=`. Para extraer fotos y variantes reales de un proveedor, usa el
conector AutoDS MCP. Shopify descarta en silencio las imágenes que no puede bajar (p. ej. Wikimedia): tras el lote
se consulta cuántas se adjuntaron de verdad y se avisa («Shopify solo aceptó 0 de 1»).

## Flujo
```
línea → detectar_plataforma (por HOST real) / extraer_product_id
      → ¿URL ya importada?                 → skipped (duplicado)
      → divisa de la tienda (Shopify shop_info)
      → FinancialValidator.validar_producto(coste, envío, monedas)
            multiplicador sobre coste LANDED; < x2 → skipped
      → precio ,99 (sube al siguiente ,99, nunca por debajo del x3) y se REVALIDA con el PVP final
      → deterministic_gate.verificar_validacion_financiera   → error si no cuadra
      → página (solo plataformas conocidas, sin redirecciones a otros hosts): título + imágenes
            captcha → «Producto <id> (revisar título)»
      → ShopifyClient.create_draft_product (descripción neutra, imágenes, variantes, tags)
      → importaciones_masivas
      → verificación de imágenes (una espera por lote)
      → fila en Google Sheets «Pipeline» (opcional; un fallo de Sheets no deshace el borrador)
```

**Fila en Pipeline:** SKU = ID del producto; «Costo Origen» = coste LANDED ya convertido a la divisa de la
tienda (así PVP/coste = multiplicador validado); «Categoria» = `importación · <plataforma> · borrador <id>`.

## Reglas aplicadas (Adrián Sáenz `Q4Ykcwh5Osc 24:40`)
- Mínimo **x2** sobre coste landed (rechaza); objetivo **x3** (PVP calculado = landed × 3).
- Coste fuera de $5–15 → advertencia en la validación, no rechazo.
- Baterías de litio sueltas: prohibidas; la URL no permite detectarlo, lo comprueba quien importa.
- El curso no fija umbral de margen ni límite de peso: no se aplican.

## Descripción del borrador
Siempre neutra («Borrador pendiente de ficha de producto»): el borrador puede acabar publicado y no debe mostrar proveedor, URL de origen ni cálculos internos. La URL de origen queda solo en la tabla `importaciones_masivas`.

## Estados
| Status | Significado |
|--------|-------------|
| `success` | Borrador creado en Shopify |
| `skipped` | DATA_GAP, duplicado o por debajo de x2 |
| `error` | Gate determinista no cuadra, Shopify sin configurar o fallo de API |

## Código
- Servicio: `app/services/bulk_url_importer.py` → `BulkUrlImporter.previsualizar(...)` (no crea nada) e `importar_lote(items, moneda_costo, etiqueta_lote, precio_psico, sincronizar_hoja)`; máx. 50 productos por lote
- Shopify: `app/services/shopify_client.py` → `create_draft_product(…, opciones=)`, `eliminar_producto` (scope `write_products`)
- Sheets: `app/services/google_sheets_live.py` → `upsert_producto_pipeline` (gspread 6: `find()` devuelve None)
- Escritorio: `app/ui/components/bulk_import_panel.py` (Tienda → Importación masiva)
- Web: `/importacion` + `app/routes/importacion.py` (`/api/importacion/{estado,previsualizar,importar,historial}`)
- BD: tabla `importaciones_masivas` (migración 0013)
- Tests: `tests/test_bulk_url_importer.py`, `tests/test_google_sheets_pipeline.py`

## Etiqueta de lote
`etiqueta_lote` (p. ej. `test-2026-11`) se añade a los tags de Shopify para filtrar o borrar en bloque los productos que no funcionen.

## Entorno
`SHOPIFY_STORE_URL` (dominio `.myshopify.com`) + `SHOPIFY_CLIENT_ID` + secreto de la app en `.env` (ver `shopify_client.credenciales`).
