---
name: google-ads
description: "Campañas Google Ads: búsqueda, Shopping, PMax — keywords, pujas, optimización ROAS. Usar cuando el usuario hable de: google ads, search campaign, shopping, pmax, keywords google."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/google-ads.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /google-ads

Lee `referencias/google_ads.md` y configura/optimiza campañas de Google Ads.

## Conectores a activar automáticamente
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): SIEMPRE invocar `keywords-explorer-overview` para el producto antes de proponer keywords. Usar `keywords-explorer-matching-terms` para encontrar variaciones. Cargar también `mcp__plugin_marketing_ahrefs__doc` la primera vez.
- **Google Sheets**: registrar métricas de campaña (CTR, CPC, ROAS) en Dashboard tab "Google Ads"
- **Stripe**: si el usuario pega datos de revenue, cruzar con `stripe_analytics` para verificar atribución real

## Skills Claude a cargar
- `dataviz` → SIEMPRE cargar si hay métricas de campaña para visualizar
- `artifact-design` → si se genera estructura de campaña como artefacto

## Flujo con Ahrefs (obligatorio para keywords)
1. Recibir producto/nicho del usuario
2. Invocar `keywords-explorer-overview` con el producto como query, país del mercado
3. Invocar `keywords-explorer-matching-terms` para variaciones
4. Filtrar: volumen >500/mes, intención de compra (comprar/precio/oferta)
5. Proponer estructura de grupos de anuncios con keywords reales
6. Registrar en Google Sheets

## Regla de ROAS
ROAS mínimo = 2 (Adrián Sáenz `Q4Ykcwh5Osc 09:40`). Si los datos muestran ROAS <2 → recomendación de pausa.
