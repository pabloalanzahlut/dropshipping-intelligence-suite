# 📋 MANUAL DE CUMPLIMIENTO GEM OS
**Versión:** 2.0 | **Fecha:** 2026-10-25 | **Estatus:** 🟢 VINCULANTE

---

## 🎯 Propósito

Este manual documenta el **Sistema de Gobernanza de Agentes** de GEM OS, que implementa las 4 metodologías obligatorias para todos los agentes del sistema.

---

## 📑 Estructura del Sistema de Gobernanza

```
📁 dropshipping_intelligence_suite/
│
├── 📄 agent.md                          ← Constitución suprema del agente
│
├── 📁 app/services/
│   ├── 📄 validator_rules.py            ← Validador de cumplimiento (3 fases)
│   ├── 📄 memory_logger.py              ← Bitácora de memoria activa
│   └── 📄 protocol_enforcer.py          ← Asegurador "preguntar antes de inventar"
│
├── 📁 app/agents_engine/
│   └── 📄 executor.py                   ← Orquestador integrado
│
├── 📁 app/ui/components/
│   └── 📄 governance_panel.py           ← UI de control de gobernanza
│
├── 📁 governance/
│   ├── 📁 memory/                       ← Archivos JSONL de memoria
│   └── 📁 tests/
│       └── 📄 test_governance.py        ← Tests de validación
│
└── 📄 COMPLIANCE_MANUAL.md              ← Este documento
```

---

## 🏛️ Las 4 Metodologías Implementadas

### 1️⃣ REGLA PRINCIPAL — Gestión y Estructura del Agente

| Componente | Archivo | Función |
|-----------|---------|---------|
| agent.md | `agent.md` | Constitución con reglas inmutables |
| No inventar | `protocol_enforcer.py` | `check_data_gaps()` |
| Memoria activa | `memory_logger.py` | `log()`, `get_context()` |

**Flujo:**
```
Agent recibe tarea → 
  ProtocolEnforcer.check_data_gaps() → 
    si faltan datos → preguntar al usuario
    si datos completos → MemoryLogger.log(data_received)
```

### 2️⃣ MÉTODO 1 — Herramientas Externas y Formato Técnico

| Herramienta | Uso | Validación |
|------------|-----|-----------|
| OpenRouter API | Llamadas a modelos IA | `executor.py` — endpoint `/api/v1/chat/completions` |
| SQLite | Persistencia relacional | `connection.py` — 5 tablas |
| YouTube API | Transcripciones | `youtube_channel_monitor.py` |
| Tkinter UI | Interfaz desktop | Paneles en `app/ui/components/` |

**Formato de salida requerido (JSON):**
```json
{
  "agent_id": "nombre_agente",
  "status": "success|error|warning",
  "data": {},
  "rules_compliance": { ... }
}
```

### 3️⃣ MÉTODO 2 — Agentes Encadenados y Memoria Secuencial

**Pipeline DAG:**
```
YouTube Monitor → TranscriptCleaner → Knowledge Base → 
  ├─ Product Hunter → FinancialValidator
  ├─ Funnel Builder → CopywritingEngine (AIDA)
  └─ Media Buyer → TikTokScriptGenerator
```

**Memoria secuencial:**
- `MemoryLogger.recall(agent_name)` → recupera historial del agente
- `MemoryLogger.get_context(agent_name)` → genera contexto para prompts

### 4️⃣ MÉTODO 3 — Manejo de Errores y Formato de Salida

| Nivel | Acción | Componente |
|-------|--------|-----------|
| INFO | Registrar | `MemoryLogger.log()` |
| WARNING | Registrar + Notificar | `MemoryLogger.log()` category='warning' |
| ERROR | Detener subtarea | `RulesValidator.post_execution_validation()` |
| CRITICAL | Detener todo | `ProtocolEnforcer.block_if_hallucinating()` |

---

## 🔄 Ciclo de Vida de una Ejecución

```
1. PRE-FLIGHT CHECK
   ├── agent.md cargado?              ← RulesValidator._check_agent_md()
   ├── No inventar configurado?       ← RulesValidator._check_no_invent_policy()
   ├── Memoria disponible?            ← RulesValidator._check_memory_available()
   └── Reglas negocio presentes?      ← RulesValidator._check_business_rules()

2. DATA GAP CHECK
   ├── ¿Faltan datos críticos?        ← ProtocolEnforcer.check_data_gaps()
   └── Si falta → preguntar usuario   ← ProtocolEnforcer.generate_questions_batch()

3. EJECUCIÓN
   ├── System prompt con contextos    ← AgentExecutor.execute_agent_task()
   ├── Memoria activa inyectada       ← MemoryLogger.get_context()
   └── Llamada a OpenRouter           ← requests.post()

4. POST-VALIDACIÓN
   ├── JSON válido?                   ← json.loads()
   ├── Superlativos prohibidos?       ← RulesValidator._detectar_superlativos()
   ├── Alucinaciones?                 ← RulesValidator._detect_hallucinations()
   └── Registrar en BD                ← RulesValidator._log_validation_result()

5. MEMORIA
   └── Log automático                 ← MemoryLogger.log()
```

---

## 📊 KPIs de Gobernanza

| KPI | Target | Cómo se mide |
|-----|--------|-------------|
| Cumplimiento global | ≥ 90% | `RulesValidator.compliance_score()` |
| Check pre-ejecución | 100% PASS | `pre_execution_check()` |
| Output sin alucinaciones | 100% | `post_execution_validation()` |
| Memoria registrada | 100% ejecuciones | `MemoryLogger.memory_stats()` |
| agent.md íntegro | 100% | `check_agent_md_integrity()` |

---

## 🚀 Cómo Usar

### Verificar estado desde UI:
1. Abrir la aplicación: `python app/main.py`
2. Ir al tab **"Control de Gobernanza v2.0"**
3. Ver scores, estado de metodologías, bitácora

### Verificar desde CLI:
```bash
python -c "
from app.services.validator_rules import RulesValidator
v = RulesValidator()
print(v.pre_execution_check())
"
```

### Ver memoria:
```bash
python -c "
from app.services.memory_logger import MemoryLogger
m = MemoryLogger()
print(m.memory_stats())
"
```

---

## 🔒 Inmutabilidad

Este manual es parte del sistema de gobernanza. Cualquier cambio debe ser:
1. Aprobado por el usuario
2. Versionado en el archivo
3. Registrado en la bitácora del sistema

---

*Generado por GEM OS Governance Core v2.0 — 2026-10-25*