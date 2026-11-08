# /configurar-tienda

Lee `ai_workspace/skills/configurar_tienda/procedimiento.md` y guía al usuario por el checklist completo de configuración inicial de Shopify.

## Conectores a activar automáticamente
- **Stripe** (`mcp__1cc6d3ec`): verificar que el método de pago está conectado antes de marcar el paso de pagos como completo
- **Google Sheets** (`mcp__69f3b6ec`): registrar fecha de configuración en Dashboard GEM OS tab "Pipeline"

## Skills Claude a cargar
- `artifact-design` → generar checklist visual como artefacto si el usuario lo pide
- `artifact-capabilities` → si el artefacto necesita estado persistente (checkboxes guardados)

## Flujo
1. Preguntar: ¿qué pasos ya están completados?
2. Ejecutar el procedimiento desde el primer paso pendiente
3. Para el paso de Stripe/Pagos: verificar con `stripe_api_read` que la cuenta está activa
4. Para el paso de píxeles: recordar que TikTok Pixel debe instalarse antes de `/tiktok-ads`
5. Emitir JSON de output con `listo_para_trafico: true/false`

## Regla crítica
No marcar `listo_para_trafico: true` hasta que los 3 píxeles (Meta, Google, TikTok) estén verificados.
