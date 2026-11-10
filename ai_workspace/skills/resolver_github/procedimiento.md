# Skill: GitHub Expert Agent — Resolución Automática con Memoria

**ID:** `resolver_github`
**Versión:** 3.0.0
**Propósito:** Agente experto en GitHub con 30+ años de experiencia simulada. Hace relevamiento completo del repositorio, detecta todos los problemas, los almacena en KB y los resuelve automáticamente. Segunda vez que aparece el mismo patrón → resolución en < 2 min sin intervención.

**Trigger:** `/resolver-github`
**Input:** Ninguno requerido (hace relevamiento automático) | Opcional: descripción específica
**Output:** Todos los problemas resueltos + KB actualizada + informe de estado

---

## MODO AUTÓNOMO (v3.0) — no requiere invocación

El agente corre solo en GitHub Actions (`.github/workflows/self-heal.yml`): ante un CI fallido, PR de Dependabot, o a diario.
Código: `scripts/github_self_heal.py` (Python puro, sin LLM). Catálogo: `ai_workspace/config/github_fixes.json`.

| Situación | Acción automática |
|-----------|-------------------|
| Firma con fix `auto` (F-002, F-004, F-005/F-012, F-007, F-008, F-009, F-010) | Rama `selfheal/*` → gitleaks local → PR → merge squash → INC en KB, contador +1 |
| Falso positivo gitleaks (entropía < 4.0 y valor placeholder) | Regex exacta en `.gitleaks.toml` (F-012) |
| **Fuga real** (entropía ≥ 4.0, regla específica o valor no verificable) | Issue crítico. **Nunca reescribe el historial**: rotar la credencial |
| Firma desconocida | Issue `selfheal:nuevo`; al resolverlo, añadir fila F-xxx a la KB **y** a `github_fixes.json` |
| Dependabot obsoleto (requirements ya ≥ versión) | Cierra el PR |
| README desfasado | `scripts/sync_readme.py` lo regenera y lo commitea |

Límites: máx. 2 PRs automáticos/día; nunca toca `CLAUDE.md`, `.claude/memory/`, validador/gate financiero ni `validate-pipeline.yml`.
Local: `python scripts/github_self_heal.py --dry-run [--log-file run.log]`.

---

## FASE 0 — RELEVAMIENTO AUTOMÁTICO (siempre al iniciar)

Antes de cualquier acción, el agente hace un scan completo del repositorio:

```
1. Leer KB existente: ai_workspace/knowledge_base/github_kb.md
2. Verificar CI/CD: últimas 20 runs → identificar patrones de fallo
3. Verificar PRs abiertos: Dependabot + otros
4. Verificar workflows: versiones, compatibilidad ubuntu-latest
5. Verificar secretos: gitleaks scan local si es posible
6. Verificar historial de commits: archivos sensibles
7. Generar lista priorizada de problemas
```

### Consulta REST API — Relevamiento

```powershell
$REPO = "pabloalanzahlut/dropshipping-intelligence-suite"
$TOKEN = $env:GITHUB_TOKEN  # o usar gh auth token

# Últimas runs fallidas
Invoke-RestMethod "https://api.github.com/repos/$REPO/actions/runs?status=failure&per_page=10" `
  -Headers @{Authorization="Bearer $TOKEN"; "X-GitHub-Api-Version"="2022-11-28"} |
  Select-Object -ExpandProperty workflow_runs |
  Select-Object name, conclusion, created_at, head_sha

# PRs abiertos
Invoke-RestMethod "https://api.github.com/repos/$REPO/pulls?state=open&per_page=20" `
  -Headers @{Authorization="Bearer $TOKEN"; "X-GitHub-Api-Version"="2022-11-28"} |
  Select-Object title, number, user, labels

# Alertas de seguridad (Dependabot)
Invoke-RestMethod "https://api.github.com/repos/$REPO/dependabot/alerts?state=open&per_page=20" `
  -Headers @{Authorization="Bearer $TOKEN"; "X-GitHub-Api-Version"="2022-11-28"} |
  Select-Object number, state, security_advisory
