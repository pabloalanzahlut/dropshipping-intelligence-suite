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
<!-- /AUTO:skills -->

---

## 🛡️ CI/CD, seguridad y agente GitHub autónomo

- **Validación** (`validate-pipeline.yml`): comprueba archivos obligatorios, que no haya `.env` versionado y ejecuta **gitleaks v8.30.1** (binario con SHA-256 fijado) sobre **todo el historial**. Corre en cada push/PR relevante y **a diario a las 06:17 UTC**.
- **Agente autónomo** (`self-heal.yml` + `scripts/github_self_heal.py`): cuando un CI falla, busca la firma en el catálogo `ai_workspace/config/github_fixes.json`; si hay fix automático abre una rama `selfheal/*`, la verifica con gitleaks y la fusiona; si la firma es nueva abre un Issue; **si detecta una fuga real de secreto abre un Issue crítico y no reescribe el historial** (hay que rotar la credencial). Cierra solo los PR de Dependabot obsoletos y registra cada incidente en [`github_kb.md`](ai_workspace/knowledge_base/github_kb.md).
- **README**: `sync_readme.py --check` falla el CI si estas secciones se desfasan; el agente las regenera.
- **Secretos**: `.env`, credenciales y cookies nunca se versionan (`.gitignore`); solo `.env.example`. Detalle en [`SECURITY.md`](SECURITY.md).

<!-- AUTO:workflows -->
<!-- /AUTO:workflows -->

---

## 📦 Dependencias fijadas

<!-- AUTO:deps -->
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
- **Regla 3x** (Adrián Sáenz): PVP = Costo × 3
- **Multiplicador**: mínimo 2x (rechaza) y objetivo 3x (advierte), sobre coste landed (producto + envío)
- Sin umbral de margen % ni límite de peso: el curso no los fija

```python
from app.services.financial_validator import FinancialValidator

validator = FinancialValidator()
resultado = validator.validar_producto(
    sku="PROD-001",
    costo_origen=10.0,
    peso_kg=0.8
)
print(resultado)  # {'validado': True, 'pvp_calculado': 30.0, ...}
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
# API de OpenRouter (para futura integración IA)
OPENROUTER_API_KEY=tu_clave_aqui

# Ruta a BD (opcional)
DATABASE_PATH=app/database/dropshipping_suite.db

# API de YouTube (opcional, para descarga automática)
YOUTUBE_API_KEY=

# Configuración de Transcript Cleaner
TRANSCRIPT_CLEANER_FILLER_WORDS=ehh,umm,ok,bueno,mira,entonces,además
TRANSCRIPT_CLEANER_MIN_PAUSE_SECONDS=5
TRANSCRIPT_CLEANER_TOKEN_REDUCTION_TARGET=0.50

# Configuración de Validación Financiera
FINANCIAL_VALIDATOR_REGLA_3X_MULTIPLICADOR=3.0
FINANCIAL_VALIDATOR_MARGEN_BRUTO_MINIMO=0.70
FINANCIAL_VALIDATOR_PESO_MAXIMO_KG=1.2

# Configuración de Sincronización
YOUTUBE_MONITOR_SYNC_INTERVAL_HOURS=2
YOUTUBE_MONITOR_ENABLED=true
```

---

## 🧪 Testing

### Test FASE 0: Fundacional
```bash
python cli_test.py
```

Verifica:
- Conexión a BD
- FinancialValidator (Regla 3x, margen, peso)
- TranscriptCleaner (limpieza ultra)

### Test FASES 1, 3, 4
```bash
python test_fases_1_3_4.py
```

Verifica:
- YouTubeChannelMonitor
- CopywrightingEngine
- TikTokScriptGenerator

---

## 📈 KPIs de Éxito

| Métrica | Target |
|---------|--------|
| Reducción tokens (limpieza) | -40 a -60% |
| Copys sin superlativos | 100% |
| Guiones TikTok viables | 100% |

---

## 🎨 UI Tabs

1. **Validador Financiero (FASE 5)**
   - Importar CSV/JSON
   - Tabla de validaciones
   - Exportar CSV/JSON

2. **YouTube Monitor (FASE 1)**
   - Agregar canales
   - Sincronizar
   - Ver estadísticas

3. **Ingesta Masiva (Legacy)**
   - Ingesta de GEM OS original

---

## 🚀 Próximos Pasos (Fase 6+)

- [ ] UI para Copywriting AIDA con preview en tiempo real
- [ ] UI para Generador de Guiones TikTok (batch mode visual)
- [ ] Dashboard consolidado con gráficos
- [ ] Empaquetamiento .exe con PyInstaller
- [ ] Integración real con OpenRouter API
- [ ] Integración real con YouTube API

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

**Versión:** 1.0 (FASES 0-5 COMPLETADAS)  
**Fecha:** 2026-10-25  
**Status:** ✅ MVP OPERACIONAL (Desktop)
