---
name: tiktok-ads
description: "TikTok Ads pagados: pixel, Business Manager, campañas de ventas, retargeting. Usar cuando el usuario hable de: tiktok ads pagados, pixel tiktok, campaña tiktok."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/tiktok-ads.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /tiktok-ads

Lee `referencias/tiktok_ads.md` y configura/gestiona campañas de TikTok Ads pagados.

## Conectores a activar automáticamente
- **Google Sheets**: registrar métricas de campaña (CPM, CTR, CVR, ROAS TikTok vs ROAS Shopify) en Dashboard tab "TikTok Ads"
- **Stripe**: cruzar revenue declarado por TikTok con `stripe_analytics` para verificar atribución real (TikTok sobreestima)

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
