# /investigar-nicho

Lee `ai_workspace/skills/investigar_nicho/procedimiento.md` y genera un informe de 10 ángulos de ataque para el nicho indicado.

## Conectores a activar automáticamente — OBLIGATORIO
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): es el conector central de este skill
  1. `keywords-explorer-overview` → volumen y dificultad del nicho
  2. `keywords-explorer-matching-terms` → keywords long-tail de compra
  3. `keywords-explorer-related-terms` → ángulos alternativos
  4. `site-explorer-organic-keywords` → qué keywords usa la competencia
  5. `serp-overview` → quién domina el nicho en Google
  
  Cargar `mcp__plugin_marketing_ahrefs__doc` antes de la primera llamada a Ahrefs.

- **Google Sheets** (`mcp__69f3b6ec`): guardar el informe de nicho en Dashboard tab "Nichos"

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