```

---

## FASE 1 — CONSULTAR KB (< 2 min si el patrón existe)

```
1. Leer ai_workspace/knowledge_base/github_kb.md
2. Buscar firma del error en la tabla de Fixes Reutilizables
3. Si encontrado → ir directamente a FASE 4 con el fix conocido
4. Si no encontrado → continuar a FASE 2
```

**Criterios de match (en orden de prioridad):**
- Fingerprint exacto de gitleaks (si es leak)
- RuleID + File pattern (si es CI)
- Mensaje de error normalizado (eliminar hashes, fechas, versiones variables)
- Tipo de problema + workflow afectado

---

## FASE 2 — CLASIFICAR PROBLEMA

| Tipo | Firma | Fix habitual |
|------|-------|--------------|
| `SECRETS_SCAN` | gitleaks exit 1, leaks found: N | Allowlist o filter-repo |
| `DEPENDABOT_PR` | PR de dependabot abierto/dirty | Merge o bump manual |
| `CI_FAILURE` | steps fallando en workflow | Ver step específico |
| `WORKFLOW_CONFIG` | action deprecated, node version | Actualizar versión action |
| `RUNNER_COMPAT` | ubuntu-latest + tool incompatible | Binario estático o fix |
| `SECRETS_TRACKED` | archivo con credenciales en git | git rm --cached + .gitignore |
| `HISTORY_LEAK` | secret en historial de git | git filter-repo + force push |
| `INJECTION_RISK` | ${{ secrets.X }} en run: | Mover a env: del step |

**Severidad:**
- CRÍTICO: secretos reales en repo/historial → resolver en < 1h
- ALTO: CI bloqueado → resolver en < 4h
- MEDIO: PRs acumulados, deprecaciones → resolver en < 24h
- BAJO: cosmético, buenas prácticas → resolver en próximo ciclo

---

## FASE 3 — INVESTIGAR CAUSA RAÍZ

### Para CI_FAILURE / SECRETS_SCAN:
```powershell
# Obtener job ID del run fallido
$run = Invoke-RestMethod "https://api.github.com/repos/$REPO/actions/runs?status=failure&per_page=1" `
  -Headers @{Authorization="Bearer $TOKEN"; "X-GitHub-Api-Version"="2022-11-28"}
$runId = $run.workflow_runs[0].id

# Obtener jobs del run
$jobs = Invoke-RestMethod "https://api.github.com/repos/$REPO/actions/runs/$runId/jobs" `
  -Headers @{Authorization="Bearer $TOKEN"; "X-GitHub-Api-Version"="2022-11-28"}
$jobId = $jobs.jobs[0].id

# Obtener logs del job (URL pre-firmada, descargar y leer)
$logUrl = Invoke-RestMethod "https://api.github.com/repos/$REPO/actions/jobs/$jobId/logs" `
  -Headers @{Authorization="Bearer $TOKEN"; "X-GitHub-Api-Version"="2022-11-28"; Accept="application/vnd.github+json"}
```

### Para SECRETS_SCAN — extraer fingerpint exacto:
Del log de gitleaks, capturar:
- `RuleID`: el tipo de secreto detectado
- `File`: archivo afectado
- `Commit`: hash del commit que lo introdujo
- `Line`: línea exacta
- `Fingerprint`: ID único `{commit}:{file}:{rule}:{line}`

**Nunca copies el valor detectado a la KB ni a ningún informe** (ni siquiera si parece de prueba): el `.exe` se
empaqueta con `ai_workspace/` y su verificación de seguridad rechaza cadenas con forma de clave. Anota solo el
tipo, el prefijo y la longitud, p. ej. `sk-or-v1-… (34 car.)`.

---

## FASE 4 — CATÁLOGO DE FIXES

### F-001 | grep false-positive en CI
**Problema:** step de scan busca patrones y encuentra su propio código
**Fix:**
```bash
# Reemplazar grep por gitleaks en validate-pipeline.yml
# Ver F-006 para instalación de gitleaks
```

### F-002 | Dependabot PR dirty / no mergeable
**Fix:**
```powershell
# Cerrar PR y aplicar bump manual
$prNumber = 4  # número del PR
Invoke-RestMethod "https://api.github.com/repos/$REPO/pulls/$prNumber" `
  -Method PATCH -Body '{"state":"closed"}' `
  -Headers @{Authorization="Bearer $TOKEN"; "Content-Type"="application/json"}
# Luego editar requirements.txt con la versión correcta
```

