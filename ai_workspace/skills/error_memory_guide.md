# 🧠 ERROR MEMORY GUIDE — Sistema de Auto-Resolución de Errores

**Versión:** 1.0 — **Estatus:** 🟢 OPERATIVO

---

## 📋 Descripción

Sistema que **recuerda errores** para que a la **segunda vez que ocurran** se resuelvan automáticamente sin intervención manual.

### Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                  error_auto_resolver.py              │
│  ┌──────────────────────────────────────────────┐   │
│  │  @remember_and_resolve()  decorador          │   │
│  │  with auto_recovery():    context manager    │   │
│  │  @resolve_with_strategy() decorador directo  │   │
│  └──────────┬───────────────────────────────────┘   │
│             │ consulta                              │
│             ▼                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │      ErrorKnowledgeRegistry (Singleton)       │   │
│  │  ┌────────────┐    ┌──────────────────────┐  │   │
│  │  │ Caché en   │    │  SQLite (persistente) │  │   │
│  │  │ memoria    │    │  error_knowledge      │  │   │
│  │  │ O(1) lookup│    │  tabla                │  │   │
│  │  └────────────┘    └──────────────────────┘  │   │
│  └──────────────────────────────────────────────┘   │
│             │ exporta                               │
│             ▼                                       │
│  governance/memory/error_memory.json                │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Uso Básico

### Decorador `@remember_and_resolve()`

```python
from app.core.error_auto_resolver import remember_and_resolve

@remember_and_resolve()
def procesar_transcripcion(video_id: str):
    # Si falla la 1ra vez → se registra
    # Si falla la 2da vez → se resuelve automáticamente
    resultado = api_riesgosa(video_id)
    return resultado
```

### Context Manager `auto_recovery`

```python
from app.core.error_auto_resolver import auto_recovery

with auto_recovery(module='kb_router') as recovery:
    datos = consultar_base_datos()
    if recovery.recovered:
        logger.info("Error recuperado automáticamente")
```

### Estrategia Forzada

```python
from app.core.error_auto_resolver import resolve_with_strategy

@resolve_with_strategy('retry_with_backoff')
def llamada_openrouter(prompt: str):
    return client.chat(prompt)
```

---

## 🎯 Estrategias de Resolución

| Estrategia | Qué hace | Cuándo usarla |
|-----------|----------|---------------|
| `retry_once` | Reintenta la función 1 vez | Errores transitorios (timeout, rate limit) |
| `retry_with_backoff` | Espera 2s y reintenta | APIs con rate limiting (429) |
| `return_default` | Retorna `None` y sigue | Errores no críticos (caché, logging) |
| `log_and_raise` | Loggea y relanza | Errores irrecuperables (BD corrupta) |

---

## 🔧 Integración con Módulos Existentes

### En `executor.py` (agentes)

```python
from app.core.error_auto_resolver import remember_and_resolve

class AgentExecutor:
    @remember_and_resolve(module='agent_executor')
    def execute_agent(self, agent_name: str, task: dict):
        # ... lógica existente ...
        pass
```

### En `memory_logger.py`

El `MemoryLogger.log_error()` ya registra en SQLite. El `ErrorKnowledgeRegistry` usa la **misma BD** pero tabla separada (`error_knowledge`). No hay conflicto.

### En `retry_decorator.py`

El `@remember_and_resolve` es **complementario** a `@with_retry`:
- `@with_retry` → reintenta N veces con backoff
- `@remember_and_resolve` → recuerda el error para la PRÓXIMA ejecución

Puedes combinarlos:

```python
@with_retry(max_retries=3)
@remember_and_resolve()
def mi_funcion():
    ...
```

---

## 📊 API del Registry

```python
from app.core.error_knowledge_registry import error_kb

# Registrar error manualmente
record = error_kb.register_error(exc, module='mi_modulo', function='mi_func')

# Buscar si un error es conocido
record = error_kb.find_error(exc)

# ¿Tiene solución?
if error_kb.has_solution(exc):
    solucion = error_kb.get_solution(exc)

# Marcar como resuelto
error_kb.mark_resolved(exc, strategy='retry_once')

# Estadísticas
stats = error_kb.get_stats()
# → {'total_known_errors': 5, 'resolved_errors': 3, ...}

# Exportar a JSON
error_kb.export_to_json()
```

---

## 🗄️ Estructura en BD

Tabla: `error_knowledge` (en `data/dropshipping_suite.db`)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `signature_hash` | TEXT PK | Hash SHA256 del error (fingerprint) |
| `exception_type` | TEXT | Tipo de excepción (ValueError, ConnectionError...) |
| `exception_message` | TEXT | Mensaje del error (truncado a 200 chars) |
| `module` | TEXT | Módulo donde ocurrió |
| `function` | TEXT | Función donde ocurrió |
| `occurrence_count` | INTEGER | Veces que ha ocurrido |
| `first_seen` | TEXT | ISO8601 primera vez |
| `last_seen` | TEXT | ISO8601 última vez |
| `resolved` | INTEGER | 0=no resuelto, 1=resuelto |
| `resolution_strategy` | TEXT | Estrategia que lo resuelve |
| `context_hint` | TEXT | JSON con contexto adicional |
| `stacktrace_sample` | TEXT | Últimas líneas del traceback |

---

## 📁 Archivos del Sistema

| Archivo | Propósito | Creado por |
|---------|-----------|------------|
| `app/core/error_knowledge_registry.py` | Singleton + persistencia | ✅ Este proyecto |
| `app/core/error_auto_resolver.py` | Decoradores + context managers | ✅ Este proyecto |
| `governance/memory/error_memory.json` | Export JSON del knowledge base | `error_kb.export_to_json()` |
| `data/dropshipping_suite.db` → tabla `error_knowledge` | Persistencia SQLite | Automático al iniciar |

---

## 📚 Fuentes Oficiales

| Concepto | Fuente |
|----------|--------|
| Singleton Pattern | Gang of Four — Design Patterns |
| Decorators | PEP 318 — [python.org/dev/peps/pep-0318](https://www.python.org/dev/peps/pep-0318/) |
| Context Managers | PEP 343 — [python.org/dev/peps/pep-0343](https://www.python.org/dev/peps/pep-0343/) |
| functools.wraps | PEP 378 — [python.org/dev/peps/pep-0378](https://www.python.org/dev/peps/pep-0378/) |
| Exception Handling | PEP 8 — [python.org/dev/peps/pep-0008](https://www.python.org/dev/peps/pep-0008/) |
| Logging | [docs.python.org/3/library/logging](https://docs.python.org/3/library/logging.html) |
| JSON | [docs.python.org/3/library/json](https://docs.python.org/3/library/json.html) |
| traceback | [docs.python.org/3/library/traceback](https://docs.python.org/3/library/traceback.html) |

---

## ✅ Checklist de Implementación

- [x] `app/core/error_knowledge_registry.py` — Singleton + SQLite + caché
- [x] `app/core/error_auto_resolver.py` — Decoradores + context managers
- [ ] `governance/memory/error_memory.json` — Export automático (1er error)
- [ ] Integración con `executor.py` — `@remember_and_resolve` en agentes
- [ ] Integración con `memory_logger.py` — Conexión al registry
- [ ] Integración con `retry_decorator.py` — Compatibilidad garantizada

---

*Generado por GEM OS Governance Core v2.0 — 2026-10-31*