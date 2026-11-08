# /tiktok-ads

Lee `ai_workspace/skills/tiktok_ads/procedimiento.md` y configura/gestiona campañas de TikTok Ads pagados.

## Conectores a activar automáticamente
- **Google Sheets** (`mcp__69f3b6ec`): registrar métricas de campaña (CPM, CTR, CVR, ROAS TikTok vs ROAS Shopify) en Dashboard tab "TikTok Ads"
- **Stripe** (`mcp__1cc6d3ec`): cruzar revenue declarado por TikTok con `stripe_analytics` para verificar atribución real (TikTok sobreestima)

## Skills Claude a cargar
- `dataviz` → SIEMPRE si hay métricas de campaña
- `artifact-design` → si se genera estructura de campaña o análisis como artefacto

## Diferencia clave con `/publicar-tiktok`
Este skill es para **ads de pago** con pixel de conversión. `/publicar-tiktok` es publicación orgánica gratuita vía Make.com.

## Flujo
1. Verificar que el pixel TikTok está instalado (prerrequisito de `/configurar-tienda`)
2. Si no está instalado → redirigir a `/configurar-tienda` paso "Píxeles"
3. Configurar campaña según el procedimiento
4. Registrar en Google Sheets
5. Alertar si ROAS TikTok difiere >30% del ROAS Shopify (señal de atribución inflada)

## Regla de ROAS
ROAS mínimo = 2 sobre coste landed (Adrián Sáenz). Cruzar siempre con Shopify como fuente de verdad.