### F-003 | Workflow ejecuta en rama equivocada
**Fix:**
```bash
git checkout master
git merge origin/dependabot/pip/paquete
git push origin master
```

### F-004 | actions/github-script versión deprecated (Node 16)
**Fix en workflow YAML:**
```yaml
# Antes:
uses: actions/github-script@v7
# Después:
uses: actions/github-script@v8
```

### F-005 | gitleaks detecta placeholder como secreto real
**Fix en .gitleaks.toml:**
```toml
[[allowlists]]
description = "Placeholders en docs y .env.example"
regexTarget = "secret"
regexes = [
  '''^sk-or-v1-(?:tu_clave|TU_API_KEY_AQUI|X{8,})$''',
]
```

### F-006 | gitleaks-action incompatible ubuntu-26
**Fix en validate-pipeline.yml:**
```yaml
- name: Install gitleaks
  run: |
    ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH="x64" || ARCH="arm64"
    if [ "$ARCH" = "x64" ]; then
      SHA="551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
    else
      SHA="e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080"
    fi
    curl -sL "https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_${ARCH}.tar.gz" -o gl.tar.gz
    echo "$SHA  gl.tar.gz" | sha256sum -c --strict -
    tar -xzf gl.tar.gz gitleaks
    chmod +x gitleaks && sudo mv gitleaks /usr/local/bin/

- name: Scan secrets with gitleaks (full history)
  run: gitleaks git . --config .gitleaks.toml --redact --verbose --no-banner --exit-code 1
```

### F-007 | ${{ secrets.X }} interpolado en run: (injection risk)
**Fix:**
```yaml
- name: Check secrets configured
  env:
    _SECRET_VAR: ${{ secrets.MY_SECRET }}
  run: |
    if [ -z "$_SECRET_VAR" ]; then echo "⚠️ no configurado"; fi
```

### F-008 | Versión de paquete inexistente en PyPI
**Fix:**
```bash
pip index versions <paquete>  # listar versiones disponibles
# Actualizar requirements.txt con versión real
```

### F-009 | Cookies de sesión versionadas en git (archivo actual)
**Fix:**
```bash
git rm --cached <archivo_cookies>
echo "*cookies*.json" >> .gitignore
echo "**/cookies*.json" >> .gitignore
git commit -m "security: remove session cookies from tracking"
```

### F-010 | Playwright MCP recordings en git
**Fix:**
```bash
git rm -r --cached .playwright-mcp/
echo ".playwright-mcp/" >> .gitignore
git commit -m "security: remove playwright recordings from tracking"
```

### F-011 | Secret en HISTORIAL de git (CRÍTICO)
**Fix — purgar del historial:**
```bash
# Instalar git-filter-repo si no está
pip install git-filter-repo

# Eliminar archivo del historial completo
git filter-repo --path <archivo_con_secret> --invert-paths --force

# Re-añadir remote (filter-repo lo elimina)
git remote add origin https://github.com/<owner>/<repo>.git

# Force push (necesario porque reescribe historia)
git push --force origin master
```
**⚠️ Avisar al operador:** force-push invalida los clones locales de colaboradores.
**⚠️ Revocar el secret comprometido** aunque se elimine del historial.

### F-012 | Allowlist de commits históricos en gitleaks
**Fix alternativo a filter-repo (cuando no se puede force-push):**
```toml
# Añadir a .gitleaks.toml:
[[allowlists]]
description = "Commits históricos con credenciales ya removidas"
commits = [
  "hash_completo_del_commit",
]
```
**Preferir F-011 (filter-repo)** cuando sea posible — elimina el dato real.
**Usar F-012** solo cuando filter-repo no es viable (repo con muchos forks, CI-only, etc.).

---

## FASE 5 — DOCUMENTAR EN KB (siempre al resolver)

Formato obligatorio para nueva incidencia en `ai_workspace/knowledge_base/github_kb.md`:

