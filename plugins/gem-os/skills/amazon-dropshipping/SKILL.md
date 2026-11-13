---
name: amazon-dropshipping
description: "Dropshipping en Amazon: proveedor, listings, envíos, devoluciones, AutoDS. Usar cuando el usuario hable de: amazon, listing amazon, BSR, fulfillment."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/amazon-dropshipping.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /amazon-dropshipping

Lee `referencias/amazon_dropshipping.md` y configura el canal Amazon como complemento a Shopify.

## Conectores a activar automáticamente
- **Google Sheets**: registrar métricas de cuenta Amazon (ventas, devoluciones, salud de cuenta) en Dashboard tab "Amazon"
- **Stripe**: Amazon tiene su propio sistema de pagos — Stripe no aplica aquí, pero registrar revenue total en el P&L consolidado

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
