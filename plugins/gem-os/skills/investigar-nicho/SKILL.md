---
name: investigar-nicho
description: "Genera informe de 10 ángulos de ataque para un nicho (Nivel 2). Usar cuando el usuario hable de: investigar nicho, ángulos de ataque, keywords nicho."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/investigar-nicho.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /investigar-nicho

Lee `referencias/investigar_nicho.md` y genera un informe de 10 ángulos de ataque para el nicho indicado.

## Conectores a activar automáticamente — OBLIGATORIO
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): es el conector central de este skill
  1. `keywords-explorer-overview` → volumen y dificultad del nicho
  2. `keywords-explorer-matching-terms` → keywords long-tail de compra
  3. `keywords-explorer-related-terms` → ángulos alternativos
  4. `site-explorer-organic-keywords` → qué keywords usa la competencia
  5. `serp-overview` → quién domina el nicho en Google
  
  Cargar `mcp__plugin_marketing_ahrefs__doc` antes de la primera llamada a Ahrefs.

- **Google Sheets**: guardar el informe de nicho en Dashboard tab "Nichos"

## Skills Claude a cargar
- `dataviz` → SIEMPRE — visualizar volúmenes de búsqueda y dificultad de keywords
- `artifact-design` → generar el informe de 10 ángulos como artefacto compartible
- `anthropic-skills:deep-research` → si el nicho es complejo y requiere investigación profunda

## Output esperado
Informe con:
1. Volumen de búsqueda total del nicho
2. Top 10 keywords de compra con volumen y KD
3. 10 ángulos de ataque diferentes (precio, urgencia, dolor, resultado, comparación, etc.)
4. Competidores principales en SEO y ads
5. Recomendación de canal principal (Google Ads vs Meta vs TikTok)
