# /tiktok-shop

Lee `ai_workspace/skills/tiktok_shop/procedimiento.md` y configura/opera el canal TikTok Shop sin stock.

## Conectores a activar automáticamente
- **Google Sheets** (`mcp__69f3b6ec`): registrar ventas TikTok Shop (ventas/semana, afiliados activos, comisión promedio) en Dashboard tab "TikTok Shop"
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): si el usuario busca producto viral para TikTok Shop, usar `keywords-explorer-overview` con filtro por tendencia

## Skills Claude a cargar
- `dataviz` → si hay métricas de ventas o rendimiento de afiliados
- `artifact-design` → si se genera plan de contenido o estructura de afiliados como artefacto

## Flujo
1. Verificar disponibilidad de TikTok Shop en el país del usuario
2. Guiar creación de cuenta de vendedor
3. Validar producto: wow factor visual + precio ≤ €50 + demostrabilidad en 5s
4. Configurar programa de afiliados: comisión 10-20% del PVP
5. Registrar métricas en Google Sheets

## Regla financiera
Margen neto = PVP - comisión TikTok (7%) - comisión afiliado (si aplica) - coste landed.
Verificar con `/validar-financiero` antes de listar.
