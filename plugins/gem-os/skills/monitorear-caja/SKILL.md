---
name: monitorear-caja
description: "Revisa salud del flujo de caja con datos pegados del día/semana (Nivel 6). Usar cuando el usuario hable de: flujo de caja, ROAS del día, revenue, margen neto."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/monitorear-caja.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /monitorear-caja

Lee `referencias/monitorear_flujo_caja.md` y analiza la salud financiera del día/semana.

## Conectores a activar automáticamente — TODOS
- **Google Sheets**: SIEMPRE leer Dashboard GEM OS tab "ROAS_Diario" y "Pipeline" antes de analizar. Usar `get_values` para traer los últimos 7 días de datos. Si hay nuevos datos del usuario, escribirlos con `update_values`.
- **Stripe**: usar `stripe_analytics` para verificar revenue real del período. Cruzar con lo que declaran TikTok/Meta (siempre difieren).
- **Gmail**: buscar emails de Shopify con subject "New order" o "Payout" de los últimos 7 días para cruzar con métricas

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
