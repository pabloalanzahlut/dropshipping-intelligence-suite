# Skill: Resolver Problemas GitHub (Auto-Alimentado)

**ID:** `resolver_github`
**Versión:** 1.0.0
**Propósito:** Diagnosticar y resolver cualquier problema de GitHub (CI/CD, PRs, Dependabot, secretos, workflows, permisos) con memoria persistente de soluciones. Cada problema resuelto se ingresa automáticamente en la KB interna para acelerar futuras resoluciones.

**Trigger:** `/resolver-github` o cuando se detecta un problema de GitHub
**Input:** Descripción del problema + logs/screenshots opcionales
**Output primario:** Solución aplicada + incidencia documentada en KB
**Output secundario:** `ai_workspace/knowledge_base/github_kb.md` actualizado

> **Método Xavier:** Cada resolución exitosa alimenta la KB con la firma del error,
> la causa raíz y el fix comprobado. La segunda vez que aparezca el mismo problema,
> se resuelve sin intervención manual.

---

## Arquitectura del Skill

```
Usuario reporta problema GitHub
        ↓
[FASE 0] Consultar KB ← ¿Ya vimos este patrón?
        ├─ SÍ → Aplicar fix conocido directamente (< 2 min)
        └─ NO → Continuar diagnóstico
        ↓
[FASE 1] Clasificar problema (tipo + severidad)
        ↓
[FASE 2] Investigar causa raíz (logs, API REST, git)
        ↓
[FASE 3] Aplicar solución
        ↓
[FASE 4] Verificar (CI verde / PR mergeado / issue cerrado)
        ↓
[FASE 5] INGERIR EN KB ← Siempre, exitoso o no
        ↓
Informe al operador
```

---

## FASE 0 — Consulta KB (Auto-resolución)

Antes de cualquier diagnóstico, buscar en `ai_workspace/knowledge_base/github_kb.md` por:

1. **Firma del error** — primeras 60 chars del mensaje de error normalizado
2. **Tipo de problema** — de la clasificación de FASE 1
3. **Contexto** — workflow/job/step/herramienta involucrada

**Si hay match con confianza ≥ Alta:**
```
GITHUB_KB_HIT: [tipo] → Aplicando fix conocido: {descripcion_fix}
Fuente: {incidencia_id} | Fecha: {fecha} | Éxito previo: {n} veces
```
→ Aplicar directamente, saltando FASES 1-3
→ Pasar igualmente por FASE 4 (verificar) y FASE 5 (incrementar contador)

---

## FASE 1 — Clasificación del Problema

### Árbol de tipos

```
GITHUB_PROBLEM
├── CI_FAILURE          — Workflow rojo, job fallido
│   ├── BUILD           — Error de compilación / instalación
│   ├── TEST            — Tests fallidos
│   ├── LINT            — Linting / formato
│   ├── SECRETS_SCAN    — gitleaks / secret detection
│   └── PERMISSIONS     — Falta de permisos del token GITHUB_TOKEN
├── DEPENDABOT
│   ├── MERGE_CONFLICT  — PR de Dependabot en conflicto
│   ├── CI_RED          — CI falla en rama Dependabot
│   ├── DIRTY_PR        — PR no mergeable por estado del branch
│   └── VERSION_NONEXISTENT — Dependabot apunta a versión inexistente en PyPI/npm
├── PR_MANAGEMENT
│   ├── MERGE_BLOCKED   — Branch protection no cumplida
│   ├── REVIEW_REQUIRED — Falta review requerido
│   ├── OUT_OF_DATE     — Rama desactualizada respecto a base
│   └── CONFLICT        — Conflicto de merge
├── WORKFLOW_CONFIG
│   ├── SYNTAX_ERROR    — YAML inválido
│   ├── ACTION_VERSION  — Action usa Node deprecated (v6→v8)
│   ├── PATH_FILTER     — paths-filter mal configurado
│   └── RUNNER_COMPAT   — Incompatibilidad de runner (ubuntu-24 vs 26)
├── SECRETS_SECURITY
│   ├── ENV_TRACKED     — .env versionado accidentalmente
│   ├── KEY_EXPOSED     — Clave real en código/historial
│   ├── INJECTION_RISK  — ${{ secrets.X }} en run: (anti-patrón)
│   └── BINARY_BUNDLE   — Clave dentro de ejecutable distribuido
└── REPO_HEALTH
    ├── LABEL_MISSING   — Labels de triage no configurados
    ├── BRANCH_STALE    — Ramas abandonadas
    └── HOOK_FAILURE    — Pre-commit / post-commit hook fallido
```

