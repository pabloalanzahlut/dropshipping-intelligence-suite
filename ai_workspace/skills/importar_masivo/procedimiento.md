# Skill: Importación Masiva de Productos (`/importar-masivo`)

## Propósito
Importar múltiples productos desde AliExpress, CJ Dropshipping o Temu en un solo paso, validando la regla 3x y creando borradores directamente en Shopify.

## Activación
```
/importar-masivo
```

## Inputs requeridos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `urls` | lista | Una URL por línea de producto |
| `costo_origen` | float | Costo de compra en USD (DATA_GAP_REQUEST si falta) |
| `peso_kg` | float | Peso estimado (default: 0.3 kg) |

## Flujo de ejecución

```
URLs pegadas
    ↓
detectar_plataforma()  →  aliexpress | cjdropshipping | temu | desconocida
    ↓
extraer_product_id()
    ↓
FinancialValidator.validar_producto()
    ├── FALLA regla 3x  →  status=skipped
    ├── FALLA peso       →  status=skipped
    └── OK               →  continuar
              ↓
scrape_titulo_basico()
              ↓
ShopifyClient.create_draft_product()
              ↓
guardar en tabla importaciones_masivas
```

## Reglas de negocio aplicadas
- **Regla 3x**: PVP = costo_origen × 3 (mínimo)
- **Baterías de litio**: categoría prohibida → RECHAZAR

## Outputs
```json
[
  {
    "url": "https://aliexpress.com/item/...",
    "plataforma": "aliexpress",
    "product_id": "12345678",
    "status": "success",
    "shopify_draft_id": "7891234567890",
    "error": null
  }
]
```

## Estados posibles
| Status | Significado |
|--------|-------------|
| `success` | Borrador creado en Shopify |
| `skipped` | No cumple reglas financieras o DATA_GAP_REQUEST |
| `error` | Error técnico (Shopify API, red) |

## Código de referencia
- Servicio: `app/services/bulk_url_importer.py` → `BulkUrlImporter.importar_lote()`
- Shopify: `app/services/shopify_client.py` → `ShopifyClient.create_draft_product()`
- UI: `app/ui/components/bulk_import_panel.py`
- BD: tabla `importaciones_masivas` (migración 0013)

## Variables de entorno requeridas
```
SHOPIFY_STORE_URL=https://tu-tienda.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxx
```


