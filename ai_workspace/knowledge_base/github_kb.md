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
| F-007 | SECRETS_SECURITY/INJECTION_RISK | secrets interpolados en run: | Mover a env: del step | 1 |
| F-008 | DEPENDABOT/VERSION_NONEXISTENT | no matching distribution found | Verificar con pip index versions | 1 |

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
