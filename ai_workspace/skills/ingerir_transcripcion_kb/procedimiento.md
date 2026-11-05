# Skill: Ingerir Transcripción en Knowledge Base

**ID:** `ingerir_transcripcion_kb`
**Versión:** 2.0.0 (actualizado GEM OS v3.7)
**Propósito:** Tomar una transcripción limpia de YouTube y extraer entidades clave para indexarlas en la Knowledge Base SQLite, disponibles para consulta del agente IA interno.

**Trigger:** Automático tras clasificación HOT o WARM por `clasificar_productos`
**Input:** Transcripción limpia + metadatos del video (video_id, canal, fecha, clasificacion)
**Output primario:** Filas en SQLite (`product_trends`, `conversion_formulas`, `operations_traffic`)
**Output secundario:** `ai_workspace/memory/kb_index.json` (snapshot exportado) + `ai_workspace/knowledge_base/kb_{video_id}.md` (copia legible)

> **Nota arquitectural:** La fuente de verdad es SQLite. Los archivos `.md` y `kb_index.json`
> son exportaciones generadas automáticamente por `KBIndexSync` tras cada ingesta.
> No editar manualmente esos archivos; serán sobreescritos.

---

## Reglas de Indexación

### Qué GUARDAR en la KB
- Productos mencionados con precio, margen o métricas de ventas → `product_trends`
- Estrategias de marketing con resultados numéricos verificables → `conversion_formulas`
- Nombres de proveedores o plataformas con contexto de uso → `operations_traffic`
- Hooks o copy que el creador describe como exitosos → `conversion_formulas`
- Errores o lecciones aprendidas con contexto → `operations_traffic`

### Qué DESCARTAR
- Opiniones sin datos ("este producto es increíble")
- Contenido off-topic (política, entretenimiento sin relación)
- Repeticiones del mismo dato ya indexado (usar dedup por hash MD5)
- Datos de envío expresamente ficticios ("llega en 24h")

---

## Pipeline de Ingesta (implementado en Python)

```
Transcripción cruda (yt-dlp)
        ↓
TranscriptCleaner.clean_for_ia()       → pre-limpieza local (gratis)
        ↓
OpenRouterTranscriptionCleaner         → extracción de valor CRO
        ↓
KBRouter.route_and_insert()            → INSERT en SQLite
        ├─ product_trends              (productos + nicho + margen)
        ├─ conversion_formulas         (AIDA + frameworks)
        └─ operations_traffic          (tráfico + logística)
        ↓
KBIndexSync.sync()                     → regenera kb_index.json
KBIndexSync.export_md_for_video()      → genera kb_{video_id}.md
```

### Tablas SQLite destino

| Tabla | Campos clave |
|-------|-------------|
| `product_trends` | video_id, product_name, niche, wow_factor, estimated_margin |
| `conversion_formulas` | video_id, category, framework_name, raw_structure, persuasion_triggers |
| `operations_traffic` | video_id, traffic_source, scaling_strategy, logistics_notes, weight_kg |

### Idempotencia
- Guard por hash MD5 del texto pre-limpiado en `video_sources.content_hash`
- Si el video ya existe → saltar sin reinsertar (dedup automático)
- Dedup de contenido en `transcripciones_youtube` por `hash_md5`

---

## Paso Post-Ingesta — Exportación automática

Tras cada ingesta exitosa, `provider_monitor_engine._process_single_video()` llama:

```python
KBIndexSync(db_path=...).sync()                    # actualiza kb_index.json
KBIndexSync(db_path=...).export_md_for_video(vid)  # genera/actualiza kb_{vid}.md
```

El endpoint `POST /api/kb/sync` permite forzar una sincronización manual completa.

---

## Manejo de Errores

| Nivel | Condición | Acción |
|-------|-----------|--------|
| INFO | Transcripción VACÍA (sin valor CRO) | Registrar STATUS_COMPLETED, no insertar en KB |
| WARNING | Falla KBIndexSync post-ingesta | Registrar, no detener pipeline |
| ERROR | Falla route_and_insert | Registrar STATUS_FAILED, reintentar en próximo ciclo |
| CRITICAL | Falla DB connection | Detener pipeline, alertar |
