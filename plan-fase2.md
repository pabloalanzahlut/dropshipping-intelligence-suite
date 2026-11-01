# Plan de Implementación: 3 Mejoras Estratégicas para GEM OS

## 1. Configuración de Canales de Monitoreo (YouTube Monitor)

### Problema
- `youtube_channels.json` solo contiene un canal placeholder genérico
- `queue_state.json` tiene URLs placeholder (`https://youtube.com`) para los 5 mentores
- `provider_monitor_engine.py` tiene un diccionario `favorite_channels` hardcodeado con URLs placeholder y nombres incorrectos (Sebastián Esqueda, Bruno Sanders en vez de los mentores reales)
- No hay sincronización entre estos 3 archivos → inconsistencia de datos

### Solución
- Unificar la fuente de verdad en `youtube_channels.json` con los 5 mentores reales y sus URLs verdaderas
- Actualizar `queue_state.json` para reflejar los mismos canales con URLs reales
- Refactorizar `provider_monitor_engine.py` para leer canales desde `youtube_channels.json` en lugar de tenerlos hardcodeados
- Agregar validación de formato de URL al cargar

### Archivos a modificar
- `youtube_channels.json`
- `queue_state.json`
- `app/services/provider_monitor_engine.py`

---

## 2. Distribución del Software (`build_exe.py`)

### Problema
- El script `build_exe.py` actual es básico: no incluye la base de datos SQLite por defecto, no copia el `.env`, no incluye `ai_workspace/`, ni las carpetas de recursos UI
- No maneja la creación de estructura de directorios post-instalación
- No tiene soporte para `--onefile` (ejecutable único)

### Solución
- Mejorar `build_exe.py` para que:
  - Incluya `app/database/dropshipping_suite.db` (base de datos semilla)
  - Incluya `.env.example` (renombrándolo a `.env` en destino)
  - Incluya toda la carpeta `ai_workspace/` con sus subcarpetas
  - Incluya `app/ui/resources/` si existe
  - Genere un ejecutable en modo `--onefile` para distribución simple
  - Cree las carpetas necesarias en el directorio de salida
  - Agregue logging detallado del proceso

### Archivos a modificar
- `build_exe.py`

---

## 3. Optimización de Prompts AI para Copys y Guiones (Fases 3 y 4)

### Problema
- `copywriting_engine.py` genera copys mock sin usar OpenRouter (solo templates estáticos)
- `tiktok_script_generator.py` genera guiones mock sin usar OpenRouter (hooks hardcodeados, cuerpos genéricos)
- `prompt_curator.py` tiene la URL de OpenRouter incorrecta (`https://openrouter.ai` en vez de `https://openrouter.ai/api/v1/chat/completions`)
- `openrouter_client.py` (TranscriptionCleaner) funciona bien pero no es usado por los generadores de copy/guiones
- No hay inyección de contexto de KB (matriz_tendencias, fórmulas_conversion, operaciones_trafico) en los prompts de generación

### Solución
- Refactorizar `copywriting_engine.py` para que tenga un método `generar_con_openrouter()` que:
  - Construya un prompt AIDA con contexto de KB (últimas transcripciones + archivos de contexto)
  - Inyecte las reglas de negocio (Regla 3x, margen ≥70%, peso <1.2kg)
  - Use el cliente OpenRouter correctamente
  - Valide que la respuesta no contenga superlativos prohibidos
- Refactorizar `tiktok_script_generator.py` para que tenga un método `generar_con_openrouter()` que:
  - Construya un prompt para guiones TikTok con hooks virales
  - Inyecte contexto de KB y restricciones anti-baneo
  - Use el cliente OpenRouter correctamente
- Corregir `prompt_curator.py`: URL de API y modelo por defecto
- Agregar carga de archivos de contexto (`matriz_tendencias.md`, `formulas_conversion.md`, `operaciones_trafico.md`) en ambos generadores

### Archivos a modificar
- `app/services/copywriting_engine.py`
- `app/services/tiktok_script_generator.py`
- `app/services/prompt_curator.py`

---

## Notas y Consideraciones

- **Backwards Compatibility**: Los métodos mock existentes se conservan como fallback cuando no hay API key
- **Idempotencia**: La generación con IA solo ocurre cuando hay OPENROUTER_API_KEY configurada
- **Contexto fresco**: Se priorizan las últimas 5 transcripciones de la KB como contexto
- **Validación post-generación**: Los superlativos se filtran automáticamente en la respuesta de la IA
- **Sin dependencias nuevas**: Todo se implementa con `requests` y `os` ya existentes en requirements.txt