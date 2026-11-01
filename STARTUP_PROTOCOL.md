# 🚀 PROTOCOLO DE INICIALIZACIÓN EN FRÍO — GEM OS

**Suite:** Dropshipping Intelligence Suite (GEM OS)  
**Status:** PRODUCCIÓN CERTIFICADA ✅  
**Fecha:** 2026-10-25

---

## 📋 COMANDOS DE INICIALIZACIÓN

### PASO 1: Verificar Entorno
```bash
# Windows PowerShell
python --version
pip --version
python -c "import tkinter; print('tkinter OK')"
```

**Requisitos Mínimos:**
- Python 3.9+
- pip (gestor de paquetes)
- tkinter (incluido en Python estándar)
- SQLite3 (incluido en Python)

---

### PASO 2: Instalar Dependencias (Primera Vez)
```bash
cd h:\dropshipping_intelligence_suite
pip install -r requirements.txt
```

**Dependencias Instaladas:**
- `requests==2.32.3` — Comunicación con APIs (OpenRouter)
- `python-dotenv==1.0.1` — Gestión de variables de entorno
- `pyinstaller==6.11.1` — Compilación a ejecutable (opcional)

---

### PASO 3: Inicializar Base de Datos
```bash
cd h:\dropshipping_intelligence_suite
python init_database.py
```

**Validaciones Ejecutadas:**
```
[OK] Conexion a BD establecida
[OK] 5 tablas creadas (video_sources, product_trends, conversion_formulas, operations_traffic, sqlite_sequence)
[OK] weight_kg validado en operations_traffic
[OK] estimated_margin validado en product_trends
[OK] framework_name validado en conversion_formulas
```

**Archivo Creado:**
- `app/database/dropshipping_suite.db` (SQLite3 relacional)

---

### PASO 4: Verificar Variables de Entorno
```bash
# Archivo: .env (debe existir en raíz del proyecto)
OPENROUTER_API_KEY=sk-or-v1-[TU_API_KEY_AQUI]
DATABASE_PATH=app/database/dropshipping_suite.db
```

**Notas Críticas:**
- ⚠️ `OPENROUTER_API_KEY` es requerido para limpieza de transcripciones
- ⚠️ `DATABASE_PATH` debe coincidir con la ruta de inicialización
- 🔐 Nunca commitear `.env` al repositorio

---

### PASO 5: Iniciar Interfaz de Usuario ConsoleView
```bash
cd h:\dropshipping_intelligence_suite
python app/main.py
```

**Interfaz Gráfica Lanzada:**
- Ventana Tkinter: "GEM OS • Dropshipping Intelligence Suite"
- Resolución: 900x600 (mín. 800x500)
- ConsoleView Terminal integrada

**Componentes en Pantalla:**
```
┌─────────────────────────────────────────┐
│  GEM OS • Dropshipping Intelligence    │
│          Suite v1.0.0                  │
├─────────────────────────────────────────┤
│                                         │
│  [Terminal/Log Output]                 │
│  • Sistema preparado                   │
│  • Base de datos conectada             │
│  • Servicios listos                    │
│                                         │
├─────────────────────────────────────────┤
│ [Iniciar Sincronización] [Estado: OK]  │
└─────────────────────────────────────────┘
```

---

## 🔄 FLUJO COMPLETO DE INICIALIZACIÓN

### Secuencia de Ejecución
```
1. Cargar variables de entorno (.env)
   └─ OPENROUTER_API_KEY, DATABASE_PATH

2. Inicializar DatabaseConnection
   ├─ Conectar a SQLite3 (app/database/dropshipping_suite.db)
   ├─ Crear esquema (5 tablas)
   └─ Validar columnas críticas

3. Inicializar ConsoleView (UI Tkinter)
   ├─ Crear ventana principal (900x600)
   ├─ Montar componentes visuales
   └─ Configurar callbacks de log

4. Inicializar ProviderMonitorEngine (en hilo daemon)
   ├─ Recibir db_manager por inyección
   ├─ Instanciar KBCacheValidator
   ├─ Instanciar KBRouter
   └─ Listo para ingesta masiva

5. Mantener mainloop de Tkinter
   └─ Esperar eventos del usuario
```

