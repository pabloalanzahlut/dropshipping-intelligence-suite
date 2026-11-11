# Skill: Importación Masiva de Productos (`/importar-masivo`)

## Propósito
Importar varios productos de AliExpress, CJ Dropshipping o Temu en un paso: valida cada uno sobre su coste landed y crea BORRADORES en Shopify. Los borradores no se publican hasta tener la ficha real.

## Entrada (una línea por producto)
```
URL  coste  envío
```
| Campo | Regla |
|-------|-------|
| `coste` | Precio del producto en la divisa del proveedor (USD por defecto). Obligatorio |
| `envío` | Coste de envío del proveedor. Obligatorio; `0` solo si el envío es gratis |
| divisa | Se convierte al tipo del día (`fx_rates`) a la divisa REAL de la tienda, leída de Shopify |

Falta coste o envío → `DATA_GAP_REQUEST` (status `skipped`), no se estima.

## Flujo
```
línea → detectar_plataforma / extraer_product_id
      → ¿URL ya importada?                 → skipped (duplicado)
      → divisa de la tienda (Shopify shop_info)
      → FinancialValidator.validar_producto(coste, envío, monedas)
            multiplicador sobre coste LANDED; < x2 → skipped
      → deterministic_gate.verificar_validacion_financiera   → error si no cuadra
      → título (<title>; si hay captcha: «Producto <id> (revisar título)»)
      → ShopifyClient.create_draft_product (descripción neutra)
      → importaciones_masivas
```

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
- Servicio: `app/services/bulk_url_importer.py` → `BulkUrlImporter.importar_lote(items, moneda_costo, etiqueta_lote)`
- Shopify: `app/services/shopify_client.py` → `create_draft_product` (scope `write_products`)
- UI: `app/ui/components/bulk_import_panel.py` (escritorio: Tienda → Importación masiva)
- BD: tabla `importaciones_masivas` (migración 0013)
- Tests: `tests/test_bulk_url_importer.py`

## Etiqueta de lote
`etiqueta_lote` (p. ej. `test-2026-11`) se añade a los tags de Shopify para filtrar o borrar en bloque los productos que no funcionen.

## Entorno
`SHOPIFY_STORE_URL` (dominio `.myshopify.com`) + `SHOPIFY_CLIENT_ID` + secreto de la app en `.env` (ver `shopify_client.credenciales`).
