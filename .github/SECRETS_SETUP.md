# Configuración de Secrets en GitHub

Para que los workflows de GEM OS funcionen correctamente, configura estos secrets en:
**GitHub → Settings → Secrets and variables → Actions → New repository secret**

## Secrets requeridos

| Secret | Descripción | Dónde obtenerlo |
|--------|-------------|-----------------|
| `MAKE_WEBHOOK_TIKTOK` | URL webhook de Make.com para auto-publicar TikTok | Make.com → tu escenario → webhook URL |
| `OPENROUTER_API_KEY` | API key de OpenRouter para fichas masivas | openrouter.ai → Keys |
| `REMOVEBG_API_KEY` | API key de remove.bg para imágenes sin fondo | remove.bg → API |

## Cómo configurarlos

1. Ve a: `https://github.com/pabloalanzahlut/dropshipping-intelligence-suite/settings/secrets/actions`
2. Clic en **"New repository secret"**
3. Pega el nombre exacto (ej: `MAKE_WEBHOOK_TIKTOK`) y el valor
4. Clic en **"Add secret"**

## Verificar que están configurados

Una vez configurados, el workflow `auto-sync.yml` mostrará `✅` al ejecutarse.
Para ejecutarlo manualmente: Actions → Auto Sync GEM OS → Run workflow
