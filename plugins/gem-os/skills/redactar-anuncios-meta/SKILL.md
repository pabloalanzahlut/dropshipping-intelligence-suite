---
name: redactar-anuncios-meta
description: "Copy para Meta Ads estáticos: imagen única, carousel, variantes A/B. Usar cuando el usuario hable de: anuncio meta, Facebook Ads, Instagram Ads, copy ads."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/redactar-anuncios-meta.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /redactar-anuncios-meta

Lee `referencias/redactar_anuncios_meta.md` y genera copy para Meta Ads estáticos.

## Conectores a activar automáticamente
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): usar `content-helper-topics` para identificar los pain points más buscados del producto. Cargar `doc` antes de la primera llamada.
- **Google Sheets**: si hay datos de campañas anteriores en Dashboard, leerlos para informar el copy con métricas reales
- **Figma** (`mcp__plugin_marketing_figma`): si el usuario pide mockup visual del anuncio, generar diseño en Figma

## Skills Claude a cargar
- `artifact-design` → generar los anuncios como artefacto visual si hay imágenes
- `dataviz` → si hay métricas de A/B test para visualizar

## Tipos de anuncio que genera
1. **Imagen única** — headline 5-7 palabras + texto principal 125 chars + CTA
2. **Carousel** — 3-5 tarjetas con beneficio progresivo
3. **Variantes A/B** — mínimo 2 variantes de headline y texto por anuncio

## Reglas (INMUTABLES)
- Prohibido superlativos vacíos: "increíble", "revolucionario", "el mejor"
- Prohibido promesas de envío sin confirmar con el proveedor
- Siempre incluir garantía real (si existe) o política de devoluciones
- Copy basado en pain points reales del nicho (usar Ahrefs para validar)