### Severidad

| Nivel | Criterio | Tiempo máximo de respuesta |
|-------|----------|---------------------------|
| CRÍTICO | Secreto expuesto / clave en historial | Inmediato — revocar antes de fix |
| ALTO | CI roto en master / PR bloqueado | < 15 min |
| MEDIO | Dependabot acumulado / workflow lento | < 1 hora |
| BAJO | Labels / documentación / style | Próxima sesión |

---

## FASE 2 — Investigación (Herramientas disponibles)

### Sin gh CLI (usar API REST vía PowerShell/curl)

```powershell
# Listar PRs abiertos
Invoke-RestMethod -Uri "https://api.github.com/repos/{owner}/{repo}/pulls?state=open" `
  -Headers @{Authorization="token $env:GH_PAT"; "User-Agent"="GEM-OS"}

# Estado de CI de un commit
Invoke-RestMethod -Uri "https://api.github.com/repos/{owner}/{repo}/commits/{sha}/check-runs" `
  -Headers @{Authorization="token $env:GH_PAT"; "User-Agent"="GEM-OS"}

# Logs de un workflow run
Invoke-RestMethod -Uri "https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/logs" `
  -Headers @{Authorization="token $env:GH_PAT"; "User-Agent"="GEM-OS"} `
  -OutFile "$env:TEMP\logs.zip"
```

### Con gh CLI (si disponible)

```bash
gh pr list --state open
gh run list --limit 10
gh run view {run_id} --log
gh api repos/{owner}/{repo}/pulls/{number}/files
```

### Diagnóstico local

```bash
# Ver qué archivos están en staging (antes de commit)
git status --short
git diff --staged --name-only

# Verificar secretos localmente con gitleaks
gitleaks git . --config .gitleaks.toml --redact --verbose

# Ver historial de un archivo específico
git log --oneline --follow -- path/to/file

# Qué contiene el .env que NO debe estar versionado
git ls-files | grep -E '(^|/)\.env($|\.)'
```

---

## FASE 3 — Catálogo de Fixes Conocidos

### F-001: CI roto por grep false-positive en workflow

**Síntoma:** Step de validación falla porque grep encuentra el patrón dentro del propio workflow
**Causa:** El workflow busca una clave/patrón y la encuentra en su propia definición
**Fix:**
```yaml
# ANTES (problemático)
- run: grep -r "sk-or-v1-" . && exit 1

# DESPUÉS (correcto) — usar gitleaks o excluir el propio workflow
- run: |
    gitleaks git . --config .gitleaks.toml --redact --exit-code 1
```
**Tiempo:** 5 min | **Riesgo:** Bajo

---

### F-002: Dependabot PR con rama "dirty" (405 en merge API)

**Síntoma:** `Invoke-RestMethod` a `/merge` devuelve 405 — "Pull Request is not mergeable"
**Causa:** La rama del PR está desactualizada o tiene conflicto
**Fix (secuencia):**
```bash
# 1. Intentar update-branch vía API
POST /repos/{owner}/{repo}/pulls/{number}/update-branch

# 2. Si falla → cerrar el PR (Dependabot recreará)
PATCH /repos/{owner}/{repo}/pulls/{number}  body: {"state":"closed"}

# 3. Aplicar el bump manualmente en requirements.txt
# 4. Push → el nuevo PR de Dependabot se cierra automáticamente
```
**Tiempo:** 10 min | **Riesgo:** Bajo

