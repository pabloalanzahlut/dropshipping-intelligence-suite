# Skill: Consultar Knowledge Base (Agente IA Interno)

**ID:** `consultar_kb_agente`
**Versión:** 2.0.0 (actualizado GEM OS v3.7)
**Propósito:** Permite al agente IA web interno responder consultas del operador sobre productos, estrategias y métricas indexadas en la Knowledge Base SQLite.

**Audiencia:** SOLO el operador (uso interno). Este agente NO responde a clientes finales.
**Fuente de datos:** SQLite — tablas `product_trends`, `conversion_formulas`, `operations_traffic`
**Acceso web:** `POST /api/kb/query` → `AgentExecutor.execute_agent_task()` con contexto KB inyectado

> **Nota arquitectural:** La fuente de verdad es SQLite, no los archivos `.md`.
> El endpoint `_build_kb_context()` inyecta automáticamente los últimos 30 insights
> como texto en el system prompt antes de cada consulta. No leer archivos `.md` directamente.

---

## Tipos de Consulta Soportados

### 1. Consultas de Producto
- "¿Qué productos HOT tenemos indexados esta semana?"
- "¿Hay algún producto de fitness con margen >5x?"
- "Muéstrame los últimos 3 productos WARM"

**Respuesta esperada (JSON):**
```json
{
  "tipo": "producto",
  "resultado": [
    {
      "nombre": "...",
      "nicho": "...",
      "margen_estimado": 4.5,
      "canal": "...",
      "fecha": "..."
    }
  ],
  "fuentes": ["video_id_1", "video_id_2"],
  "confianza": "Alta"
}
```

### 2. Consultas de Estrategia / Conversión
- "¿Qué estrategia de TikTok Ads funcionó mejor según la KB?"
- "¿Qué hooks usa {canal}?"
- "¿Cuál es el framework de conversión más mencionado?"

### 3. Consultas de Operaciones y Tráfico
- "¿Qué fuentes de tráfico recomienda la KB?"
- "¿Qué notas de logística hay para productos >0.5kg?"

### 4. Consultas de Métricas Agregadas
- "¿Cuál es el margen promedio de los productos indexados?"
- "¿Qué escala de ROAS mencionan los creadores?"

**Respuesta:** valor calculado + rango (min-max) + número de fuentes

### 5. Consultas de Lecciones
- "¿Qué errores comunes menciona la KB?"
- "¿Qué aciertos se repiten en varios videos?"

---

## Protocolo de Respuesta

El agente recibe en su system prompt:
1. El contexto KB completo (últimas 30 entradas de las 3 tablas, formato texto)
2. La pregunta del operador

Debe responder SIEMPRE en JSON estructurado con estos campos:

```json
{
  "respuesta": "...",
  "tipo_consulta": "producto|conversion|operaciones|metrica|leccion",
  "datos": [...],
  "fuentes": ["video_id · canal · fecha"],
  "confianza": "Alta|Media|Baja",
  "fecha_consulta": "YYYY-MM-DD"
}
```

### Reglas de respuesta
1. **Nunca inventar datos** no presentes en el contexto KB inyectado → si no hay información: `"No tengo datos indexados sobre eso. ¿Quieres que busque un video sobre el tema?"`
2. **Citar siempre la fuente**: cada dato debe ir acompañado de su video_id y canal
3. **No ejecutar acciones** (no publicar, no escribir a Shopify) → solo lectura
4. **Datos financieros**: siempre aclarar que son referencias de videos, no garantías

---

## Integración con el Pipeline

```
YouTube Monitor → yt-dlp → TranscriptCleaner → OpenRouter
        ↓
KBRouter.route_and_insert() → SQLite (product_trends, conversion_formulas, operations_traffic)
        ↓
KBIndexSync.sync() → kb_index.json (caché exportado)
        ↓
POST /api/kb/query
  → _build_kb_context() inyecta SQLite como texto
  → AgentExecutor.execute_agent_task("consultar_kb_agente")
  → Respuesta JSON al operador vía UI /agente
```

## Endpoint de sincronización manual
`POST /api/kb/sync` — regenera `kb_index.json` y todos los archivos `kb_*.md`
desde el estado actual de SQLite. Útil para inspección o debugging.
