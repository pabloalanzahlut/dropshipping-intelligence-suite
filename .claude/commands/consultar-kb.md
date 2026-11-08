# /consultar-kb

Lee `ai_workspace/skills/consultar_kb_agente/procedimiento.md` y responde la consulta del operador basándose en la Knowledge Base SQLite.

## Conectores a activar automáticamente
- **Google Sheets** (`mcp__69f3b6ec`): si la consulta es sobre métricas agregadas (ROAS promedio, margen medio), cruzar con Dashboard GEM OS tab "Pipeline" para datos actualizados
- **Google Drive** (`mcp__73e33a54`): si hay archivos KB exportados en Drive, buscarlos con `search_files`

## Skills Claude a cargar
- `dataviz` → si la respuesta incluye métricas o comparaciones que se beneficien de un gráfico
- `artifact-design` → si se genera un resumen visual de la KB como artefacto

## Fuentes de datos (en orden de prioridad)
1. SQLite `app/database/dropshipping_suite.db` — tablas: `product_trends`, `conversion_formulas`, `operations_traffic`
2. `ai_workspace/memory/kb_index.json` — índice exportado
3. `ai_workspace/knowledge_base/kb_*.md` — archivos individuales por video

## Tipos de consulta y routing
| Consulta | Tabla SQLite | Acción |
|----------|-------------|--------|
| "¿qué productos HOT tenemos?" | `product_trends` | filtrar por clasificacion='HOT' |
| "¿qué estrategias de conversión hay?" | `conversion_formulas` | listar frameworks |
| "¿qué fuentes de tráfico recomienda la KB?" | `operations_traffic` | agrupar por traffic_source |
| "¿cuál es el margen promedio?" | `product_trends` | AVG(estimated_margin) |

## Regla
Nunca inventar datos. Si no hay información en la KB → "No tengo datos indexados sobre eso. ¿Quieres que busque un video sobre el tema?"
