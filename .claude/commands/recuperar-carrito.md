# /recuperar-carrito

Webhook Shopify → Make.com → email nocturno 20–23h para recuperación de carritos abandonados.

## Conectores a activar automáticamente
- **Gmail** (`mcp__ae68f902`): revisar si hay emails de recuperación enviados previamente — evitar duplicados en la misma sesión. Buscar con `search_threads` subject: "carrito abandonado" o "olvidaste algo"
- **Google Sheets** (`mcp__69f3b6ec`): registrar métricas de recuperación en Dashboard — columnas: fecha, carritos_abandonados, emails_enviados, recuperados, revenue_recuperado
- **Stripe** (`mcp__1cc6d3ec`): cruzar con `stripe_analytics` para verificar qué carritos recuperados se convirtieron en cobros reales

## Skills Claude a cargar
- `dataviz` → generar gráfico de tasa de recuperación por período
- `artifact-design` → si se genera template de email de recuperación como artefacto

## Configuración Make.com
- Webhook URL: variable `MAKE_WEBHOOK_CARRITO` en `.env`
- Trigger: Shopify evento "checkout/create" sin "order/create" asociado en 1h
- Ventana de envío: 20:00–23:00h (horario local del cliente)
- Máximo 2 emails por carrito (1h después + 24h después)

## Template de email (estructura)
1. Asunto: "Olvidaste algo en [nombre_tienda]" — sin emojis excesivos
2. Cuerpo: imagen producto + precio + CTA "Completar pedido"
3. Garantía/política devoluciones si existe
4. Sin promesas de envío irreales

## Regla
Nunca enviar fuera de la ventana 20–23h. Respetar unsubscribes de Klaviyo.
