---
name: configurar-tienda
description: "Checklist completo Shopify: dominio, pagos, políticas, envíos, AutoDS, píxeles. Usar cuando el usuario hable de: configurar tienda, shopify setup, dominio, pagos shopify."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/configurar-tienda.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /configurar-tienda

Lee `referencias/configurar_tienda.md` y guía al usuario por el checklist completo de configuración inicial de Shopify.

## Conectores a activar automáticamente
- **Stripe**: verificar que el método de pago está conectado antes de marcar el paso de pagos como completo
- **Google Sheets**: registrar fecha de configuración en Dashboard GEM OS tab "Pipeline"

## Skills Claude a cargar
- `artifact-design` → generar checklist visual como artefacto si el usuario lo pide
- `artifact-capabilities` → si el artefacto necesita estado persistente (checkboxes guardados)

## Flujo
1. Preguntar: ¿qué pasos ya están completados?
2. Ejecutar el procedimiento desde el primer paso pendiente
3. Para el paso de Stripe/Pagos: verificar con `stripe_api_read` que la cuenta está activa
4. Para el paso de píxeles: recordar que TikTok Pixel debe instalarse antes de `/tiktok-ads`
5. Emitir JSON de output con `listo_para_trafico: true/false`

## Regla crítica
No marcar `listo_para_trafico: true` hasta que los 3 píxeles (Meta, Google, TikTok) estén verificados.
