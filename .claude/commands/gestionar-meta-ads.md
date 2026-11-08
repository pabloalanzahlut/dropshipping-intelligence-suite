# /gestionar-meta-ads

Lee `ai_workspace/skills/gestionar_meta_ads/procedimiento.md` y genera naming de campañas + hooks s0–s3 estilo Roger Viladrosa.

## Conectores a activar automáticamente
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): usar `content-helper-topics` para identificar los pain points más resonantes del nicho — alimentan los hooks s0–s3. Cargar `doc` antes de la primera llamada.
- **Google Sheets** (`mcp__69f3b6ec`): escribir la estructura de campaña en Dashboard tab "Pipeline" — columnas: campaña, ad_set, hook_code, estado
- **Figma** (`mcp__plugin_marketing_figma`): si se pide mockup de los creativos, generar diseño de los anuncios en Figma

## Skills Claude a cargar
- `artifact-design` → generar la estructura de campaña como artefacto compartible
- `dataviz` → si hay métricas previas de hooks, visualizar CTR por fórmula

## Naming convention Roger Viladrosa
```
[PAÍS]-[OBJETIVO]-[PRODUCTO]-[AUDIENCIA]-[FECHA]
Ejemplo: ES-VTA-MASAJEADOR-LOOKALIKE-241108
```

## Estructura de hooks s0–s3
- **s0** (awareness): presentar el problema sin mencionar el producto
- **s1** (interés): mostrar la solución de forma visual en 3s
- **s2** (consideración): prueba social o demostración real
- **s3** (conversión): CTA directo con urgencia o garantía

## Regla
Mínimo 3 variantes de hook por nivel para test A/B. Sin superlativos vacíos.
