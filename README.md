# 🎯 GEM OS • Dropshipping Intelligence Suite

**Suite de inteligencia para dropshipping global en Shopify: validación financiera, selección de producto, copy, guiones de vídeo y monitorización, con app de escritorio, panel web y agentes autónomos.**
**Stack:** Python 3.11+ / FastAPI + panel web / Tkinter / SQLite / APScheduler / OpenRouter (Claude, DeepSeek, Gemini) / Higgsfield

> Herramienta de uso personal. Las reglas financieras vienen del curso de Adrián Sáenz y son inmutables (ver [`CLAUDE.md`](CLAUDE.md)).
> Las secciones marcadas `AUTO` de este README las regenera `scripts/sync_readme.py`; no se editan a mano.

---

## 🚀 Inicio Rápido

### Prerequisitos
- Python 3.11+
- pip (gestor de paquetes)
- Windows 10/11 (recomendado), macOS o Linux

### Instalación desde código fuente

1. **Clonar/descargar el proyecto**
```bash
cd h:\dropshipping_intelligence_suite
```

2. **Crear entorno virtual (recomendado)**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
# Copiar plantilla y editar
cp .env.example .env
# Editar .env con tus claves API
# Como mínimo: OPENROUTER_API_KEY=sk-or-v1-tu_clave
```

5. **Ejecutar la aplicación**
```bash
python app/main.py
```

### Abrir GEM OS en Windows (recomendado: doble clic)
- `scripts\windows\abrir_gem_os.bat` — abre el **escritorio** desde Python (sin consola y sin depender del
  `.exe`). Arranca por sí mismo el servidor web y todas las automatizaciones; si ya estaba abierto, no abre otro.
- `scripts\windows\abrir_web.bat` — solo el servidor web y el panel en el navegador.
- Arranque con Windows: `powershell -ExecutionPolicy Bypass -File scripts\windows\instalar_autoarranque.ps1 -Escritorio`
  (quitar con `-Quitar`; `-SoloMostrar` enseña qué haría sin instalar nada).
- Los errores de arranque quedan en `logs\elite\escritorio.err`.

### Ejecutable Windows (.exe)
```bash
python build_exe.py              # Modo carpeta (rápido)
python build_exe.py --onefile    # Ejecutable único portable
# Genera: dist/GEM_OS_Suite/GEM_OS_Suite.exe
```

**El .exe no lleva tus claves dentro** (ni `.env`, ni credenciales, ni cookies, ni bases de datos; el build
lo comprueba con `scripts/verificar_dist.py` y falla si encuentra alguno). Cómo usarlo con tus agentes:

1. Copia la carpeta `dist/GEM_OS_Suite/` donde quieras (es portable) y abre `GEM_OS_Suite.exe`.
2. Primer arranque → se abre **Configuración**: pega tu clave de OpenRouter y pulsa «Probar OpenRouter».
   Se guarda en `%APPDATA%\GEM_OS_Suite\.env` (también se lee un `.env` junto al `.exe`, si lo prefieres).
3. ¿Vienes del proyecto? Configuración → «Traer mis datos desde…» y elige la carpeta `data/` del proyecto
   (se comprueba la base de datos y se guarda copia de lo que hubiera).
4. El `.exe` arranca por sí mismo el servidor web: alertas, avisos, resumen diario, mantenimiento y
   sincronización funcionan mientras esté abierto, y **🌐 Abrir panel web** te lleva a la web.
5. Para que arranque con Windows: `powershell -ExecutionPolicy Bypass -File scripts\windows\instalar_autoarranque.ps1 -Exe "C:\ruta\GEM_OS_Suite.exe"`.

Datos, registros y copias del `.exe` viven en `%APPDATA%\GEM_OS_Suite\` (`GEM_OS_DATA_DIR` lo cambia).

---

## 🧰 Skills y comandos (Claude Code)

Se invocan con `/comando` o en lenguaje natural (auto-dispatch, ver [`CLAUDE.md`](CLAUDE.md)). Pipeline: producto → clasificar → refutar → validar financiero → creativo → tienda → escalado.

<!-- AUTO:skills -->
33 comandos disponibles:

| Comando | Función |
|---|---|
| `/amazon-dropshipping` | Lee ai_workspace/skills/amazon_dropshipping/procedimiento.md y configura el canal Amazon como complemento a Sh |
| `/autods-notas` | Genera notas profesionales en inglés para enviar a proveedores chinos a través de AutoDS |
| `/buscar-producto` | Descubre candidatos aplicando los 5 criterios de producto ganador |
| `/clasificar-producto` | model: sonnet |
| `/clonar-seccion` | model: haiku |
| `/configurar-tienda` | Lee ai_workspace/skills/configurar_tienda/procedimiento.md y guía al usuario por el checklist completo de conf |
| `/consolidar-manual` | Convierte toda la Knowledge Base en **un manual paso a paso**, no en una lista |
| `/consultar-kb` | Lee ai_workspace/skills/consultar_kb_agente/procedimiento.md y responde la consulta del operador basándose en  |
| `/destilar-skill` | Reescribe una skill a partir de lo que **realmente pasó**, no de lo que creíamos |
| `/escalar-campana` | model: sonnet |
| `/estructurar-landing` | model: haiku |
| `/fake-door` | Mide si un producto interesa **antes de comprar stock o gastar en ads** |
| `/generar-video-ia` | Genera un video de producto para TikTok Ads usando **Higgsfield AI** — sin filmar, sin equipo |
| `/gestionar-meta-ads` | Lee ai_workspace/skills/gestionar_meta_ads/procedimiento.md y genera naming de campañas + hooks s0–s3 estilo R |
| `/google-ads` | Lee ai_workspace/skills/google_ads/procedimiento.md y configura/optimiza campañas de Google Ads |
| `/hook-matrix` | model: haiku |
| `/importar-masivo` | Lee ai_workspace/skills/importar_masivo/procedimiento.md y procesa URLs de AliExpress/CJ/Temu → valida regla 3 |
| `/investigar-nicho` | Lee ai_workspace/skills/investigar_nicho/procedimiento.md y genera un informe de 10 ángulos de ataque para el  |
| `/matriz-precios` | model: sonnet |
| `/monitorear-caja` | model: sonnet |
| `/monitorear-skool` | Lee ai_workspace/skills/monitorear_skool/procedimiento.md |
| `/oferta-multiunidad` | Diseña la estructura de oferta que sube el ticket medio sin tocar el precio unitario |
| `/pipeline-completo` | Ejecuta el pipeline completo de GEM OS sobre una transcripción de video o datos de producto |
| `/recuperar-carrito` | Webhook Shopify → Make.com → email nocturno 20–23h para recuperación de carritos abandonados |
| `/redactar-anuncios-meta` | model: haiku |
| `/redactar-ficha-shopify` | model: haiku |
| `/redactar-guion` | model: haiku |
| `/refutar-producto` | model: sonnet |
| `/resolver-github` | Lee ai_workspace/skills/resolver_github/procedimiento.md y diagnostica/resuelve problemas GitHub (CI, PRs, Dep |
| `/tiktok-ads` | Lee ai_workspace/skills/tiktok_ads/procedimiento.md y configura/gestiona campañas de TikTok Ads pagados |
| `/tiktok-shop` | Lee ai_workspace/skills/tiktok_shop/procedimiento.md y configura/opera el canal TikTok Shop sin stock |
| `/trafico-organico` | Lee ai_workspace/skills/trafico_organico/procedimiento.md y ejecuta el flujo de contenido orgánico para TikTok |
| `/validar-financiero` | model: sonnet |
<!-- /AUTO:skills -->

---

## 🛡️ CI/CD, seguridad y agente GitHub autónomo

- **Validación** (`validate-pipeline.yml`): comprueba archivos obligatorios, que no haya `.env` versionado y ejecuta **gitleaks v8.30.1** (binario con SHA-256 fijado) sobre **todo el historial**. Corre en cada push/PR relevante y **a diario a las 06:17 UTC**.
- **Agente autónomo** (`self-heal.yml` + `scripts/github_self_heal.py`): cuando un CI falla, busca la firma en el catálogo `ai_workspace/config/github_fixes.json`; si hay fix automático abre una rama `selfheal/*`, la verifica con gitleaks y la fusiona; si la firma es nueva abre un Issue; **si detecta una fuga real de secreto abre un Issue crítico y no reescribe el historial** (hay que rotar la credencial). Cierra solo los PR de Dependabot obsoletos y registra cada incidente en [`github_kb.md`](ai_workspace/knowledge_base/github_kb.md).
- **README**: `sync_readme.py --check` falla el CI si estas secciones se desfasan; el agente las regenera.
- **Secretos**: `.env`, credenciales y cookies nunca se versionan (`.gitignore`); solo `.env.example`. Detalle en [`SECURITY.md`](SECURITY.md).

<!-- AUTO:workflows -->
| Workflow | Disparadores |
|---|---|
| Auto Label PRs (`auto-label.yml`) | pull_request |
| Auto Sync GEM OS (`auto-sync.yml`) | push, schedule, workflow_dispatch |
| Cleanup Stale Branches (`delete-stale-branches.yml`) | schedule, workflow_dispatch |
| Release GEM OS (`release.yml`) | push |
| Self-Heal GEM OS (`self-heal.yml`) | workflow_run, pull_request, schedule, workflow_dispatch |
| Setup Repository Labels (`setup-labels.yml`) | workflow_dispatch |
| Stale Issues & PRs (`stale.yml`) | schedule, workflow_dispatch |
| Validate GEM OS Pipeline (`validate-pipeline.yml`) | pull_request, push, schedule, workflow_dispatch |
<!-- /AUTO:workflows -->

---

## 📦 Dependencias fijadas

<!-- AUTO:deps -->
| Paquete | Versión fijada |
|---|---|
| requests | 2.34.2 |
| python-dotenv | 1.2.4 |
| pyinstaller | 6.22.3 |
| yt-dlp | 2026.10.26 |
| youtube-transcript-api | 0.6.2 |
| openai | 1.54.3 |
| fastapi | 0.162.0 |
| uvicorn | 0.54.0 |
| python-multipart | 0.0.33 |
| jinja2 | 3.1.6 |
| markdown | 3.11.3 |
| apscheduler | 3.11.3 |
<!-- /AUTO:deps -->

---

## 📋 Fases de Implementación

### ✅ FASE 0: Fundacional (COMPLETADA)
- [x] Tablas BD: `productos_validados`, `transcripciones_youtube`
- [x] Motor `FinancialValidator` (multiplicador 2x/3x sobre coste landed, fees y cancelaciones)
- [x] Variables de entorno configurables
- [x] Tests unitarios

**Tests:** `python cli_test.py`

---

### ✅ FASE 1: YouTube Monitor + Ultra-Limpieza de Transcripciones (COMPLETADA)
- [x] Servicio `YouTubeChannelMonitor`: descarga automática
- [x] Motor `TranscriptCleaner`: 6 funciones de limpieza agresiva
  - Eliminar muletillas ("ehh", "umm", "ok", "bueno", etc.)
  - Eliminar timestamps VTT/SRT
  - Detectar secciones por pausas
  - Normalizar párrafos
  - Validar UTF-8
  - Contar tokens (objetivo: -40 a -60% reducción)
- [x] Deduplicación por hash MD5
- [x] UI: Panel Monitor de YouTube
- [x] Background daemon (sincronización cada 2 horas)

**Duración:** 4 días | **Estado:** ✅ OPERACIONAL

---

### ✅ FASE 3: Copywriting AIDA Framework (COMPLETADA)
- [x] Motor `CopywrightingEngine`: genera copys sin superlativos
- [x] Framework AIDA: Attention, Interest, Decision, Action
- [x] Inyección de contexto KB limpia en prompts
- [x] Scoring automático A/I/D/A
- [x] Tabla `copys_generados` en BD
- [x] Validación de prohibición de adjetivos superlativos

**Adjetivos prohibidos:** "increíble", "alucinante", "fantástico", "asombroso", etc.

**Duración:** 4 días | **Estado:** ✅ OPERACIONAL

---

### ✅ FASE 4: Generador de Guiones TikTok (COMPLETADA)
- [x] Motor `TikTokScriptGenerator`: guiones con trending topics
- [x] Hook Patterns virales:
  - Story-telling: narrativa in medias res
  - Curiosity-gap: pregunta generadora
  - Shock: dato sorprendente
  - Humor: situación cómica
- [x] Inyección de contexto KB + análisis trending
- [x] Batch generation: 1 producto → 5 variantes
- [x] Tabla `guiones_tiktok` en BD
- [x] Estimación de duración (segundos)

**Duración:** 4 días | **Estado:** ✅ OPERACIONAL

---

### ✅ FASE 5: Validación Financiera + Dashboard (COMPLETADA)
- [x] UI: Panel Validador Financiero con importación CSV/JSON
- [x] Export CSV/JSON con flagging de productos no-validados
- [x] Batch processing con threading
- [x] Dashboard con KPIs principales
- [x] Preparación para empaquetamiento .exe

**Duración:** 3 días | **Estado:** ✅ OPERACIONAL

---

## 🏗️ Arquitectura

```
┌─────────────────────────────┐
│  CAPA PRESENTACIÓN (Tkinter) │
│  • Validador Financiero     │
│  • Monitor YouTube          │
│  • Ingesta Masiva (Legacy)  │
└─────────────────────────────┘
            ↓
┌─────────────────────────────┐
│  CAPA ORQUESTACIÓN (Services)│
│  • FinancialValidator       │
│  • YouTubeChannelMonitor    │
│  • TranscriptCleaner       │
│  • CopywrightingEngine      │
│  • TikTokScriptGenerator    │
└─────────────────────────────┘
            ↓
┌─────────────────────────────┐
│  CAPA PERSISTENCIA (SQLite)  │
│  • productos_validados      │
│  • transcripciones_youtube  │
│  • copys_generados          │
│  • guiones_tiktok           │
└─────────────────────────────┘
```

---

## 📊 Módulos Principales

### `app/services/financial_validator.py`
Validador financiero con reglas inmutables:
- **Multiplicador** (Adrián Sáenz): mínimo 2x (rechaza) y objetivo 3x (advierte), siempre sobre **coste landed** (producto + envío)
- **Coste de origen** recomendado: 5–15 USD (advierte fuera de rango)
- **Costes reales del P&L**: fees Shopify + divisa 4,0 % y cancelaciones/devoluciones 10,1 % de la facturación
- Sin umbral de margen % ni límite de peso: el curso no los fija

```python
from app.services.financial_validator import FinancialValidator

validator = FinancialValidator()
resultado = validator.validar_producto(
    sku="PROD-001",
    costo_origen=10.0,
    costo_envio=2.0,
    pvp_sugerido=36.0,
)
print(resultado)  # multiplicador sobre coste landed (12.0) y estado de validación
```

---

### `app/services/transcript_cleaner.py`
Ultra-limpieza de transcripciones para optimizar tokens OpenRouter:
- Elimina muletillas y filler words
- Elimina timestamps VTT/SRT
- Detecta secciones por pausas
- Normaliza párrafos
- Valida UTF-8
- Estima reducción de tokens

```python
from app.services.transcript_cleaner import TranscriptCleaner

cleaner = TranscriptCleaner()
resultado = cleaner.clean(transcripcion_raw)
print(f"Reducción: {resultado['reduccion_pct']}%")  # Típico: 40-60%
```

---

### `app/services/youtube_channel_monitor.py`
Monitor automático de canales YouTube:
- Descarga transcripciones VTT/SRT
- Deduplica por hash MD5
- Integra limpieza ultra
- Almacena en BD
- Sincronización en background (2 horas)

```python
from app.services.youtube_channel_monitor import YouTubeChannelMonitor

monitor = YouTubeChannelMonitor()
monitor.agregar_canal("https://www.youtube.com/@canal", "Nombre Canal")
stats = monitor.sincronizar_canales()
```

---

### `app/services/copywriting_engine.py`
Generador de copys AIDA sin superlativos:
- Framework AIDA estructura (Attention/Interest/Decision/Action)
- Prohibe adjetivos superlativos
- Inyecta contexto de KB limpia
- Calcula scores automáticos
- Almacena en BD

```python
from app.services.copywriting_engine import CopywrightingEngine

engine = CopywrightingEngine()
copy = engine.generar_copy_template(
    nombre_producto="Producto X",
    categoria="Electrónica",
    costo_origen=5.0,
    pvp=15.0,
    peso_kg=0.5
)
```

---

### `app/services/tiktok_script_generator.py`
Generador de guiones TikTok virales:
- 4 patrones de hooks: story-telling, curiosity-gap, shock, humor
- Inyecta contexto KB + trending topics
- Genera 5 variantes por producto
- Estima duración en segundos
- Almacena en BD

```python
from app.services.tiktok_script_generator import TikTokScriptGenerator

gen = TikTokScriptGenerator()
variantes = gen.generar_variantes_lote(
    nombre_producto="Producto X",
    categoria="Accesorios",
    cantidad=5
)
```

---

## 🗄️ Base de Datos

### Tablas Principales

#### `productos_validados`
```sql
CREATE TABLE productos_validados (
    id INTEGER PRIMARY KEY,
    sku TEXT UNIQUE,
    costo_origen REAL,
    pvp REAL,
    margen_bruto REAL,
    status_validacion TEXT,  -- 'validado' | 'rechazado'
    validado_regla_3x BOOLEAN,
    peso_kg REAL,
    nota_auditoria TEXT,
    creada_at TEXT,
    actualizada_at TEXT
);
```

#### `transcripciones_youtube`
```sql
CREATE TABLE transcripciones_youtube (
    id INTEGER PRIMARY KEY,
    video_id TEXT,
    titulo TEXT,
    canal TEXT,
    fecha TEXT,
    transcripcion_texto TEXT,
    transcripcion_limpia TEXT,
    hash_md5 TEXT UNIQUE,
    tokens_original INTEGER,
    tokens_limpios INTEGER,
    procesada BOOLEAN,
    creada_at TEXT,
    actualizada_at TEXT
);
```

#### `copys_generados`
```sql
CREATE TABLE copys_generados (
    id INTEGER PRIMARY KEY,
    producto_id INTEGER,
    titulo_copy TEXT,
    descripcion TEXT,
    attention_score REAL,
    interest_score REAL,
    decision_score REAL,
    action_score REAL,
    promedio_score REAL,
    sin_superlativos BOOLEAN,
    rating_usuario INTEGER,
    context_kb_reference TEXT,
    creada_at TEXT
);
```

#### `guiones_tiktok`
```sql
CREATE TABLE guiones_tiktok (
    id INTEGER PRIMARY KEY,
    producto_id INTEGER,
    titulo TEXT,
    hook TEXT,
    cuerpo TEXT,
    cta TEXT,
    guion_completo TEXT,
    patron_hook TEXT,
    duracion_segundos INTEGER,
    context_kb_reference TEXT,
    rating_usuario INTEGER,
    creada_at TEXT
);
```

---

## 🔧 Variables de Entorno

Copia `.env.example` → `.env` y configura:

```bash
# API de OpenRouter (única clave obligatoria)
OPENROUTER_API_KEY=sk-or-v1-tu_clave

# Ruta a BD (opcional)
DATABASE_PATH=app/database/dropshipping_suite.db
```

`.env.example` es la lista completa y vigente de variables (Make.com, remove.bg, Higgsfield, Shopify, intervalos de sincronización…). Las reglas financieras no se configuran por entorno: viven en `app/services/financial_validator.py`.

---

## 🧪 Testing

```bash
python -m pytest tests/ -q                 # suite completa
python cli_test.py                         # humo de FASE 0 (BD, validador, limpieza)
python scripts/sync_readme.py --check      # README sincronizado
python scripts/github_self_heal.py --dry-run   # relevamiento del agente GitHub sin escribir
```

---

## 📈 KPIs de Éxito

| Métrica | Target |
|---------|--------|
| Reducción tokens (limpieza) | -40 a -60% |
| Copys sin superlativos | 100% |
| Guiones TikTok viables | 100% |

---

## 🎨 Interfaces

- **Panel web** (FastAPI, `app/services/dashboard_server.py`): productos, negocio, Insights KB, tienda Shopify, sistema y configuración. Es la referencia visual; el escritorio replica su diseño.
- **Escritorio** (Tkinter, `app/main.py`): validador financiero, monitor de YouTube, panel de tienda y configuración. El `.exe` arranca el servidor web por sí mismo.

---

## 📚 Documentación de Referencia

- **Reglas de Negocio:** `.github/instructions/ecom-financial-rules.md.instructions.md`
- **Contexto KB:** `.github/instructions/dropshipping-kb-context.md.instructions.md`
- **Fórmulas:** `ai_workspace/context/formulas_conversion.md`
- **Tendencias:** `ai_workspace/context/matriz_tendencias.md`
- **Tráfico:** `ai_workspace/context/operaciones_trafico.md`

---

## 📞 Soporte

Para reportar bugs o sugerencias, contacta al equipo GEM OS.

---

## 📄 Licencia

Copyright 2026 GEM OS. Todos los derechos reservados.

---

## 🏆 Construcción Basada En

- **KDP Master Suite** (v3.7.2): Pipeline YouTube → Transcripción → KB → GEM
- **GEM OS**: Gobernanza de reglas inmutables y auditoría técnica
- **Mentores**: Adrián Sáenz (Regla 3x), Iván Caicedo (Logística), JaviEcom/Marc Verdú/Vic Ecomilions (Copywriting)

---
