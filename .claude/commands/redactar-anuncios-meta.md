# /redactar-anuncios-meta

Lee `ai_workspace/skills/redactar_anuncios_meta/procedimiento.md` y genera copy para Meta Ads estáticos.

## Conectores a activar automáticamente
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): usar `content-helper-topics` para identificar los pain points más buscados del producto. Cargar `doc` antes de la primera llamada.
- **Google Sheets** (`mcp__69f3b6ec`): si hay datos de campañas anteriores en Dashboard, leerlos para informar el copy con métricas reales
- **Figma** (`mcp__plugin_marketing_figma`): si el usuario pide mockup visual del anuncio, generar diseño en Figma

## Skills Claude a cargar
- `artifact-design` → generar los anuncios como artefacto visual si hay imágenes
- `dataviz` → si hay métricas de A/B test para visualizar

## Tipos de anuncio que genera
1. **Imagen única** — headline 5-7 palabras + texto principal 125 chars + CTA
2. **Carousel** — 3-5 tarjetas con beneficio progresivo
3. **Variantes A/B** — mínimo 2 variantes de headline y texto por anuncio

## Reglas (INMUTABLES)
- Prohibido superlativos vacíos: "increíble", "revolucionario", "el mejor"
- Prohibido promesas de envío sin confirmar con el proveedor
- Siempre incluir garantía real (si existe) o política de devoluciones
- Copy basado en pain points reales del nicho (usar Ahrefs para validar)
