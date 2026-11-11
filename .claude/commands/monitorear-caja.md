---
model: sonnet
---
# /monitorear-caja

Lee `ai_workspace/skills/monitorear_flujo_caja/procedimiento.md` y analiza la salud financiera del día/semana.

## Conectores a activar automáticamente — TODOS
- **Google Sheets** (`mcp__69f3b6ec`): SIEMPRE leer Dashboard GEM OS tab "ROAS_Diario" y "Pipeline" antes de analizar. Usar `get_values` para traer los últimos 7 días de datos. Si hay nuevos datos del usuario, escribirlos con `update_values`.
- **Stripe** (`mcp__1cc6d3ec`): usar `stripe_analytics` para verificar revenue real del período. Cruzar con lo que declaran TikTok/Meta (siempre difieren).
- **Gmail** (`mcp__ae68f902`): buscar emails de Shopify con subject "New order" o "Payout" de los últimos 7 días para cruzar con métricas

## Skills Claude a cargar
- `dataviz` → SIEMPRE — generar gráfico de ROAS diario, revenue vs gasto en ads, margen neto
- `artifact-design` → generar dashboard visual del período como artefacto compartible

## Flujo automático
1. Leer últimos 7 días de Google Sheets (ROAS_Diario)
2. Cruzar con Stripe para revenue verificado
3. Calcular: margen neto = revenue - coste producto - ads - fees (4%) - devoluciones (10,1%)
4. Generar gráfico con `dataviz`
5. Emitir señal: SALUDABLE / ADVERTENCIA / CRÍTICO según umbrales del procedimiento

## Referencia P&L Adrián Sáenz
Revenue 100% → Ads 32,1% → Devoluciones/cancelaciones 10,1% → Fees 4% → Margen operativo 34,8%
