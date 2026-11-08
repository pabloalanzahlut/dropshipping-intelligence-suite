# /monitorear-skool

Lee `ai_workspace/skills/monitorear_skool/procedimiento.md`. El agente Dr. Marcus Chen analiza posts de Comunidad Ecommerce Skool → extrae productos ganadores → KB.

## Conectores a activar automáticamente
- **Google Sheets** (`mcp__69f3b6ec`): escribir productos ganadores extraídos en Dashboard tab "Pipeline" — columnas: producto, fuente_skool, fecha_post, clasificacion_preliminar, URL_proveedor_sugerida
- **Google Drive** (`mcp__73e33a54`): guardar el reporte completo de Skool como archivo en Drive para referencia futura

## Skills Claude a cargar
- `artifact-design` → generar el reporte de productos ganadores como artefacto visual compartible
- `dataviz` → si hay tendencias de múltiples posts, visualizar productos por frecuencia de mención

## Fuentes de datos
- `ai_workspace/knowledge_base/skool_productos.json` — base de datos de productos ya extraídos
- `ai_workspace/scripts/skool_scraper.py` — script de extracción autenticada (requiere cookies de sesión)

## Output esperado por producto
```json
{
  "producto": "nombre",
  "fuente": "skool_post_url",
  "fecha": "YYYY-MM-DD",
  "precio_sugerido_venta": null,
  "proveedor_sugerido": "AliExpress/CJ/Temu",
  "clasificacion_preliminar": "WARM",
  "notas": "contexto del post"
}
```

## Siguiente paso
Todo producto extraído de Skool va directamente a `/clasificar-producto` para validación financiera.
