# 📋 WORKFLOW COMPLETO — GEM OS Dropshipping Intelligence Suite

## 📊 Flujo General del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                      GEM OS SUITE                               │
│  Pipeline: Bootstrap → UI → Ingesta → Validación → Salida       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1️⃣ BOOTSTRAP WORKFLOW (Inicialización)

```
[INICIO]
    ├─ 1. PathManager._is_executable()
    │      └─ ¿sys.frozen? → Modo .exe (AppData)
    │      └─ ¿No?         → Modo Desarrollo (local data/)
    ├─ 2. PathManager.get_paths()
    │      └─ Crea directorios: data/, logs/, backups/
    ├─ 3. bootstrap.initialize_app_environment()
    │      ├─ Si .exe: Copia plantillas de sys._MEIPASS → AppData
    │      └─ Si dev:   Usa archivos existentes en data/
    ├─ 4. cleanup_legacy_paths()
    │      └─ Migra: app/database/ → data/
    ├─ 5. load_dotenv()
    │      └─ Carga OPENROUTER_API_KEY
    ├─ 6. DatabaseConnection()
    │      └─ Crea dropshipping_suite.db en data/
    └─ 7. Lanzar UI (Tkinter)
```

| Paso | Archivo | Función |
|------|---------|---------|
| 1-2 | `app/config/path_manager.py` | `PathManager` |
| 3-4 | `app/config/bootstrap.py` | `bootstrap_system()` |
| 5 | `app/main.py` | `load_dotenv()` |
| 6 | `app/database/connection.py` | `DatabaseConnection()` |
| 7 | `app/main.py` | `GEMOSApplication()` |

---

## 2️⃣ MAIN WORKFLOW (Runtime - UI)

```
[UI - Tkinter Notebook]
    ├─ Tab 1: Dashboard (FASE 5)     → KPIs DB
    ├─ Tab 2: Validador Financiero    → Regla 3x, Margen, Peso
    ├─ Tab 3: YouTube Monitor         → Sincronización canales
    ├─ Tab 4: Redactor Copys AIDA     → Attention/Interest/Decision/Action
    ├─ Tab 5: Generador TikTok        → Guiones Ads
    ├─ Tab 6: Control Gobernanza      → Cumplimiento reglas
    ├─ Tab 7: Ingesta Masiva (Legacy) → Consola YouTube
    └─ Tab 8: Enrutador Híbrido       → FreeLLMAPI/OpenRouter/Ollama
```

### Conexiones:
```
UI Tab → Panel (Componente) → Servicio (Lógica)
    → DatabaseConnection (Persistencia)
    → HybridInferencePool (Inferencia LLM)
    → PathManager (Rutas)
```

---

## 3️⃣ AGENT WORKFLOW (Pipeline IA)

```
user_request + project_name + skill_name
    │
    ├─ 1. PRE-FLIGHT CHECK
    │      └─ validator.pre_execution_check()
    ├─ 2. DATA GAP VALIDATION
    │      └─ Si faltan datos → [BLOQUEO] preguntar usuario
    ├─ 3. CONSTRUIR CONTEXTOS
    │      ├─ Governance: agents.md
    │      ├─ Skill: skills/<skill>/procedimiento.md
    │      └─ Memory: memory/<agent>_memory.txt
    ├─ 4. MEMORIA ACTIVA (últimos 15 eventos)
    ├─ 5. EJECUCIÓN → OpenRouter API (JSON)
    ├─ 6. POST-VALIDACIÓN
    ├─ 7. LOG en memoria
    └─ 8. ERROR HANDLING (SI FALLA)
           ├─ Nivel 1: Fallo único → log local
           └─ Nivel 2: Fallo doble → reescribe skill
```

| Paso | Archivo | Función |
|------|---------|---------|
| 1-4 | `app/agents_engine/executor.py` | `execute_agent_task()` |
| 5 | `app/services/openrouter_client.py` | LLM call |
| 6 | `app/services/validator_rules.py` | `post_execution_validation()` |
| 7 | `app/services/memory_logger.py` | `log()` |
| 8 | `app/agents_engine/executor.py` | `handle_agent_error()` |

---

## 4️⃣ STATE MACHINE (Máquina de Estados)

```
IDLE → VALIDANDO → (REPAIR|REJECT) → HASHING
→ (DUPLICATE|UNIQUE) → KB_INGEST → GEM_FEED → COMPLETE
                                    ↓
                              ERROR_HANDLER → REINTENTO|max_retries→ FAILED
```

### Gates (Hard Gates):
| Condición | Acción |
|-----------|--------|
| Corrupción > 5% | NO-GO, solicitar re-descarga |
| Duplicado exacto | SKIP, loguear referencia |
| KB inconsistente | HALT, trigger backup restore |
| Security violation | CRITICAL_HALT, alertar admin |
| Score < 70 | DEPLOY_REJECTED, rollback |

---

## 5️⃣ HYBRID INFERENCE POOL

```
[QUERY recibida]
    │
    ├─ CAPA 1: FreeLLMAPI ($0.00)
    │   ├─ ¿Disponible? → Usar (gratuito)
    │   └─ ¿No? → Pasar a capa 2
    │
    ├─ CAPA 2: OpenRouter (Nube)
    │   ├─ ¿API Key? → Usar (deepseek/deepseek-chat)
    │   └─ ¿No? → Pasar a capa 3
    │
    └─ CAPA 3: Ollama (Localhost)
        ├─ ¿Disponible? → Usar (qwen2.5-coder)
        └─ ¿No? → Error: Sin capa disponible
```

### Pool Singleton:
```python
pool = HybridInferencePool()
respuesta = pool.execute_hybrid_query(system_prompt, user_prompt)
```

---

## 6️⃣ DATA FLOW (Flujo de Datos)

```
YouTube (API) ──► Transcripciones
                      │
                  ┌───▼──────────────┐
                  │ TranscriptCleaner│ (UTF-8 + Filler Words)
                  └───┬──────────────┘
                      │
                  ┌───▼──────────────┐
                  │ IdempotencyGuard │ (Hash MD5)
                  └───┬──────────────┘
                      │
                  ┌───▼──────────────┐
                  │   Knowledge      │
                  │  Base (SQLite)   │ ← data/dropshipping_suite.db
                  └───┬──────────────┘
                      │
        ┌─────────────┼────────────────┐
        │             │                │
   ┌────▼────┐   ┌────▼────┐    ┌────▼────┐
   │Product  │   │ Copy    │    │TikTok   │
   │Hunter   │   │AIDA     │    │Script   │
   └─────────┘   └─────────┘    └─────────┘
```

---

## 📁 Archivos del Flujo

| Documento | Propósito |
|-----------|-----------|
| `app/config/path_manager.py` | Gestión de rutas (4 métodos) |
| `app/config/bootstrap.py` | Inicialización del sistema |
| `WORKFLOW_COMPLETE.md` | Este documento (flujo completo) |
| `THREADING_MODEL.md` | Modelo de concurrencia |
| `WORKSPACE_STRUCTURE.md` | Estructura de workspace |