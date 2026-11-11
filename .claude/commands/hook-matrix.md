---
model: haiku
---
# /hook-matrix

Lee `ai_workspace/skills/redactar_hook_matrix/procedimiento.md` y genera una matriz de ≥10 hooks por fórmula.

## Conectores a activar automáticamente
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): usar `content-helper-topics` para identificar los pain points más resonantes del nicho antes de escribir los hooks. Cargar `doc` antes de la primera llamada.
- **Google Sheets** (`mcp__69f3b6ec`): si hay datos de CTR de hooks anteriores en Dashboard, leerlos para priorizar las fórmulas que ya funcionaron

## Skills Claude a cargar
- `artifact-design` → SIEMPRE — generar la matriz como artefacto visual (tabla con columnas: fórmula, hook, plataforma, duración)

## Fórmulas obligatorias (mínimo 2 hooks por fórmula)
| Fórmula | Estructura |
|---------|-----------|
| Story | "Cuando [situación]... descubrí que [solución]" |
| Shock | "[Dato sorprendente] sobre [problema común]" |
| Curiosity | "Nadie te dice que [insight contraintuitivo]" |
| Before/After | "[Estado malo] → [Estado bueno] en [tiempo]" |
| POV | "POV: [situación identificable del target]" |
| Urgencia | "[Número] personas ya [resultado] — tú también puedes" |

## Regla
Hook debe funcionar en los primeros 3 segundos. Sin superlativos vacíos. Basado en pain points reales validados con Ahrefs.
