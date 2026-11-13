---
name: redactar-ficha-shopify
description: "Genera ficha completa de producto para Shopify. Usar cuando el usuario hable de: ficha shopify, descripción producto, título SEO."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/redactar-ficha-shopify.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /redactar-ficha-shopify

Lee `referencias/redactar_ficha_shopify.md` y genera ficha completa de producto para Shopify (v2.0: multi-ángulo AIDA + SEO enriquecido).

## Conectores a activar automáticamente
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): OBLIGATORIO — usar `keywords-explorer-overview` para el keyword principal del producto y `keywords-explorer-matching-terms` para keywords long-tail. Cargar `doc` antes de la primera llamada. Las keywords de mayor volumen van en título y primeros 150 chars de descripción.
- **Google Sheets**: si hay fichas anteriores del mismo nicho en Dashboard, leerlas para mantener coherencia de tono y keywords
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
