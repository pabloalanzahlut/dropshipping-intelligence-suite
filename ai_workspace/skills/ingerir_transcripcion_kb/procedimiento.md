# Skill: Ingerir Transcripción en Knowledge Base

**ID:** `ingerir_transcripcion_kb`
**Versión:** 1.0.0
**Propósito:** Tomar una transcripción limpia de YouTube y extraer entidades clave para indexarlas en la Knowledge Base, disponibles para consulta del agente IA interno.

**Trigger:** Automático tras clasificación HOT o WARM por `clasificar_productos`
**Input:** Transcripción limpia + metadatos del video (video_id, canal, fecha, clasificacion)
**Output:** Archivo `ai_workspace/knowledge_base/kb_{video_id}.md`

---

## Reglas de Indexación

### Qué GUARDAR en la KB
- Productos mencionados con precio, margen o métricas de ventas
- Estrategias de marketing con resultados numéricos verificables
- Nombres de proveedores o plataformas con contexto de uso
- Hooks o copy que el creador describe como exitosos
- Errores o lecciones aprendidas con contexto

### Qué DESCARTAR
- Opiniones sin datos ("este producto es increíble")
- Contenido off-topic (política, entretenimiento sin relación)
- Repeticiones del mismo dato ya indexado (usar dedup)
- Datos de envío expresamente ficticios ("llega en 24h")

---

## Pipeline de Ingesta

### Paso 1 — Extracción de Entidades
Para cada transcripción limpia, identificar y extraer:

```
PRODUCTOS:
  - nombre, categoría, precio_mencionado, margen_mencionado, plataforma_venta

ESTRATEGIAS:
  - nombre_estrategia, descripcion_breve, resultado_numerico, fuente_tráfico

PROVEEDORES:
  - nombre, plataforma (AutoDS/AliExpress/CJ), valoracion_mencionada

MÉTRICAS:
  - roas, cpc, conversion_rate, revenue_mencionado, periodo

LECCIONES:
  - tipo (error|acierto), descripcion, impacto
```

### Paso 2 — Validación de Calidad
- Descartar entidades con confianza < 0.6
- Si una entidad duplica una ya en KB (Jaccard > 0.85): actualizar la existente, no crear nueva
- Mínimo 3 entidades válidas para proceder; si hay menos → registrar como INFO y no guardar

### Paso 3 — Formato del Chunk para Búsqueda Semántica

Cada archivo KB tiene la siguiente estructura:

```markdown
# KB: {titulo_video}

**video_id:** {video_id}
**canal:** {canal}
**fecha_indexacion:** {YYYY-MM-DD}
**clasificacion:** HOT | WARM
**fuente:** youtube_transcript

---

## Productos

- **{nombre}** | Categoría: {cat} | Precio ref: ${precio} | Margen: {margen}%

## Estrategias

- **{nombre}**: {descripcion} → Resultado: {resultado}

## Proveedores Mencionados

- {nombre} ({plataforma}) — {valoracion}

## Métricas Clave

- ROAS: {roas} | CPC: ${cpc} | CR: {cr}% | Revenue: ${revenue} ({periodo})

## Lecciones

- [{tipo}] {descripcion} → Impacto: {impacto}

---
*Generado por ingerir_transcripcion_kb v1.0.0*
```

### Paso 4 — Guardar y Registrar
1. Escribir archivo en `ai_workspace/knowledge_base/kb_{video_id}.md`
2. Registrar en `ai_workspace/memory/kb_index.json`:
   ```json
   {
     "video_id": "",
     "archivo": "kb_{video_id}.md",
     "fecha": "",
     "clasificacion": "",
     "entidades_indexadas": 0,
     "canal": ""
   }
   ```
3. Notificar Orchestrator Core: "KB actualizada — {video_id}"

---

## Manejo de Errores

| Nivel | Condición | Acción |
|-------|-----------|--------|
| INFO | < 3 entidades extraídas | Registrar, no guardar |
| WARNING | Transcripción vacía o < 200 palabras | Registrar + notificar |
| ERROR | Falla escritura en disco | Detener, reintentar 1 vez |