---

### F-003: `pull_request` trigger ejecuta workflow del branch, no de master

**Síntoma:** Se arregla el workflow en master pero el PR sigue fallando
**Causa:** El evento `pull_request` ejecuta `.github/workflows/*.yml` del HEAD del PR, no de master
**Fix:**
```bash
# Mergear master en la rama del PR para que traiga el workflow corregido
git fetch origin master
git checkout {branch-del-pr}
git merge origin/master
git push origin {branch-del-pr}
# Ahora el PR tiene el workflow correcto y el CI se re-ejecuta
```
**Tiempo:** 5 min | **Riesgo:** Bajo

---

### F-004: actions/github-script usa Node 16/18 deprecated

**Síntoma:** Warning "Node.js 16 actions are deprecated" o fallo en runner nuevo
**Fix:**
```yaml
# Actualizar versión
uses: actions/github-script@v8   # Node 20+, compatible ubuntu-26
# No usar @v9 aún salvo que sea necesario — v8 es el balance estabilidad/modernidad
```
**Tiempo:** 2 min | **Riesgo:** Muy bajo

---

### F-005: gitleaks en CI — fallo por placeholder de clave en docs

**Síntoma:** gitleaks detecta `sk-or-v1-TU_CLAVE_AQUI` en README como secreto real
**Fix:** Agregar allowlist en `.gitleaks.toml`:
```toml
[[allowlists]]
description = "Placeholders documentados"
regexTarget = "secret"
regexes = [
  '''^sk-or-v1-(?:tu_clave|TU_API_KEY_AQUI|X{8,})$''',
]
```
**Tiempo:** 3 min | **Riesgo:** Muy bajo

---

### F-006: gitleaks incompatible con runner (ubuntu-26 / arm64)

**Síntoma:** gitleaks-action falla porque requiere Node / versión de runner no soportada
**Fix:** Usar binario estático con SHA-256 pinned:
```yaml
- name: Install gitleaks
  run: |
    case "$(uname -m)" in
      x86_64)  arch=x64;   sha="551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb" ;;
      aarch64) arch=arm64; sha="e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080" ;;
    esac
    tarball="gitleaks_8.30.1_linux_${arch}.tar.gz"
    curl -sSfL --retry 3 -o "$RUNNER_TEMP/$tarball" \
      "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/${tarball}"
    echo "${sha}  $RUNNER_TEMP/$tarball" | sha256sum -c -
    tar -xzf "$RUNNER_TEMP/$tarball" -C "$RUNNER_TEMP" gitleaks
    echo "$RUNNER_TEMP" >> "$GITHUB_PATH"
```
**Tiempo:** 10 min | **Riesgo:** Bajo

---

### F-007: secrets interpolados directamente en `run:` (injection risk)

**Síntoma:** `${{ secrets.TOKEN }}` aparece en bloque `run:` de un workflow
**Causa:** Anti-patrón — el valor del secreto puede ser inyectado si se controla el input
**Fix:**
```yaml
# ANTES (vulnerable)
- run: curl -H "Authorization: ${{ secrets.TOKEN }}" https://api.example.com

# DESPUÉS (seguro)
- run: curl -H "Authorization: $MY_TOKEN" https://api.example.com
  env:
    MY_TOKEN: ${{ secrets.TOKEN }}
```
**Tiempo:** 5 min por step | **Riesgo:** Bajo (fix preventivo)

---

### F-008: Versión de dependencia inexistente en PyPI

**Síntoma:** `pip install yt-dlp==2024.10.23` falla con "No matching distribution found"
**Fix:**
```bash
# Verificar versiones disponibles
pip index versions yt-dlp 2>/dev/null | head -3
# Usar la última estable o la más cercana disponible
# Actualizar requirements.txt con versión verificada
```
**Tiempo:** 3 min | **Riesgo:** Bajo

---