### Arquitectura de Threading
```
┌─ MAINLOOP TKINTER (hilo principal)
│  ├─ Renderizar UI ConsoleView
│  ├─ Escuchar eventos de usuario
│  └─ Escribir logs en terminal
│
└─ DAEMON THREAD (background)
   ├─ ProviderMonitorEngine
   ├─ Descargar transcripciones
   ├─ Limpiar con OpenRouter
   ├─ Ingestar en BD (SQLite)
   └─ Callback → ConsoleView.write_log()
```

---

## 🧪 VALIDACIÓN POST-STARTUP

### Verificar que el Sistema Está Operativo
```bash
# En otra terminal (mientras main.py está corriendo):
python -c "
from app.database.connection import DatabaseConnection
from app.services.openrouter_client import OpenRouterTranscriptionCleaner
print('[OK] Todas las importaciones funcionales')
"
```

### Verificar Conectividad OpenRouter
```bash
# Prueba de conectividad
python -c "
import os
os.environ['OPENROUTER_API_KEY'] = 'test'
from app.services.openrouter_client import OpenRouterTranscriptionCleaner
cleaner = OpenRouterTranscriptionCleaner()
print(f'[OK] Endpoint: {cleaner.url}')
# Resultado esperado: https://openrouter.ai/api/v1/chat/completions
"
```

### Verificar BD Inicializada
```bash
sqlite3 app/database/dropshipping_suite.db "SELECT COUNT(*) as tablas FROM sqlite_master WHERE type='table';"
# Resultado esperado: 5
```

---

## ⚡ COMANDOS RÁPIDOS

### One-Liner: Inicialización Completa
```bash
cd h:\dropshipping_intelligence_suite && pip install -r requirements.txt && python init_database.py && python app/main.py
```

### Limpiar Base de Datos (Reset Completo)
```bash
Remove-Item "app/database/dropshipping_suite.db" -Force
python init_database.py
```

### Modo Debug (Logs Verbosos)
```bash
$env:DEBUG=1
python app/main.py
```

---

## 🔍 TROUBLESHOOTING

### Error: `ModuleNotFoundError: No module named 'tkinter'`
**Solución:**
```bash
# En Windows, tkinter viene con Python
# Si no está presente, reinstalar Python con opción "tcl/tk"
# O instalar: pip install tk
```

### Error: `OPENROUTER_API_KEY not found`
**Solución:**
```bash
# Crear archivo .env en raíz del proyecto
echo "OPENROUTER_API_KEY=sk-or-v1-[TU_KEY]" > .env
echo "DATABASE_PATH=app/database/dropshipping_suite.db" >> .env
```

### Error: `database is locked`
**Solución:**
```bash
# Cerrar todas las instancias de main.py
# Esperar 5 segundos
# Reiniciar: python app/main.py
```

### Error: `HTTP 404 en OpenRouter`
**Solución:**
```bash
# Verificar que openrouter_client.py tiene:
# self.url = "https://openrouter.ai/api/v1/chat/completions"
# Ejecutar: python app/main.py (ya está corregido)
```

---

## ✅ CHECKLIST PRE-PRODUCCIÓN

- [ ] Python 3.9+ instalado
- [ ] pip funcional
- [ ] tkinter disponible
- [ ] requirements.txt instalado (`pip install -r requirements.txt`)
- [ ] .env configurado con OPENROUTER_API_KEY válida
- [ ] init_database.py ejecutado exitosamente
- [ ] Todas las 5 tablas creadas
- [ ] Columnas críticas validadas (weight_kg, estimated_margin, framework_name)
- [ ] app/main.py lanza interfaz sin errores
- [ ] ConsoleView se renderiza correctamente
- [ ] Botón "Iniciar Sincronización" visible y funcional

---

## 🎯 PRÓXIMO PASO

Una vez la UI esté corriendo:
1. Click en botón "Iniciar Sincronización"
2. Esperar a que el daemon thread comience ingesta masiva
3. Logs aparecerán en ConsoleView en tiempo real
4. BD se poblará con datos procesados de canales favoritos

---

## 📊 ESTADO DE PRODUCCIÓN

```
Status:           ✅ VERDE (Producción Certificada)
BD:               ✅ Operacional
OpenRouter API:   ✅ Endpoint correcto
Threading:        ✅ Inyección funcional
Gobernanza:       ✅ Activa
Documentación:    ✅ Completa
```

**El sistema está listo para operaciones normales en producción.**

