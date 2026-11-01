# 🎯 Plan Maestro: Suite de Inteligencia Dropshipping + Shopify (Fase Desktop)

**Alcance:** Software de escritorio orientado a dropshippers, media agencies y e-commerce profesional  
**Contexto:** Construido sobre GEM OS existente + KDP Master Suite como referencia arquitectónica  
**Timeline:** MVP funcional 1-2 semanas  
**Público:** Dropshippers principiantes → E-commerce profesional (ramp gradual)

---

## 🏗️ Arquitectura General

```
┌─────────────────────────────────────────────────┐
│  CAPA PRESENTACIÓN (Desktop UI - Tkinter)       │
│  • Dashboard principal (validación + stats)     │
│  • Editor visual de copywriting                 │
│  • Monitor de tendencias en tiempo real         │
│  • Queue de procesamiento visual               │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│  CAPA ORQUESTACIÓN (Services Engine)            │
│  • FinancialValidator (Regla 3x + 70% margen) │
│  • CopywrightingEngine (AIDA framework)        │
│  • YouTubeChannelMonitor (Ingesta transcr.)   │
│  • TikTokScriptGenerator (Guiones CON IA)     │
│  • TrafficAnalyzer (Tendencias reales)        │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│  CAPA PERSISTENCIA (SQLite + KB Local)          │
│  • Tabla: productos_validados                  │
│  • Tabla: transcripciones_youtube              │
│  • Tabla: copys_generados                      │
│  • Tabla: guiones_tiktok                       │
│  • Tabla: tendencias_trafico                   │
└─────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────┐
│  CAPA EXTERNOS (APIs + Archivos)                │
│  • OpenRouter / Gemini (copywriting IA)       │
│  • YouTube (descargas + transcripciones)      │
│  • Uploads manuales (CSVs, JSONs)             │
│  • OpenRouter (optimización de prompts)       │
└─────────────────────────────────────────────────┘
```

---

## 📋 Plan de Fases Detallado

### **FASE 0: Fundacional (Hoy - 2 días)**

Objetivo: Establecer base operativa sin UI de lujo.

#### ✅ Tareas Core

| ID | Tarea | Componente | Criticidad |
|----|-------|-----------|-----------|
| 0.1 | Crear tabla `productos_validados` | DB | CRÍTICO |
| 0.2 | Implementar `FinancialValidator` (Regla 3x) | Services | CRÍTICO |
| 0.3 | Crear endpoint CLI de prueba | CLI | HIGH |
| 0.4 | Archivo `.env` con claves de API | Config | HIGH |
| 0.5 | Documentación de estructura de datos | Docs | MEDIUM |

**Entregables:**
- `app/services/financial_validator.py` → Motor de validación financiera
- Extensión BD: tabla `produtos_validados` con campos (id, sku, costo_origen, pvp, margen_bruto, status_validacion, validado_por_regla_3x, nota_peso_kg)
- Archivo: `cli_test.py` para pruebas rápidas
- README de setup: variables de entorno

**Duración Estimada:** 2 días

---

### **FASE 1: Validación Financiera Completa (Días 3-5)**

Objetivo: MVP de validador financiero con interfaz básica visual.

#### ✅ Tareas Core

| ID | Tarea | Componente | Criticidad |
|----|-------|-----------|-----------|
| 1.1 | UI: Panel "Validar Producto" | UI | CRÍTICO |
| 1.2 | Parser CSV/JSON → tabla DB | Services | CRÍTICO |
| 1.3 | Auditoría Iván Caicedo (peso < 1.2kg) | FinancialValidator | HIGH |
| 1.4 | Export CSV con validaciones | Services | HIGH |
| 1.5 | Batch processing de N productos | Services | MEDIUM |

**Entregables:**
- Nueva pestañaUI: "Validador Financiero"
- Columna auditoría logística en tabla `productos_validados`
- CSV export con flagging de productos no-validados
- Progress bar para batch processing

**Duración Estimada:** 3 días

---

### **FASE 2: YouTube + Transcripciones (Días 6-9)**

Objetivo: Ingesta automatizada de transcripciones de mentores; almacenamiento en KB local.

#### ✅ Tareas Core

| ID | Tarea | Componente | Criticidad |
|----|-------|-----------|-----------|
| 2.1 | Servicio `YouTubeChannelMonitor` | Services | CRÍTICO |
| 2.2 | Tabla `transcripciones_youtube` | DB | CRÍTICO |
| 2.3 | Parser VTT/SRT → texto limpio | Services | HIGH |
| 2.4 | UI: "Monitor Canales YouTube" | UI | HIGH |
| 2.5 | Deduplicación por hash MD5 | Services | MEDIUM |
| 2.6 | Background daemon de sincronización | Threading | MEDIUM |