## FASE 4 — Verificación

Criterios de éxito por tipo:

| Tipo | Criterio de éxito |
|------|------------------|
| CI_FAILURE | Run verde en GitHub Actions (status: completed / conclusion: success) |
| DEPENDABOT | PR mergeado o cerrado + no reaparece en lista |
| PR_MANAGEMENT | PR en estado "merged" o "closed" según corresponda |
| WORKFLOW_CONFIG | Workflow ejecuta todos los steps sin error |
| SECRETS_SECURITY | gitleaks scan: "no leaks found" + .env no en `git ls-files` |
| REPO_HEALTH | Labels presentes / ramas limpias |

**No reportar éxito hasta verificar con una llamada real a la API o ver el CI verde.**

---

## FASE 5 — Ingestión en KB (Auto-alimentación)

**Obligatorio tras cada resolución, exitosa o fallida.**

### Estructura del registro

```markdown
## INC-{YYYYMMDD}-{NNN} | {TIPO} | {SEVERIDAD}

**Fecha:** {fecha}
**Repositorio:** {owner}/{repo}
**Firma del error:** {primeras 80 chars del mensaje normalizado}
**Causa raíz:** {explicación técnica en 1-2 frases}
**Fix aplicado:** {referencia a F-XXX o descripción nueva}
**Resultado:** ✅ RESUELTO | ❌ FALLIDO | ⚠️ WORKAROUND
**Tiempo total:** {minutos}
**Veces visto:** {n} (incrementar si era KB_HIT)
**Tags:** [{tipo}, {herramienta}, {runner_si_aplica}]
**Notas:** {cualquier detalle que acelere la próxima resolución}
```

### Destino

Agregar al final de `ai_workspace/knowledge_base/github_kb.md` (crear si no existe).

### Deduplicación

- Si la **firma del error** ya existe en la KB → NO crear nuevo registro, incrementar `Veces visto` del existente y actualizar `Notas` si hay información nueva.
- Normalización de firma: lowercase + eliminar números de línea/commit/sha + trim

---

## Reglas de Comportamiento del Agente

1. **NUNCA** reportar éxito sin haber verificado (FASE 4)
2. **SIEMPRE** ingerir en KB aunque el fix falle — el fracaso también es conocimiento
3. **Si hay secreto expuesto** → FASE 3 F-007 o equivalente + avisar al operador para revocar clave ANTES de continuar con cualquier otro fix
4. **Si no hay PAT disponible** → pedir al operador antes de intentar acciones sobre la API de GitHub
5. **Preferir API REST** sobre `gh` CLI (el CLI puede no estar instalado en el runner)
6. **No cerrar PRs de Dependabot** sin intentar primero el merge o update-branch — cerrar hace que Dependabot ignore esa versión

---

## Output esperado al operador

```
GITHUB_RESOLVER — {TIPO} | Severidad: {nivel}

📋 Problema detectado:
   {descripción clara en 1-2 frases}

🔍 Causa raíz:
   {causa técnica verificada}

🔧 Fix aplicado:
   {qué se hizo exactamente}

✅ Verificación:
   {evidencia — URL de run, status de PR, output de gitleaks}

📚 KB actualizada:
   INC-{id} registrado en github_kb.md
   {si era KB_HIT: "Resuelto en X min con fix conocido (F-XXX)"}

⚠️ Avisos pendientes (si aplica):
   {PAT a revocar / secreto en dist/ / anti-patrón encontrado}
```

---

## Integración con el Pipeline GEM OS

```
/resolver-github
        ↓
resolver_github (este skill)
        ↓
[FASE 5] → github_kb.md
        ↓
/consultar-kb → AgentExecutor puede consultar incidencias GitHub
                (tabla operations_traffic ← "operations" incluye CI/CD)
```

Los registros de GitHub también pueden ingresarse en `operations_traffic` de SQLite
usando el campo `logistics_notes` para la descripción del fix, permitiendo consultas
cruzadas desde el agente interno.
