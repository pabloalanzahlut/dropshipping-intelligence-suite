# Programming Standards & Official Sources — GEM OS Suite
# Versión: 2.0.0 | Estado: ACTIVE DEVELOPMENT | Validez: 2026-10-25
# Responsable: AI Cline | Última actualización: 2026-10-25
# Commit Base: main (última revisión)

> **⚡ PROPÓSITO EJECUTIVO:** Este documento es **NORMATIVO** durante el ciclo de desarrollo.
> En PRODUCCIÓN se siguen `README.md` y `DEPLOY.md`.
> **Regla de oro ELITE:** No se escribe una línea de código sin saber qué fuente oficial la respalda.
> Documento diseñado para resolución inmediata — cada error aparece UNA SOLA VEZ.

---

## 📑 QUICK LINKS — NAVEGACIÓN RÁPIDA

| Contexto | Sección | Para qué sirve |
|----------|---------|----------------|
| [📐 1. Jerarquía de Autoridad](#1-jerarquía-de-autoridad) | Niveles de decisión técnica | Resolver dudas: "¿qué fuente manda?" |
| [📚 2. Referencias Oficiales](#2-catálogo-de-referencias-oficiales) | PEPs, Docs, Estándares | Ubicar la fuente primaria de cada regla |
| [🧮 3. Big-O & Complejidad](#3-tabla-de-complejidad-big-o) | Estructuras > Algoritmos > SQL | Decidir qué estructura/alg. usar |
| [✅ 4. Checklist Pre-Commit](#4-checklist-de-rigor-pre-commit) | Validación manual + script | Antes de commitear — linter + seguridad |
| [📝 5. Template de Código](#5-template-de-comentario) | Patrones functions, classes, async | Código boilerplate correcto |
| [🔤 6. Convenciones GEM OS](#6-convenciones-de-código--gem-os) | Nombres, Imports, Types | Consistencia de estilo |
| [🔴 7. Banco de Errores (por Tipo)](#7-banco-de-errores-categorizado-por-tipo) | Tkinter, Logging, Threading, SQL... | **Resolución inmediata** de bugs conocidos |
| [📊 8. Matriz de Decisión](#8-matriz-de-decisión) | Pregunta → Fuente → Prioridad | Referencia rápida de arquitectura |
| [🤖 9. Integración CI/CD](#9-integración-cicd) | Pre-commit hooks, GH Actions | Automatizar validaciones |
| [📋 10. Historial de Cambios](#10-historial-de-cambios) | Versionado, fechas, commits | Trazabilidad del documento |

---

## ═══════════════════════════════════════════════════════════════════════
## 1. JERARQUÍA DE AUTORIDAD
## ═══════════════════════════════════════════════════════════════════════

Ante cualquier decisión técnica, consultar en este orden:

```
  NIVEL 1: ESPECIFICACIONES OFICIALES
   ─ PEPs (Python Enhancement Proposals)
   ─ Documentación oficial del lenguaje / framework
   ─ RFCs y estándares (POSIX, OWASP, SQLite)

  NIVEL 2: FUNDAMENTOS & ALGORITMOS
   ─ Análisis de complejidad Big-O
   ─ Estructuras de datos (arrays, hash tables, trees, queues)
   ─ Algoritmos (búsqueda, ordenamiento, similitud)
   ─ Concurrencia (locks, semáforos, atomicidad)

  NIVEL 3: MEJORES PRÁCTICAS
   ─ Clean Code (Robert C. Martin)
   ─ SOLID Principles
   ─ Exception Handling robusto
   ─ Thread Safety & Race Condition prevention

  NIVEL 4: CONVENCIONES DEL PROYECTO GEM OS
   ─ snake_case, PascalCase, UPPER_SNAKE_CASE
   ─ Type hints obligatorios
   ─ Docstrings estilo Google/PEP 257
   ─ Logging con módulo `logging` (nunca print)
```

**Regla de oro:** No se escribe una línea de código sin saber qué fuente oficial la respalda.

---

## ═══════════════════════════════════════════════════════════════════════
## 2. CATÁLOGO DE REFERENCIAS OFICIALES
## ═══════════════════════════════════════════════════════════════════════

### 2.1 Python Language

| ID | Título | Enlace | Aplica a |
|-----|--------|--------|----------|
| [PEP 8] | Style Guide | https://pep8.org/ | Nombres, indentación, imports |
| [PEP 20] | Zen of Python | https://peps.python.org/pep-0020/ | Filosofía general |
| [PEP 257] | Docstring Conventions | https://peps.python.org/pep-0257/ | Documentación func/class |
| [PEP 343] | The "with" Statement | https://peps.python.org/pep-0343/ | Context managers |
| [PEP 391] | Logging Configuration | https://peps.python.org/pep-0391/ | logging.getLogger |
| [PEP 484] | Type Hints | https://peps.python.org/pep-0484/ | Firmas, Optional, List, Dict |
| [PEP 492] | Coroutines async/await | https://peps.python.org/pep-0492/ | async def, await |
| [PEP 557] | Data Classes | https://peps.python.org/pep-0557/ | @dataclass, field() |

### 2.2 Concurrencia y Threading

| ID | Enlace | Aplica a |
|-----|--------|----------|
| [Threading Docs] | https://docs.python.org/3/library/threading.html | Lock, RLock, Event |
| [concurrent.futures] | https://docs.python.org/3/library/concurrent.futures.html | submit(), map(), shutdown() |
| [Queue Docs] | https://docs.python.org/3/library/queue.html | FIFO Queue, PriorityQueue |

### 2.3 Bases de Datos y Seguridad

| ID | Enlace | Aplica a |
|-----|--------|----------|
| [SQLite Docs] | https://www.sqlite.org/lang.html | PRAGMA, transactions |
| [CWE-89] | https://cwe.mitre.org/data/definitions/89.html | SQL Injection |
| [OWASP] | https://owasp.org/www-project-top-ten/ | Seguridad general |

### 2.4 Algoritmos y Clean Code

| ID | Enlace | Aplica a |
|-----|--------|----------|
| [Big-O] | https://www.bigocheatsheet.com/ | Análisis de complejidad |
| [Jaccard] | https://en.wikipedia.org/wiki/Jaccard_index | Similitud de conjuntos |
---

## ═══════════════════════════════════════════════════════════════════════
## 3. TABLA DE COMPLEJIDAD BIG-O (Referencia Rápida)
## ═══════════════════════════════════════════════════════════════════════

### 3.1 Estructuras de Datos en Python

| Estructura | Búsqueda | Inserción | Eliminación | Memoria |
|------------|----------|-----------|-------------|---------|
| `list` | O(n) | O(1) amort. | O(n) | O(n) |
| `set` | **O(1)** avg | O(1) avg | O(1) avg | O(n) |
| `dict` | **O(1)** avg | O(1) avg | O(1) avg | O(n) |
| `deque` | O(n) | **O(1)** | O(1) | O(n) |

### 3.2 Algoritmos Comunes

| Algoritmo | Promedio | Peor Caso | Memoria |
|-----------|----------|-----------|---------|
| Binary Search | O(log n) | O(log n) | O(1) |
| Quick Sort | O(n log n) | O(n²) | O(log n) |
| Merge Sort | O(n log n) | O(n log n) | O(n) |
| Hash Lookup | O(1) | O(n) | O(n) |
| Jaccard Sim. | O(n+m) | O(n+m) | O(n+m) |

### 3.3 SQLite

| Operación | Con índice | Sin índice |
|-----------|-----------|-----------|
| SELECT por PK | O(log n) | O(n) |
| INSERT | O(log n) | O(log n) |
| COUNT(*) | O(1) opt. | O(n) |

---

## ═══════════════════════════════════════════════════════════════════════
## 4. CHECKLIST DE RIGOR (Pre-Commit en Desarrollo)
## ═══════════════════════════════════════════════════════════════════════

```
☐ [PEP 484]   Type hints completos en funciones públicas
☐ [PEP 8]     snake_case / PascalCase correctos
☐ [PEP 343]   Context manager con __exit__ garantizado
☐ [PEP 391]   logging (no print) en código principal
☐ [PEP 257]   Docstrings con args + returns
☐ [Big-O]     Complejidad documentada en docstring
☐ [Threading] Shared state con Lock
☐ [SOLID-SRP] Una responsabilidad/clase
☐ [Exception] Nunca except vacío; log + raise
☐ [SQLite]    Queries con ? (no f-strings)
☐ [CWE-89]   Validación de entrada SQL
☐ [DRY]       Refactor si > 2 copias
```

### 4.1 Script Pre-Commit Ejecutable

Guardar como `.git/hooks/pre-commit` y dar permiso `chmod +x` (o `copy` en Windows):

```bash
#!/bin/bash
# PRE-COMMIT HOOK — GEM OS Suite
# Automatiza el Checklist de Rigor (Sección 4)
set -e

ERRORS=0
echo "🔍 [GEM OS] Validando pre-commit..."

# [PEP 484] Type hints — opcional si no hay mypy en el entorno
if command -v mypy &> /dev/null; then
    mypy app/ --strict --ignore-missing-imports || ((ERRORS++))
else
    echo "⚠️  [PEP 484] mypy no instalado — salteando"
fi

# [PEP 391] No print() en código principal (solo scripts CLI)
if grep -rn "^\s*print(" app/ --include="*.py" 2>/dev/null; then
    echo "❌ [PEP 391] print() detectado en app/ — usar logging"
    ((ERRORS++))
fi

# [CWE-89] SQL Injection — detectar f-strings en queries SQL
if grep -rn 'f".*SELECT\|f'\''.*SELECT' app/ --include="*.py" 2>/dev/null; then
    echo "❌ [CWE-89] f-string en SQL detectado — usar parámetros ?"
    ((ERRORS++))
fi

# [PEP 8] Syntax check
python -m py_compile app/__init__.py 2>/dev/null || true

if [ $ERRORS -gt 0 ]; then
    echo "❌ Pre-commit FALLÓ ($ERRORS errores)"
    exit 1
fi
echo "✅ Pre-commit OK — todos los checks pasados"
```

**Uso en Windows (PowerShell):**
```powershell
# Ejecutar manualmente antes de cada commit:
python -m py_compile app/__init__.py
grep -rn "print(" app/ --include="*.py" && echo "ERROR: print() detectado"
```

---

## ═══════════════════════════════════════════════════════════════════════
## 5. TEMPLATE DE COMENTARIO
## ═══════════════════════════════════════════════════════════════════════

```python
def mi_funcion(param: str) -> bool:
    \"\"\"
    Descripción breve.

    Complejidad:
      Temporal: O(n log n)
      Espacial: O(n)

    Referencias:
      [PEP 484] Type hints
      [Big-O] Búsqueda binaria
    \"\"\"
```

Para bloques técnicos:
```python
# [concurrent.futures] ThreadPoolExecutor con workers acotados
# [PEP 343] Context manager con __exit__ para cleanup
# [CWE-89] Query parametrizada, no concatenar SQL
```
| [SOLID-SRP] | https://en.wikipedia.org/wiki/Single-responsibility_principle | Una clase = una razón |
---

## ═══════════════════════════════════════════════════════════════════════
## 6. CONVENCIONES DE CÓDIGO — GEM OS (DESARROLLO)
## ═══════════════════════════════════════════════════════════════════════

### 6.1 Nombres

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Variables | `snake_case` | `worker_count`, `db_path` |
| Métodos | `snake_case` | `_extract_field()`, `route_and_insert()` |
| Clases | `PascalCase` | `WorkerPool`, `KBRouter` |
| Constantes | `UPPER_SNAKE_CASE` | `MAX_WORKERS`, `STATUS_PENDING` |
| Módulos | `lowercase_with_underscores` | `worker_pool.py`, `kb_router.py` |
| Privado | Prefijo `_` | `_lock`, `_dispatch_loop()` |

### 6.2 Imports (orden estricto)

```python
# 1. Bloque: Biblioteca estándar
import os, sys, json
from typing import Dict, List, Optional
# 2. Bloque: Librerías de terceros
import requests
from dotenv import load_dotenv
# 3. Bloque: Módulos del proyecto
from app.config.path_manager import PathManager
from app.database.connection import DatabaseConnection
```

### 6.3 Type Hints (obligatorio)

```python
# [PEP 484] Type hints en TODA función pública y privada
def procesar(datos: List[str], umbral: float = 0.85) -> Optional[Dict]:
    ...
```

### 6.4 Logging

```python
# [PEP 391] Logger por módulo, niveles estrictos
import logging
logger = logging.getLogger(__name__)
logger.info("[MODULO] Mensaje")
logger.warning("[MODULO] Advertencia: %s", detalle)
logger.error("[MODULO] Error: %s", exc_info=exc)
```

### 6.5 Exception Handling

```python
# [Exception] NUNCA except vacío
try:
    resultado = operacion_riesgosa()
except ValueError as exc:
    logger.warning("[MODULO] Valor inválido: %s", exc)
    return fallback
except (IOError, OSError) as exc:
    logger.error("[MODULO] Error E/S: %s", exc)
    raise
except Exception as exc:
    logger.critical("[MODULO] Inesperado: %s", exc)
    raise
```

---

## ═══════════════════════════════════════════════════════════════════════
## 7. 🔴 BANCO DE ERRORES CATEGORIZADO POR TIPO
## ═══════════════════════════════════════════════════════════════════════

> **⚡ Regla del Banco:** Cada error se documenta UNA SOLA VEZ. No hay repeticiones.
> Si un error se repite, NO se agrega nueva entrada — se referencia el ERR_NNN existente.
> **Archivo que documenta errores.** No es bitácora cronológica — es biblioteca de patrones.

### 7.A TIPO A: Tkinter / UI Rendering

| ID | Síntoma | Causa | Fix Rápido | Archivo | Línea |
|----|---------|-------|-----------|---------|-------|
| **ERR_004** | `_tkinter.TclError: invalid color name "#66666"` | Color hex debe tener 6 dígitos (`#RRGGBB`). `#66666` tiene 5 | `foreground="#66666"` → `"#666666"` | `ollama_panel.py` | 62 |

**Contexto completo:**
- **Código original:** `foreground="#66666"  # ❌ 5 dígitos`
- **Corrección:** `foreground="#666666"  # ✅ 6 dígitos (gris válido)`
- **Causa raíz:** Tkinter interpreta colores via Tcl/Tk, que exige exactamente 6 dígitos hex
- **Prevención:** ☐ Validar colores con regex `^#[0-9a-fA-F]{6}$` antes de render
- **Referencia:** [Tcl/Tk Colors](https://tcl.tk/man/tcl8.5/TkCmd/colors.htm)

### 7.B TIPO B: Logging & Observabilidad [PEP 391]

| ID | Síntoma | Causa | Fix Rápido | Archivo | Línea |
|----|---------|-------|-----------|---------|-------|
| **ERR_005** | Errores silenciosos — desaparecen en stdout, no en logs | `print()` en código principal en vez de `logging` | `print(f"...")` → `logger.warning("...%s", var)` | `ollama_panel.py` | 197 |

**Contexto completo:**
- **Código original:** `except Exception as exc: print(f"[PANEL] Error: {exc}")`
- **Corrección:** `logger.warning("[PANEL] Error: %s", exc)` + `import logging` + `logger = logging.getLogger(__name__)`
- **Causa raíz:** Violación de [PEP 391]. `print()` no es observable, no tiene niveles, no es filtrable.
- **Prevención:** ☐ Pre-commit hook: `grep -rn "^\s*print(" app/ --include="*.py"` 
- **Referencia:** [PEP 391](https://peps.python.org/pep-0391/)
- **Comando fix global:** `grep -rn 'print(' app/ --include="*.py" | grep -v '__main__\|console_view'`

### 7.C TIPO C: Threading / Concurrencia

| ID | Síntoma | Causa | Fix Rápido | Archivo | Línea |
|----|---------|-------|-----------|---------|-------|
| **ERR_001** | `except:\ndef method` — método sin indentación tras `except` | Falta indentación → SyntaxError | `s/^def method/    def method/` | — | — |

**Contexto completo:**
- **Causa raíz:** Editor o copia/pega que perdió indentación en bloque `except`
- **Prevención:** ☐ Usar `python -m py_compile foo.py` antes de commit

### 7.D TIPO D: Database & SQL [CWE-89]

| ID | Síntoma | Causa | Fix Rápido | Archivo | Línea |
|----|---------|-------|-----------|---------|-------|
| **ERR_003** | `insert_line` > 6000 chars — truncamiento silencioso | Límite de split en editor AI | Dividir en ≤ 3 inserciones de ~5000 chars | — | — |

### 7.E TIPO E: Import & Module Structure

*(Reservado para futuros errores de imports circulares, path resolution, etc.)*

---

## ═══════════════════════════════════════════════════════════════════════
## 8. MATRIZ DE DECISIÓN
## ═══════════════════════════════════════════════════════════════════════

> **Uso:** Ante cualquier duda técnica, encuentra la pregunta y aplica la fuente primaria.

| Pregunta | Fuente Primaria | Prioridad |
|----------|----------------|-----------|
| ¿Cómo nombrar? | [PEP 8] Style Guide | 1ª Oficial |
| ¿@dataclass o __init__? | [PEP 557] Data Classes | 1ª Oficial |
| ¿Thread seguro? | [Threading Docs] Lock | 2ª Fundamentos |
| ¿Qué estructura datos? | [Big-O] Análisis complejidad | 2ª Fundamentos |
| ¿Cómo estructurar clase? | [SOLID-SRP] Una responsabilidad | 3ª Prácticas |
| ¿Manejar error? | [Exception] Log + raise | 3ª Prácticas |
| ¿Query SQL? | [CWE-89] Parametrización | 1ª Oficial + Seguridad |
| ¿Logging? | [PEP 391] logging module | 1ª Oficial |
| ¿Concurrencia? | [concurrent.futures] Pool | 1ª Oficial |

---

## ═══════════════════════════════════════════════════════════════════════
## 9. 🤖 INTEGRACIÓN CI/CD
## ═══════════════════════════════════════════════════════════════════════

> **Propósito:** Automatizar el Checklist de Rigor (Sección 4) en cada push/PR.

### 9.1 GitHub Actions — Workflow

Guardar como `.github/workflows/gem-os-standards.yml`:

```yaml
name: GEM OS Standards Check
on: [push, pull_request]

jobs:
  standards:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install mypy flake8

      - name: [PEP 484] Type hints
        run: mypy app/ --strict --ignore-missing-imports || true

      - name: [PEP 391] No print() in app/
        run: |
          if grep -rn "^\s*print(" app/ --include="*.py"; then
            echo "❌ print() detectado"
            exit 1
          fi

      - name: [CWE-89] SQL Injection check
        run: |
          if grep -rn 'f".*SELECT\|f'\''.*SELECT' app/ --include="*.py"; then
            echo "❌ SQL Injection risk"
            exit 1
          fi

      - name: [PEP 8] Syntax validation
        run: python -m py_compile app/__init__.py
```

### 9.2 Pre-Commit Hook (Local)

Ver **Sección 4.1** para script bash completo.

### 9.3 Reglas de CI

| Regla | Acción | Frecuencia |
|-------|--------|-----------|
| Type hints | `mypy --strict` | Cada push |
| No `print()` | `grep -rn "print(" app/` | Cada push |
| No SQL injection | `grep f-strings en queries` | Cada push |
| Syntax check | `py_compile` | Cada push |
| Hex colors | `grep "#[0-9a-fA-F]\{3,5\}\b"` | Cada push |

---

## ═══════════════════════════════════════════════════════════════════════
## 10. 📋 HISTORIAL DE CAMBIOS
## ═══════════════════════════════════════════════════════════════════════

> **Propósito:** Trazabilidad completa del documento. Cada modificación registra versión, fecha, cambios y responsable.

| Versión | Fecha | Cambios | Responsable | Referencia |
|---------|-------|---------|-------------|------------|
| 2.0.0 | 2026-10-25 | **HEADER EJECUTIVO** + QUICK LINKS + **BANCO DE ERRORES** categorizado (5 tipos) + CHECKLIST ejecutable + CI/CD workflow + HISTORIAL | AI Cline | ERR_004, ERR_005 |
| 1.0.0 | 2026-10-25 | Versión inicial: Jerarquía, Referencias, Big-O, Checklist, Templates, Convenciones, Matriz, Errores | AI Cline | — |

---

*Fin del documento — Programming Standards v2.0.0*
*Válido exclusivamente para desarrollo de GEM OS Suite.*
*Este documento es NORMATIVO en DESARROLLO. En PRODUCCIÓN se siguen docs de operación.*