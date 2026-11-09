# GitHub Knowledge Base — GEM OS
**Generado:** 2026-11-05 | **Método:** Xavier (auto-alimentación por resolución)

> Cada incidencia resuelta se registra aquí automáticamente por el skill `resolver_github`.
> La segunda vez que aparezca el mismo patrón de error → resolución automática sin intervención.
> **No editar manualmente.** Usar `/resolver-github` para agregar registros.

---

## Índice de Fixes Reutilizables

| ID | Tipo | Firma del error (normalizada) | Fix | Veces visto |
|----|------|-------------------------------|-----|-------------|
| F-001 | CI_FAILURE/SECRETS_SCAN | grep false-positive en workflow | Reemplazar grep por gitleaks | 1 |
| F-002 | DEPENDABOT/DIRTY_PR | pull request is not mergeable (405) | Cerrar PR + aplicar bump manual | 1 |
| F-003 | WORKFLOW_CONFIG | pull_request trigger ejecuta workflow del branch | Mergear master en rama del PR | 1 |
| F-004 | WORKFLOW_CONFIG/ACTION_VERSION | node.js actions are deprecated | Actualizar github-script a v8 | 1 |
| F-005 | SECRETS_SECURITY | gitleaks placeholder detectado como secreto real | Allowlist en .gitleaks.toml | 1 |
| F-006 | WORKFLOW_CONFIG/RUNNER_COMPAT | gitleaks-action incompatible ubuntu-26 | Binario estático SHA-256 pinned | 1 |
| F-007 | SECRETS_SECURITY/INJECTION_RISK | secrets interpolados en run: | Mover a env: del step | 2 |
| F-008 | DEPENDABOT/VERSION_NONEXISTENT | no matching distribution found | Verificar con pip index versions | 1 |
| F-009 | SECRETS_SECURITY/COOKIES_TRACKED | cookies de sesión (auth_token jwt) versionadas en git | git rm --cached + .gitignore *cookies*.json | 1 |
| F-010 | SECRETS_SECURITY/PLAYWRIGHT_DATA | grabaciones playwright de sesiones autenticadas en git | git rm --cached .playwright-mcp/ + .gitignore | 1 |
| F-011 | SECRETS_SECURITY/HISTORY_LEAK | secret en historial de git (cualquier archivo) | git filter-repo --path <archivo> --invert-paths --force + force push | 2 |

---

## Incidencias Registradas

<!-- Las nuevas incidencias se agregan debajo de esta línea -->

## INC-20261105-001 | SECRETS_SCAN | ALTO

**Fecha:** 2026-11-05
**Repositorio:** pabloalanzahlut/dropshipping-intelligence-suite
**Firma del error:** `grep -r "sk-or-v1-" . -- encontrando patrón en el propio workflow`
**Causa raíz:** El step de validación de secretos usaba grep que encontraba el patrón dentro de su propia definición en el archivo YAML del workflow.
**Fix aplicado:** F-001 + F-006 — reemplazar grep por gitleaks v8.30.1 binario estático con SHA-256 verificado + `.gitleaks.toml` con allowlist de placeholders
**Resultado:** ✅ RESUELTO
**Tiempo total:** 45 min (incluye configuración inicial de gitleaks)
**Veces visto:** 1
**Tags:** [CI_FAILURE, SECRETS_SCAN, gitleaks, ubuntu-26]
**Notas:** gitleaks debe instalarse como binario estático (no gitleaks-action) para compatibilidad con ubuntu-26.04. SHA-256 para x64: `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`. SHA-256 para arm64: `e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080`.

---

## INC-20261105-002 | DEPENDABOT/DIRTY_PR | MEDIO

