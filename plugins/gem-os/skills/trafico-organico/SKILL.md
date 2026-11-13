---
name: trafico-organico
description: "Setup cuenta TikTok/Reels + estrategia de contenido orgánico sin invertir en ads. Usar cuando el usuario hable de: tráfico orgánico, contenido orgánico, cuenta tiktok."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/trafico-organico.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /trafico-organico

Lee `referencias/trafico_organico.md` y ejecuta el flujo de contenido orgánico para TikTok/Reels.

## Conectores a activar automáticamente
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): si el usuario pide analizar hashtags o tendencias, usar `keywords-explorer-overview` con el nicho del producto
- **Google Sheets**: registrar métricas de videos (vistas, CTR, ventas orgánicas) en Dashboard tab "Orgánico"

## Skills Claude a cargar
- `dataviz` → si hay métricas de vistas/engagement para visualizar
- `artifact-design` → si se genera un calendario de publicación como artefacto

## Flujo
1. Identificar el producto activo desde `contexto/proyecto_activo/market_analysis.json`
2. Generar plan de contenido: 3 videos/día durante 14 días con fórmulas del procedimiento
3. Si el usuario pide análisis de hashtags: invocar Ahrefs keywords-explorer
4. Registrar métricas en Google Sheets si se pegan datos de TikTok Analytics
5. Señal de validación: si algún video supera 10K vistas → notificar para pasar a `/tiktok-ads`

## Regla
Nunca prometer envío en 24-48h en el contenido orgánico. Usar tiempos reales del proveedor.
