# /redactar-ficha-shopify

Lee `ai_workspace/skills/redactar_ficha_shopify/procedimiento.md` y genera ficha completa de producto para Shopify (v2.0: multi-ángulo AIDA + SEO enriquecido).

## Conectores a activar automáticamente
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): OBLIGATORIO — usar `keywords-explorer-overview` para el keyword principal del producto y `keywords-explorer-matching-terms` para keywords long-tail. Cargar `doc` antes de la primera llamada. Las keywords de mayor volumen van en título y primeros 150 chars de descripción.
- **Google Sheets** (`mcp__69f3b6ec`): si hay fichas anteriores del mismo nicho en Dashboard, leerlas para mantener coherencia de tono y keywords
- **Figma** (`mcp__plugin_marketing_figma`): si el usuario pide mockup visual de la ficha, generar diseño de la página en Figma

## Skills Claude a cargar
- `artifact-design` → SIEMPRE — generar la ficha como artefacto HTML/visual completo y listo para copiar a Shopify
- `dataviz` → si hay comparaciones de precio o especificaciones técnicas que se beneficien de tabla visual

## Estructura AIDA (v2.0)
1. **Atención** — Título SEO: 6-8 palabras, keyword principal al inicio
2. **Interés** — 3 beneficios con emojis funcionales (no decorativos), bullets cortos
3. **Deseo** — Especificaciones técnicas exactas del proveedor (prohibido alterar), foto/video demostrativo
4. **Acción** — CTA + garantía real + política devoluciones

## Reglas (INMUTABLES — Funnel Builder)
- Prohibido alterar dimensiones, pesos o materiales del proveedor
- Días de envío: usar los días reales del proveedor (2-5 días hábiles Shopify; 5-7 días TikTok Shop). Nunca prometer 24-48h sin confirmación
- Sin superlativos vacíos: "increíble", "revolucionario", "el mejor"
- Pasar por `deterministic_gate.py` antes de publicar — verificar specs_inmutables y promesas_envio