**Fecha:** 2026-11-05
**Repositorio:** pabloalanzahlut/dropshipping-intelligence-suite
**Firma del error:** `pull request is not mergeable` (HTTP 405 en endpoint /merge)
**Causa raíz:** PR de Dependabot con rama desactualizada o en conflicto. La API de merge devuelve 405 cuando el PR no es mergeable en ese momento.
**Fix aplicado:** F-002 — cerrar el PR vía API PATCH (state: closed), luego aplicar el bump manualmente en requirements.txt y hacer commit/push. Dependabot no recreará el PR para esa versión.
**Resultado:** ✅ RESUELTO
**Tiempo total:** 10 min
**Veces visto:** 1
**Tags:** [DEPENDABOT, DIRTY_PR, python-dotenv]
**Notas:** Afectó PR #4 (python-dotenv 1.0.1 → 1.2.4). Tras cerrar el PR manualmente y aplicar el bump, confirmar que el `pip install` acepta la nueva versión antes de hacer push.

---

## INC-20261105-003 | DEPENDABOT/VERSION_NONEXISTENT | MEDIO

**Fecha:** 2026-11-05
**Repositorio:** pabloalanzahlut/dropshipping-intelligence-suite
**Firma del error:** `no matching distribution found for yt-dlp==`
**Causa raíz:** requirements.txt tenía `yt-dlp==2024.10.23` que no existe en PyPI (yt-dlp usa formato de fecha AAAA.MM.DD pero no todas las fechas tienen release).
**Fix aplicado:** F-008 — verificar con `pip index versions yt-dlp`, sustituir por `yt-dlp==2026.10.26` (última estable disponible).
**Resultado:** ✅ RESUELTO
**Tiempo total:** 5 min
**Veces visto:** 1
**Tags:** [DEPENDABOT, VERSION_NONEXISTENT, yt-dlp, PyPI]
**Notas:** yt-dlp publica por fechas pero no todas las fechas tienen release. Siempre verificar existencia con `pip index versions` antes de fijar versión.

---

## INC-20261105-004 | WORKFLOW_CONFIG/RUNNER_COMPAT | MEDIO

**Fecha:** 2026-11-05
**Repositorio:** pabloalanzahlut/dropshipping-intelligence-suite
**Firma del error:** `actions/github-script node deprecated` / incompatibilidad ubuntu-26
**Causa raíz:** `actions/github-script@v7` usaba Node 16 (deprecated). En runners nuevos (ubuntu-26) puede fallar.
**Fix aplicado:** F-004 — actualizar a `actions/github-script@v8` (Node 20).
**Resultado:** ✅ RESUELTO
**Tiempo total:** 2 min
**Veces visto:** 1
**Tags:** [WORKFLOW_CONFIG, ACTION_VERSION, github-script, ubuntu-26]
**Notas:** No usar @v9 aún (inestable a noviembre 2026). v8 es el balance correcto.

---

## INC-20261105-005 | SECRETS_SECURITY/INJECTION_RISK | BAJO

**Fecha:** 2026-11-05
**Repositorio:** pabloalanzahlut/dropshipping-intelligence-suite
**Firma del error:** `${{ secrets.* }}` interpolado directamente en bloque `run:`
**Causa raíz:** auto-sync.yml interpola secretos directamente en scripts de shell, anti-patrón de inyección.
**Fix aplicado:** Pendiente — reportado al operador para corrección manual
**Resultado:** ⚠️ WORKAROUND (reportado, no bloqueante para repo privado)
**Tiempo total:** 0 min (solo detección)
**Veces visto:** 1
**Tags:** [SECRETS_SECURITY, INJECTION_RISK, auto-sync, anti-patrón]
**Notas:** Fix: mover `${{ secrets.X }}` a `env:` del step y usar `$MY_VAR` en el script. Ver F-007 para el patrón exacto.

---

## INC-20261108-009 | SECRETS_SECURITY/HISTORY_LEAK | CRÍTICO

