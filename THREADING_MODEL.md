# 🧵 MODELO DE CONCURRENCIA — GEM OS Suite

## 📊 Arquitectura de Hilos

```
┌────────────────────────────────────────────────────────────┐
│                    GEM OS THREADING MODEL                    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  HILO PRINCIPAL (MAINLOOP TKINTER)                          │
│  ├── Renderizado de UI                                      │
│  ├── Event Loop Tkinter (after() cada 100ms)               │
│  └── HTTP Server Uvicorn (Dashboard FastAPI)                │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │ HILO DAEMON: YouTube Monitor (Ingesta Masiva)    │        │
│  │ ├── Descarga transcripciones                     │        │
│  │ ├── Limpieza UTF-8                               │        │
│  │ └── Escritura KB                                 │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │ HILO DAEMON: Dashboard Server (Uvicorn)         │        │
│  │ └── Sirve FastAPI en puerto 8050                │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐        │
│  │ COLA (Queue): Log ConsoleView                   │        │
│  │ ├── Producer: Cualquier hilo escribe log         │        │
│  │ └── Consumer: Mainloop TK (after 100ms)          │        │
│  └─────────────────────────────────────────────────┘        │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## 1️⃣ HILO PRINCIPAL — TKINTER MAINLOOP

**Propósito:** Interfaz gráfica y coordinación

```
Responsabilidades:
├── Renderizar ventanas y tabs
├── Manejar eventos de usuario (clicks, inputs)
├── Polling de log_queue cada 100ms
└── Graceful shutdown al cerrar
```

**Archivo:** `app/main.py` — `GEMOSApplication`

**Threading Safety:**
- ✅ Solo el hilo principal toca widgets de Tkinter
- ✅ `after()` para tareas programadas
- ✅ `queue.Queue` para pasar datos entre hilos

---

## 2️⃣ HILO DAEMON — YouTube Monitor (Ingesta)

**Propósito:** Sincronización pesada de canales

```
Responsabilidades:
├── Leer youtube_channels.json
├── Descargar transcripciones (yt-dlp/youtube-transcript-api)
├── Limpiar (TranscriptCleaner)
├── Verificar idempotencia (IdempotencyGuard)
├── Escribir en KB (SQLite)
└── Reportar progreso via callbacks
```

**Archivo:** `app/services/provider_monitor_engine.py`

**Threading Safety:**
- ✅ `daemon=True` (se cierra automáticamente al salir)
- ✅ `db_manager` compartido (misma conexión SQLite)
- ✅ Log via callback thread-safe (queue)

---

## 3️⃣ COLA DE LOGS — ConsoleView

**Propósito:** Comunicación asíncrona hilos → UI

```
┌─────────────────────────────────────┐
│       queue.Queue (log_queue)        │
├─────────────────────────────────────┤
│ Producer: (cualquier hilo)          │
│   thread.put(log_message)            │
├─────────────────────────────────────┤
│ Consumer: (mainloop TK, after 100ms) │
│   try: msg = log_queue.get_nowait()  │
│   except queue.Empty: pass           │
└─────────────────────────────────────┘
```

**Archivo:** `app/ui/components/console_view.py`

---

## 4️⃣ HILO DAEMON — Dashboard Server (FastAPI)

**Propósito:** Servir dashboard web en background

```
Responsabilidades:
├── Iniciar Uvicorn en hilo separado
├── Servir rutas: /, /api/health, /api/dashboard
├── NO bloquear el mainloop de Tkinter
└── Cerrar gracefulmente al salir
```

**Archivo:** `app/services/dashboard_server.py`

---

## 5️⃣ RECURSOS COMPARTIDOS Y SEGURIDAD

### Estado Compartido:
| Recurso | Acceso | Thread-Safe |
|---------|--------|-------------|
| `db_manager` (SQLite) | Singleton inyectado | ✅ (PRAGMA journal_mode) |
| `log_queue` (Queue) | Producer/Consumer | ✅ (thread-safe nativa) |
| `log_callback` | Asignado en main thread | ✅ (solo callback) |
| `config` (dict) | Solo lectura | ✅ (inmutable runtime) |

### Reglas de Seguridad:
1. **Nunca** tocar widgets Tkinter desde hilos secundarios
2. **Siempre** usar `after()` para actualizar UI desde hilos
3. **Siempre** usar `daemon=True` en hilos worker
4. **Nunca** llamar `time.sleep()` en el main thread
5. **Siempre** cerrar conexiones DB en graceful shutdown

---

## 6️⃣ DIAGRAMA DE SECUENCIA

```
MAIN THREAD                          WORKER THREAD
     │                                      │
     │── Inicia worker ──────────────────►  │
     │                                      │
     │                                      │── Descarga transcripciones
     │                                      │── Limpieza UTF-8
     │                                      │── Hash MD5 (idempotencia)
     │                                      │── Escritura SQLite
     │                                      │
     │◄── log_queue.put("[OK] Completado")  │
     │                                      │
     │── after(100ms) → poll log_queue      │
     │── Actualiza UI                       │
     │                                      │
     │── Worker termina                     │
     │                                      │
```