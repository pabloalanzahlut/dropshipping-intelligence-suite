# 🧪 Testing Guide — Dashboard v3.0 Premium

## 📋 Guía de Pruebas Completa

### 1️⃣ Prueba Básica de Sintaxis

```bash
cd H:\dropshipping_intelligence_suite
python -m py_compile app/ui/components/dashboard_panel.py
python -m py_compile app/ui/themes/premium_theme.py
python -m py_compile app/ui/components/navigation_premium.py
```

**Resultado esperado:** Sin errores

### 2️⃣ Prueba Visual Directa

```bash
python test_dashboard_premium.py
```

**Lo que debe verse:**
- ✅ Ventana con fondo ultra-oscuro (#0f0f0f)
- ✅ Header con título "📊 Dashboard Analytics"
- ✅ 4 KPI cards con bordes coloreados
- ✅ Tablas con datos de la BD
- ✅ Gráficos (si hay datos)
- ✅ Mensaje "Dashboard Premium v3.0 cargado exitosamente"

### 3️⃣ Prueba de Inicio de Aplicación

```bash
python app/main.py
```

**Verificar:**
- ✅ Ventana abre sin errores
- ✅ Dashboard carga automáticamente
- ✅ Pestana "🏠 Dashboard" es la primera
- ✅ Botones de tema funcionan
- ✅ Panel se carga con datos

### 4️⃣ Pruebas Visuales por Componente

#### Componente: Header
**Buscar:**
- ✅ Título "📊 Dashboard Analytics" en 18pt bold
- ✅ Timestamp visible
- ✅ Botones "⚡ Sincronizar" y "🔄 Actualizar"
- ✅ Botones con colores correctos
- ✅ Hover effects en botones

#### Componente: KPI Cards
**Buscar:**
- ✅ 4 tarjetas horizontales
- ✅ Borde superior coloreado (verde, azul, ámbar, rosa)
- ✅ Icono + título en cada card
- ✅ Valor numérico grande (22pt)
- ✅ Indicador de tendencia "↑" + texto

**Verificar colores:**
| Card | Color Esperado | Hex |
|------|----------------|-----|
| 1 | Verde | #10b981 |
| 2 | Azul | #3b82f6 |
| 3 | Ámbar | #f59e0b |
| 4 | Rosa | #ec4899 |

#### Componente: Tablas
**Buscar:**
- ✅ Tabla izquierda: "✅ Últimas Validaciones"
- ✅ Tabla derecha: "✍️ Últimos Copys"
- ✅ Encabezados centrados
- ✅ Alternancia de colores (zebra striping)
- ✅ Filas pares: #1a1a1a
- ✅ Filas impares: #252525
- ✅ Hover effects gris oscuro

#### Componente: Gráficos
**Buscar:**
- ✅ Sección "📈 Tráfico y Tendencias"
- ✅ Dos gráficos (tráfico y nichos)
- ✅ Canvas con fondo #252525
- ✅ Placeholder "📊 Datos en procesamiento..."

### 5️⃣ Pruebas de Funcionalidad

#### Test: Actualizar Dashboard
1. Hacer click en "🔄 Actualizar"
2. **Verificar:**
   - ✅ Timestamp se actualiza
   - ✅ Datos se recargan
   - ✅ No hay errores en consola

#### Test: Sincronizar
1. Hacer click en "⚡ Sincronizar"
2. **Verificar:**
   - ✅ Mensaje de confirmación
   - ✅ Datos se actualizan

#### Test: Cambiar Tema
1. En el toolbar, seleccionar "☀️ Claro"
2. **Verificar:**
   - ✅ Dashboard cambia a tema claro
   - ✅ Colores adaptan correctamente

3. Volver a "🌙 Oscuro"
4. **Verificar:**
   - ✅ Dashboard vuelve a oscuro
   - ✅ Colores se restauran

#### Test: Responsive Design
1. Redimensionar ventana a 1280x800
2. **Verificar:**
   - ✅ Componentes se adaptan
   - ✅ Texto no se corta
   - ✅ Tablas scrollean correctamente

3. Redimensionar a 1920x1080
4. **Verificar:**
   - ✅ Layout se expande correctamente
   - ✅ Espaciado mantiene proporción

### 6️⃣ Pruebas de Base de Datos

#### Test: Carga de Datos
1. Dashboard abre
2. **Verificar:**
   - ✅ KPI cards muestran números
   - ✅ Tablas se llenan con datos
   - ✅ No hay errores de conexión BD

#### Test: Actualización Periódica
1. Esperar 30 segundos
2. **Verificar:**
   - ✅ Timestamp se actualiza
   - ✅ Datos se recargan automáticamente

#### Test: Sin Base de Datos
1. Desconectar BD o usar BD vacía
2. **Verificar:**
   - ✅ KPI cards muestran "0"
   - ✅ Tablas están vacías
   - ✅ No hay crashes

### 7️⃣ Pruebas de Performance

#### Test: Renderizado Inicial
**Medir tiempo:**
1. Ejecutar `time python test_dashboard_premium.py`
2. Medir desde inicio hasta "Dashboard Premium v3.0 cargado"
3. **Esperado:** < 5 segundos

#### Test: Actualización Periódica
**Medir CPU:**
1. Mantener app abierta 5 minutos
2. Revisar task manager
3. **Esperado:** CPU < 5%, Memoria estable

#### Test: Memory Leak
1. Abrir/cerrar dashboard 10 veces
2. Revisar memoria usada
3. **Esperado:** Memoria se libera, sin leak

### 8️⃣ Pruebas de Accesibilidad

#### Test: Contraste de Texto
- ✅ Texto blanco (#ffffff) sobre fondos oscuros: ratio 20:1+ ✓
- ✅ Texto gris (#b0b0b0) sobre fondos oscuros: ratio 7:1+ ✓
- ✅ Cumple WCAG AA mínimo

#### Test: Tamaño de Fuente
- ✅ Título: 18pt (legible desde 50cm)
- ✅ Body: 10pt (legible desde 40cm)
- ✅ Datos: 10pt (legible)

#### Test: Navegación
- ✅ Botones enfocables con Tab
- ✅ Enlaces/botones con contraste de hover
- ✅ Estados visuales claros

### 9️⃣ Pruebas de Compatibilidad

#### Sistemas Operativos
```bash
# Windows 10/11
python app/main.py

# WSL/Linux (si aplica)
python app/main.py

# macOS (si aplica)
python app/main.py
```

**Verificar:**
- ✅ Fuentes se renderizan correctamente
- ✅ Colores son consistentes
- ✅ Layout es igual

#### Resoluciones de Pantalla
- ✅ 1024x768 (old)
- ✅ 1280x800 (netbook)
- ✅ 1920x1080 (full HD)
- ✅ 2560x1440 (2K)
- ✅ 3840x2160 (4K - si aplica)

### 🔟 Checklist de QA

```
VISUAL
[ ] Dashboard se ve profesional
[ ] Colores son consistentes
[ ] Tipografía es jerárquica
[ ] Espaciado es uniforme
[ ] No hay elementos cortados

INTERACCIÓN
[ ] Botones responden al click
[ ] Hover effects funcionan
[ ] Tablas scrollean
[ ] Datos se actualizan
[ ] Sin lag/stuttering

FUNCIONALIDAD
[ ] KPI cards cargan datos
[ ] Tablas muestran información
[ ] Sincronización funciona
[ ] Actualización periódica activa
[ ] Temas cambian correctamente

PERFORMANCE
[ ] Inicio < 5 segundos
[ ] CPU bajo (<5% idle)
[ ] Memoria estable
[ ] No hay memory leaks
[ ] Scroll suave

COMPATIBILIDAD
[ ] Funciona en Windows 10/11
[ ] Funciona en Python 3.8+
[ ] BD se conecta correctamente
[ ] Datos cargan sin errores
```

---

## 📊 Reportes de Prueba

### Ejemplo: Reporte de Prueba Exitosa

```
┌──────────────────────────────────────────────────────────────────┐
│ REPORTE DE PRUEBA - Dashboard v3.0 Premium                      │
├──────────────────────────────────────────────────────────────────┤
│ Fecha:                 2026-10-31                                │
│ Versión:               3.0                                       │
│ Estado:                ✅ PASSOU                                 │
│                                                                  │
│ PRUEBAS REALIZADAS:                                             │
│ [✓] Sintaxis Python (3 archivos)                               │
│ [✓] Renderizado Visual                                         │
│ [✓] Carga de Datos BD                                          │
│ [✓] Actualización Periódica                                    │
│ [✓] Responsive Design (1280x800, 1920x1080)                    │
│ [✓] Hover Effects y Animaciones                                │
│ [✓] Performance (<5s inicio)                                   │
│ [✓] Accesibilidad WCAG AA                                      │
│ [✓] Memory Management (sin leaks)                              │
│ [✓] Cambio de Temas                                            │
│                                                                  │
│ RESULTADOS:                                                     │
│ Total Pruebas:         10                                       │
│ Exitosas:              10 (100%)                                │
│ Fallidas:              0                                        │
│ Tiempo de Inicio:      2.3s                                     │
│ Memoria Usada:         145MB                                    │
│                                                                  │
│ CONCLUSIÓN: El dashboard está listo para producción            │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🐛 Troubleshooting

### Problema: El dashboard no abre

**Solución:**
```python
# Verificar importes
from app.ui.components.dashboard_panel import DashboardPanel
print("✅ Import correcto")

# Verificar BD
from app.database.connection import DatabaseConnection
db = DatabaseConnection()
print("✅ BD conectada")
```

### Problema: Colores no se ven correctos

**Solución:**
- Verificar que uses tema "dark"
- Revisar valores de color en `premium_theme.py`
- Probar en Python 3.9+ si es posible

### Problema: Tablas no muestran datos

**Solución:**
```python
# Verificar BD tiene datos
cursor.execute("SELECT COUNT(*) FROM productos_validados")
print(cursor.fetchone()[0])  # Debe ser > 0
```

### Problema: Performance lento

**Solución:**
- Reducir frecuencia de actualización (línea 245)
- Limitar número de filas en tablas
- Verificar queries de BD son eficientes

---

## 📞 Reporte de Bugs

Si encuentras bugs:

1. **Documenta el problema:**
   - Paso a paso para reproducir
   - Captura de pantalla
   - Error en consola

2. **Revisa:**
   - Python version: `python --version`
   - tkinter: `python -m tkinter`
   - BD status: `sqlite3 gem_os.db ".tables"`

3. **Reporta:**
   - Crear archivo `BUG_REPORT.md`
   - Incluir traceback completo
   - Sistema operativo

---

**Guía de Pruebas Completada ✅**  
**Estado:** Listo para QA y Producción  
**Versión:** 3.0  