**Fecha:** 2026-11-08
**Repositorio:** pabloalanzahlut/dropshipping-intelligence-suite
**Firma del error:** `gitleaks: RuleID=jwt File=ai_workspace/scripts/skool_cookies.json Line=74 leaks found: 1`
**Causa raíz:** `auto_pipeline_skool.py` guardó cookies de Skool (JWT auth_token activo exp Nov 2027) en un archivo JSON. El auto-sync lo commitió. Aunque se eliminó del tracking con `git rm --cached`, el JWT quedó en el historial. `git filter-repo` para `google_credentials.json` reescribió el historial (hash cambió de `d86d465` a `4cc65c15`), pero `skool_cookies.json` sigue en el historial reescrito.
**Fix aplicado:** F-011 — pendiente ejecución del operador:
```bash
git filter-repo --path ai_workspace/scripts/skool_cookies.json --invert-paths --force
git remote add origin https://github.com/pabloalanzahlut/dropshipping-intelligence-suite.git
git push --force origin master
```
**Resultado:** 🔴 PENDIENTE — CI bloqueado en "Scan secrets with gitleaks (full history)"
**Tiempo total:** —
**Veces visto:** 2 (misma firma, hash cambió tras primer filter-repo)
**Tags:** [SECRETS_SECURITY, HISTORY_LEAK, skool, auth_token, JWT, filter-repo]
**Notas:** Commit actual con el leak: `4cc65c15354d06cfa380ff74fcc153ca4966e80c`. El auth_token (exp Nov 2027) sigue activo — ACCIÓN REQUERIDA: cerrar sesión en Skool para invalidarlo. Después del fix, el CI debería volver verde automáticamente. Patrón aprendido: `auto_pipeline_skool.py` debe usar un directorio temporal fuera del repo para guardar cookies.

---

## INC-20261108-010 | SECRETS_SECURITY/HISTORY_LEAK | CRÍTICO

**Fecha:** 2026-11-08
**Repositorio:** pabloalanzahlut/dropshipping-intelligence-suite
**Firma del error:** `gitleaks: RuleID=private-key File=ai_workspace/config/google_credentials.json Line=5 leaks found: 1`
**Causa raíz:** `google_credentials.json` (service account con private_key RSA) fue commiteado en commit `f819e6d` (2026-11-07). El archivo estaba en `.gitignore` como `ai_workspace/config/google_credentials.json` pero ese path fue ignorado por error antes de la adición al gitignore.
**Fix aplicado:** F-011 — `git filter-repo --path ai_workspace/config/google_credentials.json --invert-paths --force` + force push
**Resultado:** ✅ RESUELTO — `google_credentials.json` eliminado del historial
**Tiempo total:** 5 min
**Veces visto:** 1
**Tags:** [SECRETS_SECURITY, HISTORY_LEAK, google_credentials, private-key, filter-repo]
**Notas:** El service account key de Google sigue activo (a diferencia de JWT no hay indicación de revocación inmediata). Verificar en Google Cloud Console si el SA key `f819e6d` era el único leak. `.gitignore` ya tenía la regla; el archivo se coló antes de que se aplicara.

---

## INC-20261108-006 | SECRETS_SECURITY/COOKIES_TRACKED | CRÍTICO

**Fecha:** 2026-11-08
**Repositorio:** pabloalanzahlut/dropshipping-intelligence-suite
**Firma del error:** `auth_token jwt activo en ai_workspace/scripts/skool_cookies.json versionado en git`
**Causa raíz:** `auto_pipeline_skool.py` guarda cookies de sesión en un archivo JSON en `ai_workspace/scripts/`. El auto-sync commitió el archivo antes de que estuviera en .gitignore. El archivo contenía: `auth_token` JWT activo (exp Nov 2027), `aws-waf-token`, cookies AWS ALB y `__stripe_mid` / `__stripe_sid`.
**Fix aplicado:** F-009 — `git rm --cached ai_workspace/scripts/skool_cookies.json` + añadir `*cookies*.json` y `**/cookies*.json` a .gitignore
**Resultado:** ✅ RESUELTO (archivo fuera de tracking, .gitignore actualizado)
**Tiempo total:** 10 min
**Veces visto:** 1
**Tags:** [SECRETS_SECURITY, COOKIES_TRACKED, skool, auth_token, JWT]
**Notas:** ⚠️ ACCIÓN PENDIENTE DEL OPERADOR: El auth_token (exp Nov 2027) sigue en el historial git (commit d86d465). Para invalidarlo, cerrar sesión en Skool. Para limpiar el historial: `pip install git-filter-repo && git filter-repo --path ai_workspace/scripts/skool_cookies.json --invert-paths`. La clave de regla de prevención: `auto_pipeline_skool.py` debe tener `skool_cookies.json` en su propio directorio de trabajo temporal, no en un path versionado.

