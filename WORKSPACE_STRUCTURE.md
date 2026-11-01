# 📁 ESTRUCTURA DEL WORKSPACE — GEM OS Suite

## 📊 Árbol de Directorios

```
h:\dropshipping_intelligence_suite\
│
├── .continue/               # Config Continue (VS Code)
│   ├── agents/
│   ├── prompts/
│   ├── rules/
│   ├── skills/
│   └── workflows/
│
├── .github/
│   ├── instructions/
│   └── skills/
│
├── ai_workspace/            # [Workspace Agentes IA]
│   ├── agents.md            # Gobernanza global
│   ├── context/             # Contextos por dominio
│   ├── skills/              # Procedimientos operativos
│   ├── projects/            # Proyectos activos
│   ├── memory/              # Memoria histórica
│   ├── skills_library/      # Skills sin curar
│   └── packed_context/      # Contexto empaquetado
│
├── app/                     # [CÓDIGO FUENTE]
│   ├── config/              # ← NUEVO Config centralizada
│   │   ├── __init__.py
│   │   ├── path_manager.py  # 4 métodos de rutas
│   │   └── bootstrap.py     # Inicialización
│   ├── agents_engine/       # Orquestador de agentes
│   ├── core/                # Módulos core
│   ├── database/            # Capa BD
│   ├── services/            # Capa de servicios
│   └── ui/components/       # Componentes Tkinter
│
├── data/                    # ← NUEVO Datos centralizados
│   ├── dropshipping_suite.db
│   ├── youtube_channels.json
│   ├── queue_state.json
│   └── config.json
│
├── logs/elite/              # Logs desarrollo
├── backups/                 # Backups desarrollo
├── governance/tests/        # Tests gobernanza
├── bin/ffmpeg/              # Binarios externos
│
├── dist/GEM_OS_Suite/       # Compilación .exe
│   ├── data_template/       # Plantillas semilla
│   └── GEM_OS_Suite.exe
│
├── WORKFLOW_COMPLETE.md     # Flujo completo
├── THREADING_MODEL.md       # Modelo concurrencia
├── WORKSPACE_STRUCTURE.md   # Este documento
└── ...

---

## 🔄 Desarrollo vs Producción

### 💻 DESARROLLO (`python app/main.py`)
```
h:\dropshipping_intelligence_suite\
├── app/                # Código fuente
├── data/               # Datos de desarrollo
├── logs/               # Logs de desarrollo
├── backups/            # Backups de desarrollo
└── ai_workspace/       # Workspace de agentes
```

### 🚀 PRODUCCIÓN (`GEM_OS_Suite.exe`)
```
C:\Users\<User>\AppData\Roaming\GEM_OS_Suite\
├── data/               # Datos reales de producción
│   ├── dropshipping_suite.db
│   ├── youtube_channels.json
│   └── config.json
├── logs/elite/         # Logs de producción
├── backups/            # Backups de producción
└── ai_workspace/       # Workspace de producción
```

**Nota:** El .exe puede estar en cualquier ubicación. Los datos siempre van a AppData.

---

## 📋 Propósito de Directorios Clave

| Directorio | Propósito | Creado por |
|------------|-----------|------------|
| `app/config/` | Configuración centralizada | 🆕 PathManager |
| `data/` | Datos runtime (BD, config) | 🆕 Bootstrap |
| `logs/` | Logs de ejecución | PathManager |
| `backups/` | Backups automáticos | PathManager |
| `ai_workspace/` | Workspace de agentes IA | Git + Bootstrap |
| `dist/` | Compilación PyInstaller | build_exe.py |
| `bin/` | Binarios externos | install_ffmpeg.py |

---

## 📐 Reglas de Estructura

1. **Un solo punto de verdad:** PathManager.get_paths() resuelve TODAS las rutas
2. **Nunca rutas relativas a CWD:** Siempre relativas a base_dir o AppData
3. **Desarrollo aislado de Producción:** datos nunca se mezclan
4. **Auto-creación:** Directorios se crean automáticamente al iniciar
5. **Compatibilidad legacy:** bootstrap.py migra archivos antiguos
6. **4 métodos separados:** Detección → Base → Datos → Errores
```