**Entregables:**
- Pestaña UI: "Monitor YouTube"
- Tabla `transcripciones_youtube` (id, video_id, titulo, canal, fecha, transcripcion_texto, hash_md5, procesada)
- Proceso daemon en background sincronizando cada 2 hrs
- Lista de canales monitoreados (setup manual)

**Duración Estimada:** 4 días

---

### **FASE 3: Copywriting AIDA Framework (Días 10-13)**

Objetivo: Motor de redacción de copys Shopify siguiendo AIDA (Attention, Interest, Decision, Action).

#### ✅ Tareas Core

| ID | Tarea | Componente | Criticidad |
|----|-------|-----------|-----------|
| 3.1 | Motor `CopywrightingEngine` | Services | CRÍTICO |
| 3.2 | Tabla `copys_generados` | DB | CRÍTICO |
| 3.3 | Prompt templates AIDA (sin superlativos) | Services | HIGH |
| 3.4 | UI: "Redactor de Copys" + vista previa | UI | HIGH |
| 3.5 | Rating manual de calidad (1-5 estrellas) | Services | MEDIUM |
| 3.6 | Historial de versiones de copys | DB | MEDIUM |

**Entregables:**
- Pestaña UI: "Redactor de Copys"
- Tabla `copys_generados` (id, producto_id, titulo_copy, descripcion, attention_score, interest_score, decision_score, action_score, rating_usuario)
- Integracion con OpenRouter para generación (fallback: template local)
- Export a txt/html para copiar directo a Shopify

**Duración Estimada:** 4 días

---

### **FASE 4: Generador de Guiones TikTok (Días 14-17)**

Objetivo: Crear guiones virales TikTok basados en tendencias y productos validados.

#### ✅ Tareas Core

| ID | Tarea | Componente | Criticidad |
|----|-------|-----------|-----------|
| 4.1 | Motor `TikTokScriptGenerator` | Services | CRÍTICO |
| 4.2 | Tabla `guiones_tiktok` | DB | CRÍTICO |
| 4.3 | Análisis de trending topics | TrafficAnalyzer | HIGH |
| 4.4 | UI: "Generador de Guiones" | UI | HIGH |
| 4.5 | Template de hook-pattern viral | Services | MEDIUM |
| 4.6 | Integración con transcripciones YouTube | Services | MEDIUM |

**Entregables:**
- Pestaña UI: "Generador TikTok"
- Tabla `guiones_tiktok` (id, producto_id, titulo, hook, cuerpo, cta, tendencia_utilizada, length_segundos)
- Prompts que usan contexto de transcripciones de mentores
- Batch generation: de 1 producto → 5 variantes de guiones

**Duración Estimada:** 4 días

---

### **FASE 5: Dashboard Analytics + Polish (Días 18-20)**

Objetivo: Dashboard integrado; validaciones visuales; empaquetamiento .exe.

#### ✅ Tareas Core

| ID | Tarea | Componente | Criticidad |
|----|-------|-----------|-----------|
| 5.1 | Dashboard: stats principales | UI | CRÍTICO |
| 5.2 | Gráficos de validación (Plotly lite o Canvas) | UI | HIGH |
| 5.3 | Exportación .exe con PyInstaller | Build | HIGH |
| 5.4 | Testing manual: flujo end-to-end | QA | HIGH |
| 5.5 | Documentación README.md | Docs | MEDIUM |
| 5.6 | Modo "Demo" con datos de ejemplo | UI | MEDIUM |

**Entregables:**
- Pestaña UI: "Dashboard" con KPIs principales
- Archivo ejecutable: `DropshippingIntelligenceSuite.exe`
- README con setup instructions
- Datos demo para demostración sin APIs

**Duración Estimada:** 3 días

---

## 📊 Mapa de Dependencias

```
FASE 0 (Fundacional)
    ↓
FASE 1 (Validación Financiera) ← Depende de FASE 0
    ↓
├─→ FASE 2 (YouTube Transcripciones) ← Depende de FASE 0
├─→ FASE 3 (Copywriting AIDA) ← Depende de FASE 0, 2 (opcional)
│    ↓
│    FASE 4 (Guiones TikTok) ← Depende de FASE 1, 2
│    ↓
└─→ FASE 5 (Dashboard + .exe) ← Depende de FASE 1, 3, 4
```

**Paralelizable:** FASES 2 y 3 pueden correr en paralelo (no dependen).

---

## 🔧 Stack Técnico Base

### Backend (Python 3.11+)
- **Framework:** CLI + Services (sin Django/Flask por ahora)
- **BD:** SQLite (ya existe)
- **APIs externas:** OpenRouter, YouTube Data API
- **Threading:** Python stdlib `threading` (daemon workers)
- **Logging:** `logging` (configuración centralizada)