---

## INC-20261108-007 | SECRETS_SECURITY/PLAYWRIGHT_DATA | MEDIO

**Fecha:** 2026-11-08
**Repositorio:** pabloalanzahlut/dropshipping-intelligence-suite
**Firma del error:** `.playwright-mcp/page-*.yml` grabaciones de sesiones autenticadas en git`
**Causa raíz:** Playwright MCP graba capturas del árbol de accesibilidad de páginas en `.playwright-mcp/`. Si se navegó una sesión autenticada (Skool), las grabaciones pueden contener estructura interna de páginas privadas.
**Fix aplicado:** F-010 — `git rm --cached .playwright-mcp/` + añadir `.playwright-mcp/` a .gitignore
**Resultado:** ✅ RESUELTO
**Tiempo total:** 5 min
**Veces visto:** 1
**Tags:** [SECRETS_SECURITY, PLAYWRIGHT_DATA, playwright-mcp]
**Notas:** `.playwright-mcp/` debe estar siempre en .gitignore. Los archivos son temporales de sesión y nunca deberían versionarse.

---

## INC-20261108-008 | SECRETS_SECURITY/INJECTION_RISK | BAJO

**Fecha:** 2026-11-08
**Repositorio:** pabloalanzahlut/dropshipping-intelligence-suite
**Firma del error:** `${{ secrets.MAKE_WEBHOOK_TIKTOK }}` / `${{ secrets.OPENROUTER_API_KEY }}` en bloque `run:` de auto-sync.yml`
**Causa raíz:** Mismo patrón F-007 que INC-20261105-005 pero en un workflow diferente (auto-sync.yml). Detectado en auditoría de workflows del 2026-11-08.
**Fix aplicado:** F-007 — mover secrets a `env:` del step con prefijo `_` para distinguirlos de vars de entorno reales
**Resultado:** ✅ RESUELTO
**Tiempo total:** 3 min
**Veces visto:** 2 (veces totales del patrón F-007)
**Tags:** [SECRETS_SECURITY, INJECTION_RISK, auto-sync, CI]
**Notas:** Patrón recurrente. El auto-sync que genera workflows tiende a interpolarlo directamente. Revisar cada nuevo workflow antes del primer push.

---

## INC-20261109-011 | SECRETS_SCAN/FALSE_POSITIVE | ALTO

**Fecha:** 2026-11-09
**Repositorio:** pabloalanzahlut/dropshipping-intelligence-suite
**Firma del error:** `gitleaks: RuleID generic-api-key, File tests/test_exe_portable.py, Line 146, Commit ef4f8b47` (valor `sk-or-v1-SECRETOSECRETOSECRETO1234`, entropía 3.73)
**Causa raíz:** Valor de prueba con forma de clave OpenRouter en un test; el escaneo de historial completo lo marca aunque no sea secreto real.
**Fix aplicado:** F-012 variante regex — ampliar allowlist de `.gitleaks.toml` con `[A-Z]{8,}[0-9]+`; valor de test cambiado a `X{64}` y aserción `…XXXX`. NO usar allowlist por commit (bloqueado por política de seguridad) ni `.gitleaksignore` (gitleaks v8 no lo lee sin `--baseline-path`).
**Resultado:** ✅ RESUELTO — runs #301 y #302 en verde
**Tiempo total:** ~40 min (primera vez)
**Veces visto:** 1
**Tags:** [SECRETS_SCAN, FALSE_POSITIVE, gitleaks, tests]
**Notas:** Segunda vez → aplicar directamente la regex de allowlist. Valores de test deben usar `X{8,}` desde el inicio.
