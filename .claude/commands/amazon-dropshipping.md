# /amazon-dropshipping

Lee `ai_workspace/skills/amazon_dropshipping/procedimiento.md` y configura el canal Amazon como complemento a Shopify.

## Conectores a activar automáticamente
- **Google Sheets** (`mcp__69f3b6ec`): registrar métricas de cuenta Amazon (ventas, devoluciones, salud de cuenta) en Dashboard tab "Amazon"
- **Stripe** (`mcp__1cc6d3ec`): Amazon tiene su propio sistema de pagos — Stripe no aplica aquí, pero registrar revenue total en el P&L consolidado

## Skills Claude a cargar
- `dataviz` → si hay métricas de BSR, ventas, devoluciones para visualizar
- `artifact-design` → si se genera análisis de producto Amazon como artefacto

## Flujo
1. Verificar que AutoDS está conectado a Amazon (referencia a paso de `/configurar-tienda`)
2. Buscar producto con BSR entre 10.000-100.000 en la categoría
3. Calcular margen neto: PVP - fee Amazon (15%) - coste landed ≥ 20% PVP
4. Configurar envíos y devoluciones según el procedimiento
5. Registrar ASIN + métricas en Google Sheets

## Regla crítica de salud de cuenta
- Tasa de pedidos defectuosos < 1%
- Tasa de cancelación < 2,5%
Si se supera cualquier umbral → alerta inmediata.