### Frontend (Desktop UI)
- **GUI:** Tkinter (ya existe)
- **Componentes:** ttk (temas nativos) + Canvas (gráficos)
- **Layout:** Grid + Frame (responsive básico)

### Build
- **Empaquetamiento:** PyInstaller 6.11.1
- **Distribución:** Ejecutable Windows único (con Python embebido)

---

## 📁 Estructura de Archivos (Post-Implementación)

```
h:\dropshipping_intelligence_suite\
├── app/
│   ├── services/
│   │   ├── financial_validator.py       [NUEVO - FASE 1]
│   │   ├── youtube_channel_monitor.py   [NUEVO - FASE 2]
│   │   ├── copywriting_engine.py        [NUEVO - FASE 3]
│   │   ├── tiktok_script_generator.py   [NUEVO - FASE 4]
│   │   ├── traffic_analyzer.py          [NUEVO - FASE 4]
│   │   ├── (existentes)
│   │   └── ...
│   ├── ui/
│   │   └── components/
│   │       ├── console_view.py          [EXISTENTE]
│   │       ├── financial_panel.py       [NUEVO - FASE 1]
│   │       ├── youtube_monitor_panel.py [NUEVO - FASE 2]
│   │       ├── copywriting_panel.py     [NUEVO - FASE 3]
│   │       ├── tiktok_panel.py          [NUEVO - FASE 4]
│   │       ├── dashboard_panel.py       [NUEVO - FASE 5]
│   │       └── ...
│   ├── database/
│   │   ├── connection.py                [MODIFICADO - nuevas tablas]
│   │   └── ...
│   └── main.py                           [MODIFICADO - agregar pestañas]
├── ai_workspace/
│   ├── context/
│   │   └── (bases de conocimiento)
│   └── ...
├── .env                                  [MODIFICADO - nuevas keys]
├── requirements.txt                      [MODIFICADO - deps]
└── build_exe.py                          [EXISTENTE - reutilizar]
```

---

## 🎯 KPIs de Éxito por Fase

| Fase | KPI Principal | Métrica Éxito |
|------|---------------|--------------|
| 0 | Arquitectura DB operativa | Schema completo sin errores |
| 1 | Validación 100% de productos candidatos | Margen bruto ≥ 70%, Peso < 1.2kg |
| 2 | Ingesta de transcripciones automática | 10+ horas de contenido procesadas |
| 3 | Copys generados sin superlativos | 5+ variantes por producto en < 5s |
| 4 | Guiones TikTok trending | Mín 3 hooks virales por producto |
| 5 | Software en .exe funcional | 0 crashes, UI responsiva en 900x600px |

---

## ⚠️ Riesgos Identificados

| Riesgo | Impacto | Mitigación |
|--------|--------|-----------|
| **API OpenRouter rate-limit** | Bloquea generación masiva de copys | Implementar queue + retry con backoff exponencial |
| **YouTube API quota excedida** | No se puede descargar transcripciones | Usar caché local; opción manual upload |
| **Peso computacional de IA** | UI se congela durante generación | Threading + progress bars; async workers |
| **Datos dirty en uploads** | Validaciones fallan | Implementar parser robusto + rollback |

---

## 🚀 Próximos Pasos Inmediatos (Post-Plan)

1. **Confirmación del plan** por parte del usuario
2. **Creación de tabla `productos_validados`** en schema DB
3. **Implementación `FinancialValidator`** con tests unitarios
4. **Primera UI panel** para Fase 1
5. **Integración con main.py** (agregar pestaña)

---

## 📚 Referencias Internas

- **Reglas Financieras:** `.github/instructions/ecom-financial-rules.md.instructions.md`
- **Contexto KB:** `.github/instructions/dropshipping-kb-context.md.instructions.md`
- **Matriz Tendencias:** `ai_workspace/context/matriz_tendencias.md`
- **Fórmulas Conversión:** `ai_workspace/context/formulas_conversion.md`
- **Operaciones Tráfico:** `ai_workspace/context/operaciones_trafico.md`

---

## 🏆 Filosofía del Proyecto

✅ **Reutilización máxima** del código GEM OS existente  
✅ **Pipeline inmutable:** YouTube → Transcripción → KB → Generación  
✅ **Números reales:** Sin alucinaciones en presupuestos publicitarios  
✅ **Desktop-first:** Ejecutable local sin dependencias externas pesadas  
✅ **Gobernanza embebida:** Reglas de negocio validadas en cada paso

---

**Versión del Plan:** v1.1  
**Creado:** 2026-10-25  
**Última Actualización:** 2026-10-25  
**Fase Actual:** ✅ **TODAS LAS FASES COMPLETADAS (0-5)**  
**Estado:** ✅ Suite funcional — 6 tabs operativos, tests pasan, app inicializa sin errores
