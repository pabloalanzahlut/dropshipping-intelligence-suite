# Changelog — GEM OS • Dropshipping Intelligence Suite

Todas las versiones notables del proyecto se documentan en este archivo.
El formato sigue [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
y el versionado [SemVer](https://semver.org/).

---

## [Sin versionar] — 2026-11-08 (Auditoría de transcripciones)

### Corregido
- **Escritorio:** `main.py` llamaba a `self.after()` (no existe) y solo abría el Dashboard; los
  paneles nacían fuera de su frame y no se ocultaban al cambiar de pestaña; `COLORS` no estaba
  importado; el botón global «Sincronizar» no hacía nada si Ingesta no se había abierto y su
  indicador nunca volvía a «Inactivo»; el Validador fallaba por un color `rgba` que Tk no admite.
- **Descarga:** `youtube_rss_fetcher` no resolvía canales por `@handle` (YouTube cambió
  `channelId` → `externalId`) ni bajaba subtítulos automáticos en español. Ahora RSS con
  respaldo `yt-dlp --flat-playlist` y `--sub-langs "es.*"`, con inglés como segunda opción.
- **Limpiador:** ya no borra palabras con significado («no», «este», «bueno», «mira»…) —
  invertían frases («no funciona» → «funciona»— ni ejemplos de copy («oferta limitada»). Solo
  quita disfluencias, etiquetas de sonido y relleno del canal.
- **Monitor:** guardaba solo 5000 caracteres del original; releía todos los vídeos en cada
  sincronización; leía `youtube_channels.json` del directorio actual y creaba un canal de
  ejemplo; sincronizaba 5 canales de 29; un error dejaba el panel en «Sincronizando…».
- **Web:** errores de la API rompían la tabla; búsqueda sin escapar `%`/`_`; `limite` sin tope;
  `/api/process` permitía ingestas en paralelo; modales descolocados (Alpine borraba el
  `display:flex` en línea).

### Añadido
- `app/services/transcript_store.py`: lectura/escritura compartida por escritorio y web.
- Escritorio: pestaña **Transcripciones** (buscar, leer limpio/original, copiar, exportar `.md`,
  pegar URL o texto, borrar) y botón **Cancelar** en la sincronización.
- Web: ingesta por URL/texto, borrado, exportación `.md`, sincronización de canales con
  progreso y cancelación, paginación («Cargar más»).
- **Filtro de tema** (`app/services/topic_filter.py`, clave `"filtro_tema": true` en
  `youtube_channels.json`): de Adrián Sáenz solo se registran vídeos de ecommerce, dropshipping y
  Shopify; los canales complementarios no se filtran. Se aplica en transcripciones y en la
  ingesta KB; los descartados se recuerdan en `data/videos_descartados.json`.
- Espera y reintento ante HTTP 429 de YouTube (60 s, 3 min, 7 min) y pausas de 6–14 s entre
  descargas; si sigue limitado, la sincronización se detiene sin perder lo guardado.
- `tests/test_transcripciones.py` (29 pruebas, sin red).

- **Agente IA con enrutado automático** (`app/services/agent_router.py`): reconoce el tipo de
  pregunta (producto, estrategia, operaciones, métricas, lecciones, validación financiera,
  técnica) y elige `gem-orchestrator-core` / `gem-qa-validation` / `gem-backend-core`; la web
  muestra el agente detectado mientras se escribe y permite fijarlo a mano. El selector mostraba
  modelos que no se usaban: ahora lee el modelo real de `/api/kb/agentes`.
- Insights KB: totales reales (270), búsqueda, filtro por canal y por tipo, paginación y el
  nombre del producto como título. Antes se omitían en silencio las 90 fórmulas de conversión y
  las 90 notas de operaciones (la consulta pedía una columna inexistente), también al agente.
- Validador web: campo **Envío** (coste landed), margen neto, fees 4,0 % + cancelaciones 10,1 %,
  PVP mínimo/objetivo y advertencias, como pide la regla de Adrián Sáenz.
- Sincronización: lote máximo de 15 descargas y enfriamiento de 45 min tras un 429 de YouTube.
- Escritorio con la paleta de la web (`design_tokens.py`); los estilos premium ya no los
  pisa `BaseTheme.apply()`.

### Añadido (3ª ronda: herramienta final)
- **Productos** (`/productos`, `product_catalog.py`): catálogo con el recorrido de CLAUDE.md
  (candidato → clasificado → refutado → validado → creativo → tienda → escalado | descartado).
  Cada paso comprueba datos reales y no se puede saltar ninguno: clasificación HOT/WARM/COLD por
  multiplicador sobre coste landed, las 8 refutaciones del skill (con su veredicto), el validador
  financiero, test de demanda + creativo confirmado, y el árbol de escalado con métricas reales.
  Todo con `correlation_id` y registro de eventos.
- **Negocio** (`/negocio`, `business_metrics.py`): ROAS real, CPA, resultado, margen neto (fees 4,0 %
  y devoluciones 10,1 %), caja y días de caja, y decisión de escalado, con los umbrales literales de
  los procedimientos `monitorear_flujo_caja` y `escalar_campana`. Panel de integraciones (solo
  indica si están configuradas; nunca muestra las claves).
- **Historial** (`/historial`) con exportación a **CSV** (UTF-8 con BOM; neutraliza fórmulas).
- **Registros** (`/registros`): servidor, ingesta en vivo y log estructurado; el servidor escribe
  `logs/elite/servidor.log` (rotativo).
- **Contraseña opcional** (`GEM_OS_PASSWORD`): sesión por cookie firmada, bloqueo tras 5 fallos,
  webhooks y estáticos exentos. Aviso en el log si se publica en red sin contraseña.
- Avisos (toasts) y atajos de teclado (`g` + letra, `/`, `?`); menú dirigido por datos.
- Escritorio: el Dashboard muestra canales, insights y estado como la web; la barra lateral marca
  la pestaña activa. Corregido el contenedor de sección que nunca se colocaba (el Dashboard salía
  vacío bajo los KPI).
- `build_exe.py` incluye plantillas y estáticos de la web y los módulos nuevos.
- Reglas falsas retiradas también de los comandos `/validar-financiero`, `/pipeline-completo`,
  `/importar-masivo` y del skill de ficha Shopify.
- `tests/test_negocio.py` y `tests/test_acceso.py`.

### Corregido (aprobado por el usuario)
- `validator_rules.py::_check_business_rules` exigía en `agent.md` «Margen 70%» y «Peso 1.2 kg»
  (reglas que el curso no fija y que ya no están en `agent.md`): el pre-flight fallaba siempre y
  bloqueaba a todos los agentes, incluida la página Agente IA. Ahora exige las reglas reales:
  mínimo 2×, objetivo 3×, ROAS, AIDA y superlativos.

### Corregido (2ª ronda)
- Dashboard web: el panel «Últimos Insights» salía vacío (claves duplicadas en Alpine) y todas
  las páginas lanzaban `Cannot read properties of undefined (reading 'after')`.
- Canales con URL incorrecta: Iván Caicedo → `@soyivancaicedo`, Vic Ecomilions → `@ecomilions`.
- TikTok: la duración vuelve a 15–30 s (regla del Media Buyer en `CLAUDE.md`).
- `/youtube` listaba 5 de 29 canales.
- `elite_logger.py` no compilaba (IndentationError desde el commit inicial).

### Cambiado
- `website/gem-os/index.html`: de página de venta a página interna de uso personal (sin
  precios, testimonios ni cifras); reglas financieras corregidas según `CLAUDE.md`.
- El servidor escucha en `127.0.0.1` por defecto (`GEM_OS_HOST=0.0.0.0` para publicarlo).
- Las filas de `video_sources` creadas al guardar transcripciones llevan
  `platform='youtube_transcript'` y la ingesta de IA no las da por procesadas.
- Se eliminaron 2 transcripciones simuladas de la BD (copia en `backups/`).

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
