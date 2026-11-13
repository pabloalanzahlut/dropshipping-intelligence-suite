---
name: consultar-kb
description: "Consulta la Knowledge Base interna sobre productos, estrategias y métricas. Usar cuando el usuario hable de: consultar KB, qué tenemos en la KB, estrategias guardadas."
---

> **Entorno Cowork — leer antes de seguir.** Esta skill se genera desde GEM OS (`.claude/commands/consultar-kb.md`) y aquí no tienes el repositorio:
> 1. Carga primero la skill `reglas-gem-os`. Sus reglas mandan sobre cualquier texto de abajo; las rutas `reglas-gem-os/…` y `verificar-salida/…` son archivos de esas skills.
> 2. Conectores: se usan por nombre (Google Sheets, Stripe, Gmail, Google Drive, Ahrefs, Figma). Stripe y Gmail, solo lectura. Si uno no está conectado, dilo y sigue sin él; no inventes su resultado.
> 3. Archivos: la KB está en `contexto/kb/` y el producto en curso en `contexto/proyecto_activo/`, ambos de solo lectura. Lo que la skill llame `referencias/…` está junto a este archivo. Escribe únicamente en `salidas/`.
> 4. El código Python de `app/`, los scripts y la base de datos del proyecto no existen aquí. Si un paso los pide, haz el cálculo con las fórmulas del procedimiento y dilo en la salida; no simules haberlos ejecutado ni registres nada en la base de datos.
> 5. Todo número y todo copy comercial pasa por la skill `verificar-salida` antes de entregarse.
> 6. Si falta un dato crítico: `DATA_GAP_REQUEST`. Nunca se estima.

# /consultar-kb

Lee `referencias/consultar_kb_agente.md` y responde la consulta del operador basándose en la Knowledge Base SQLite.

## Conectores a activar automáticamente
- **Google Sheets**: si la consulta es sobre métricas agregadas (ROAS promedio, margen medio), cruzar con Dashboard GEM OS tab "Pipeline" para datos actualizados
- **Google Drive**: si hay archivos KB exportados en Drive, buscarlos con `search_files`

## Skills Claude a cargar
- `dataviz` → si la respuesta incluye métricas o comparaciones que se beneficien de un gráfico
- `artifact-design` → si se genera un resumen visual de la KB como artefacto

## Fuentes de datos (en orden de prioridad)
1. SQLite `app/database/dropshipping_suite.db` — tablas: `product_trends`, `conversion_formulas`, `operations_traffic`
2. `contexto/kb_index.json` — índice exportado
3. `contexto/kb/kb_*.md` — archivos individuales por video

## Tipos de consulta y routing
| Consulta | Tabla SQLite | Acción |
|----------|-------------|--------|
| "¿qué productos HOT tenemos?" | `product_trends` | filtrar por clasificacion='HOT' |
| "¿qué estrategias de conversión hay?" | `conversion_formulas` | listar frameworks |
| "¿qué fuentes de tráfico recomienda la KB?" | `operations_traffic` | agrupar por traffic_source |
| "¿cuál es el margen promedio?" | `product_trends` | AVG(estimated_margin) |

## Regla
Nunca inventar datos. Si no hay información en la KB → "No tengo datos indexados sobre eso. ¿Quieres que busque un video sobre el tema?"
