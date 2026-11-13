---
name: hook-matrix
description: "Genera matriz ≥10 hooks TikTok/Meta Ads por fórmula (Story, Shock, Curiosity, Before/After, POV, Urgencia). Usar cuando el usuario hable de: hook, gancho, primeros 3 segundos, matriz de hooks."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/hook-matrix.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /hook-matrix

Lee `referencias/redactar_hook_matrix.md` y genera una matriz de ≥10 hooks por fórmula.

## Conectores a activar automáticamente
- **Ahrefs** (`mcp__plugin_marketing_ahrefs`): usar `content-helper-topics` para identificar los pain points más resonantes del nicho antes de escribir los hooks. Cargar `doc` antes de la primera llamada.
- **Google Sheets**: si hay datos de CTR de hooks anteriores en Dashboard, leerlos para priorizar las fórmulas que ya funcionaron

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
