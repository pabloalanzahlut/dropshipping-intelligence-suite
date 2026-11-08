# /resolver-github

Lee `ai_workspace/skills/resolver_github/procedimiento.md` y diagnostica/resuelve problemas GitHub (CI, PRs, Dependabot, secretos). Auto-documenta soluciones en KB.

## Conectores a activar automáticamente
- **Google Drive** (`mcp__73e33a54`): buscar documentación previa sobre el problema con `search_files` — puede haber soluciones ya documentadas
- **Gmail** (`mcp__ae68f902`): si el problema llegó por email (notificación de GitHub Actions, Dependabot alert), buscar el email original con `search_threads` para contexto completo

## Skills Claude a cargar
- `artifact-design` → si se genera un diagrama de flujo del pipeline CI/CD o del árbol de decisión de resolución
- `anthropic-skills:gem-qa-validation` → para validar que la solución no rompe otros tests

## Flujo automático
1. Identificar tipo de problema: CI_FAIL | PR_BLOQUEADO | DEPENDABOT | SECRETO_EXPUESTO | MERGE_CONFLICT
2. Consultar `ai_workspace/knowledge_base/github_kb.md` — puede haber solución previa documentada
3. Diagnosticar con comandos git/gh apropiados
4. Aplicar solución
5. Documentar en `ai_workspace/knowledge_base/github_kb.md` con formato: `## [FECHA] [TIPO] — [RESUMEN]`

## Regla de seguridad (CLAUDE.md §SEGURIDAD)
Si se detecta secreto expuesto en git history → DETENER → notificar al operador antes de cualquier push.
Nunca hacer `--no-verify` ni `--force` sin confirmación explícita del usuario.
