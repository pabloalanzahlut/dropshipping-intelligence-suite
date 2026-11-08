# /trafico-organico

Lee `ai_workspace/skills/trafico_organico/procedimiento.md` y ejecuta el flujo de contenido orgánico para TikTok/Reels.

## Conectores a activar automáticamente
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): si el usuario pide analizar hashtags o tendencias, usar `keywords-explorer-overview` con el nicho del producto
- **Google Sheets** (`mcp__69f3b6ec`): registrar métricas de videos (vistas, CTR, ventas orgánicas) en Dashboard tab "Orgánico"

## Skills Claude a cargar
- `dataviz` → si hay métricas de vistas/engagement para visualizar
- `artifact-design` → si se genera un calendario de publicación como artefacto

## Flujo
1. Identificar el producto activo desde `ai_workspace/projects/producto_01/market_analysis.json`
2. Generar plan de contenido: 3 videos/día durante 14 días con fórmulas del procedimiento
3. Si el usuario pide análisis de hashtags: invocar Ahrefs keywords-explorer
4. Registrar métricas en Google Sheets si se pegan datos de TikTok Analytics
5. Señal de validación: si algún video supera 10K vistas → notificar para pasar a `/tiktok-ads`

## Regla
Nunca prometer envío en 24-48h en el contenido orgánico. Usar tiempos reales del proveedor.