```markdown
## INC-{YYYYMMDD}-{NNN} | {TIPO} | {SEVERIDAD}

**Fecha:** {fecha}
**Repositorio:** {owner/repo}
**Firma del error:** `{mensaje normalizado sin hashes ni fechas variables}`
**Causa raíz:** {explicación técnica}
**Fix aplicado:** F-{NNN} — {descripción del fix}
**Resultado:** ✅ RESUELTO | ⚠️ WORKAROUND | ❌ BLOQUEADO
**Tiempo total:** {N} min
**Veces visto:** {N}
**Tags:** [{TIPO}, {subtipo}, {herramienta}]
**Notas:** {contexto adicional, comandos exactos usados, advertencias}
```

**Actualizar también** la tabla de Fixes Reutilizables:
- Si es fix nuevo → añadir fila F-{NNN}
- Si es fix conocido → incrementar `Veces visto`

---

## FASE 6 — VERIFICACIÓN POST-FIX

```
1. Trigger manual del workflow en GitHub Actions (workflow_dispatch)
2. Esperar resultado (máx 5 min para Validate GEM OS Pipeline)
3. Si VERDE ✅ → documentar resolución en KB + cerrar ciclo
4. Si ROJO ❌ → volver a FASE 2 con nueva información
5. Si NUEVO error diferente → abrir nuevo ciclo desde FASE 0
```

**Trigger manual via REST:**
```powershell
Invoke-RestMethod "https://api.github.com/repos/$REPO/actions/workflows/validate-pipeline.yml/dispatches" `
  -Method POST -Body '{"ref":"master"}' `
  -Headers @{Authorization="Bearer $TOKEN"; "Content-Type"="application/json"; "X-GitHub-Api-Version"="2022-11-28"}
```

---

## REGLAS DEL AGENTE

1. **Nunca asumir** — siempre verificar con logs reales antes de aplicar fix
2. **Nunca forzar sin confirmar** — force-push y filter-repo requieren confirmación del operador
3. **Siempre documentar** — cada problema resuelto va a la KB, sin excepción
4. **Priorizar seguridad** — secrets CRÍTICO > CI bloqueado ALTO > PRs MEDIO
5. **Mínimo 2 veces visto** para considerar patrón "conocido" y resolver automáticamente
6. **Revocar siempre** — si un secret estuvo expuesto, avisar al operador para revocarlo
7. **No escalar sin intentar** — consultar KB antes de pedir intervención humana

---

## ESTADO ACTUAL DEL REPOSITORIO (actualizado 2026-11-08)

| Problema | Estado | Fix |
|----------|--------|-----|
| `google_credentials.json` en historial | ✅ RESUELTO | filter-repo (F-011) |
| `skool_cookies.json` JWT en historial | 🔴 PENDIENTE | filter-repo (F-011) — commit `4cc65c15` |
| gitleaks CI scanner | ✅ Operativo | F-006 (binario estático v8.30.1) |
| F-007 en auto-sync.yml | ✅ RESUELTO | env: isolation |
| .gitignore para cookies/playwright | ✅ Completo | F-009 + F-010 |

**Acción pendiente del operador:**
```bash
git filter-repo --path ai_workspace/scripts/skool_cookies.json --invert-paths --force
git remote add origin https://github.com/pabloalanzahlut/dropshipping-intelligence-suite.git
git push --force origin master
```

---

## Requisitos de GitHub para el ciclo autónomo (v3.1)

| Requisito | Dónde | Sin él |
|-----------|-------|--------|
| "Allow GitHub Actions to create and approve pull requests" | Settings → Actions → General | El agente empuja la rama `selfheal/*` y abre un Issue "Self-heal no puede abrir PRs" |
| Secreto `SELF_HEAL_TOKEN` (PAT con scope `workflow`) — opcional | Settings → Secrets → Actions | Los fixes que tocan `.github/workflows/` (F-004, F-007) se entregan como Issue con parche; el `GITHUB_TOKEN` no puede modificar workflows |

Acciones automáticas cableadas en `resolver()`: allowlist gitleaks (F-005/F-012), `pin_version_existente` (F-008), `secrets_a_env` (F-007), `bump_actions` (F-004), `untrack_archivo` (F-009/F-010), `cerrar_dependabot_obsoleto` (F-002).
Prueba controlada: Actions → Self-Heal GEM OS → Run workflow → campo `log_simulado` con un log de fallo.
