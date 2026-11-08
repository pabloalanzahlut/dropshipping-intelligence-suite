# /google-ads

Lee `ai_workspace/skills/google_ads/procedimiento.md` y configura/optimiza campañas de Google Ads.

## Conectores a activar automáticamente
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): SIEMPRE invocar `keywords-explorer-overview` para el producto antes de proponer keywords. Usar `keywords-explorer-matching-terms` para encontrar variaciones. Cargar también `mcp__plugin_marketing_ahrefs__doc` la primera vez.
- **Google Sheets** (`mcp__69f3b6ec`): registrar métricas de campaña (CTR, CPC, ROAS) en Dashboard tab "Google Ads"
- **Stripe** (`mcp__1cc6d3ec`): si el usuario pega datos de revenue, cruzar con `stripe_analytics` para verificar atribución real

## Skills Claude a cargar
- `dataviz` → SIEMPRE cargar si hay métricas de campaña para visualizar
- `artifact-design` → si se genera estructura de campaña como artefacto

## Flujo con Ahrefs (obligatorio para keywords)
1. Recibir producto/nicho del usuario
2. Invocar `keywords-explorer-overview` con el producto como query, país del mercado
3. Invocar `keywords-explorer-matching-terms` para variaciones
4. Filtrar: volumen >500/mes, intención de compra (comprar/precio/oferta)
5. Proponer estructura de grupos de anuncios con keywords reales
6. Registrar en Google Sheets

## Regla de ROAS
ROAS mínimo = 2 (Adrián Sáenz `Q4Ykcwh5Osc 09:40`). Si los datos muestran ROAS <2 → recomendación de pausa.
