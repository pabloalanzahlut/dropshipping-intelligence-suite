# Changelog — GEM OS • Dropshipping Intelligence Suite

Todas las versiones notables del proyecto se documentan en este archivo.
El formato sigue [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
y el versionado [SemVer](https://semver.org/).

---

## [1.1.0] — 2026-10-25 (Fase 6C y 6D)

### Añadido
- **Fase 6C — Configuración YouTube Channels:**
  - `data/youtube_channels.json` como **única fuente de verdad** con los 5 mentores y URLs reales.
  - Validación de formato de URL al cargar en `provider_monitor_engine.py`
    (soporta `@handle`, `/channel/UC...`, `/c/...`, `/user/...`) y normalización canónica.
  - Sincronización de `queue_state.json` con los mismos canales.
- **Fase 6D — Backups + Versionado:**
  - `app/services/kb_backup.py::backup_json_file()` para respaldar JSON de configuración
    (`youtube_channels.json`, `queue_state.json`) con checksum SHA-256 e inventario.
  - `app/services/kb_backup.py::run_config_backup()`: backup combinado DB + JSON.
  - `scripts/backup_cron.py`: script programable para Task Scheduler / cron con verificación
    de integridad y poda de retención.
  - `scripts/make_release.py`: publicación de GitHub Releases con notas del CHANGELOG
    y adjunto del ejecutable compilado.
  - `CHANGELOG.md` con historial de versiones.

### Cambiado
- Normalización y validación de URLs de canal en el motor de ingesta.

### Corregido
- `data/youtube_channels.json` no existía como fuente de verdad runtime; se creó
  conforme a `PathManager.get_paths()['config']`.

---

## [1.0.0] — 2026-10-01 (Fases 0-5)

### Añadido
- Pipeline YouTube → Transcripción → KB con `ProviderMonitorEngine`.
- Validador financiero (Regla 3x de Adrián Sáenz, margen ≥70%, peso <1.2kg).
- Redactor de copys AIDA y generador de guiones TikTok.
- Dashboard FastAPI en `app/services/dashboard_server.py`.
- Control de Gobernanza v2.0 y panel de Ollama.
- Sistema de temas Dark/Light.
- `build_exe.py` para distribución PyInstaller.

### Seguridad
- User-Agent rotation, throttle (10 videos/hora), exponential backoff con jitter.
