# 🚀 Quick Start - GEM OS v3.0 Jack-Style

## ⚡ Inicio Rápido en 3 Pasos

### 1️⃣ Ejecutar la Aplicación

```bash
# Opción A: Script de prueba
python test_jack_ui.py

# Opción B: Aplicación principal
python -m app.main

# Opción C: Lanzador Windows (doble click)
RUN_JACK_UI.bat
```

### 2️⃣ Navegar al Panel Validador

1. Abrir la aplicación
2. Click en **"💎 Validador"** en el sidebar izquierdo
3. ¡Explora el nuevo diseño!

### 3️⃣ Probar Componentes

```bash
# Demo interactivo de componentes
python demo_jack_components.py
```

---

## 📦 Archivos del Rediseño

### Componentes Principales

| Archivo | Descripción | Ubicación |
|---------|-------------|-----------|
| `financial_validator_panel_v2.py` | Panel Validador rediseñado | `app/ui/components/` |
| `navigation_v2.py` | Sidebar glassmorphism | `app/ui/components/` |
| `jack_styles.py` | Sistema de estilos ttk | `app/ui/themes/` |
| `design_tokens.py` | Paleta neon actualizada | `app/ui/themes/` |
| `dark_theme.py` | Tema Jack v3.0 | `app/ui/themes/` |

### Scripts de Prueba

| Script | Propósito |
|--------|-----------|
| `test_jack_ui.py` | Ejecuta la app completa |
| `demo_jack_components.py` | Demo de componentes |
| `RUN_JACK_UI.bat` | Lanzador Windows |

### Documentación

| Documento | Contenido |
|-----------|-----------|
| `JACK_STYLE_REDESIGN.md` | Filosofía y arquitectura |
| `UI_V3_JACK_STYLE.md` | Guía completa de uso |
| `REDESIGN_SUMMARY.md` | Resumen de cambios |
| `VISUAL_CHANGES.md` | Comparación visual |
| `QUICK_START_V3.md` | Esta guía |

---

## 🎨 Características Principales

### 💎 Componentes Premium

#### ModernButton
```python
from app.ui.components.financial_validator_panel_v2 import ModernButton

btn = ModernButton(
    parent,
    text="Click Me",
    command=callback,
    style="primary"  # primary, success, warning, error, secondary
)
```

#### GlassCard
```python
from app.ui.components.financial_validator_panel_v2 import GlassCard

card = GlassCard(
    parent,
    title="📦 Métrica",
    style="success",  # primary, success, error, info, purple, pink
    width=280,
    height=110
)
card.update_content("142", "items procesados")
```

#### ModernEntry
```python
from app.ui.components.financial_validator_panel_v2 import ModernEntry

entry = ModernEntry(parent, placeholder="Buscar producto...")
value = entry.get()
```

#### Sidebar
```python
from app.ui.components.navigation_v2 import Sidebar

sidebar = Sidebar(
    parent,
    items=[
        ("🏠", "Dashboard", callback1),
        ("💎", "Validador", callback2),
    ]
)
```

---

## 🎯 Uso del Panel Validador

### Importar Productos

**CSV:**
```csv
sku,costo_origen,peso_kg,pvp
PROD-001,12.50,0.85,37.50
PROD-002,25.00,1.35,60.00
```

**JSON:**
```json
[
  {
    "sku": "PROD-001",
    "costo_origen": 12.50,
    "peso_kg": 0.85,
    "pvp": 37.50
  }
]
```

### Reglas de Validación

1. **Regla 3x** (Adrián Sáenz): `PVP >= Costo * 3`
2. **Coste de origen** recomendado: $5–15
3. Sin umbral de margen % ni límite de peso (el curso no los fija)

### Interpretar Resultados

- ✅ **Verde**: Producto APROBADO (cumple todas las reglas)
- ❌ **Rosa**: Producto RECHAZADO (falla al menos una regla)
- 🔵 **Cyan**: Headers y acentos
- 📊 **KPI Cards**: Resumen visual de métricas

---

## 🔧 Configuración

### Aplicar Estilos Globalmente

```python
from app.ui.themes.jack_styles import apply_jack_styles
import tkinter as tk

root = tk.Tk()
apply_jack_styles(root)  # Configura ttk.Style
```

### Crear Bordes Neon

```python
from app.ui.themes.jack_styles import create_neon_border
from app.ui.themes.design_tokens import NEON_COLORS

border_frame, inner_frame = create_neon_border(
    parent,
    color=NEON_COLORS['cyan'],
    thickness=2
)
# Añadir widgets a inner_frame
```

### Panel Glassmorphism

```python
from app.ui.themes.jack_styles import create_glass_panel

canvas = create_glass_panel(parent, width=400, height=300)
# Dibujar contenido en canvas
```

---

## 🎨 Paleta de Colores Rápida

```python
from app.ui.themes.design_tokens import (
    NEON_COLORS,
    DARK_BASE,
    TEXT_COLORS,
    STATUS_COLORS
)

# Acceder a colores
cyan = NEON_COLORS['cyan']       # #00f5ff
bg = DARK_BASE['bg_primary']     # #0a0a0f
text = TEXT_COLORS['primary']    # #ffffff
success = STATUS_COLORS['success'] # #00ff88
```

---

## 🐛 Troubleshooting

### Problema: Módulo no encontrado
```bash
# Asegúrate de estar en la raíz del proyecto
cd H:\dropshipping_intelligence_suite
python test_jack_ui.py
```

### Problema: Colores no se ven
```python
# Asegúrate de llamar apply_jack_styles
from app.ui.themes.jack_styles import apply_jack_styles
apply_jack_styles(root)  # ← Importante
```

### Problema: Componentes no aparecen
```python
# Verifica imports correctos
from app.ui.components.financial_validator_panel_v2 import (
    ModernButton,
    GlassCard,
    ModernEntry
)
```

---

## 📚 Documentación Completa

Para información detallada, consulta:

- **[JACK_STYLE_REDESIGN.md](JACK_STYLE_REDESIGN.md)** - Diseño y arquitectura
- **[UI_V3_JACK_STYLE.md](UI_V3_JACK_STYLE.md)** - Guía de uso completa
- **[REDESIGN_SUMMARY.md](REDESIGN_SUMMARY.md)** - Resumen de cambios
- **[VISUAL_CHANGES.md](VISUAL_CHANGES.md)** - Comparación visual

---

## 🎓 Tutoriales

### Tutorial 1: Crear un Botón Premium

```python
import tkinter as tk
from app.ui.themes.jack_styles import apply_jack_styles
from app.ui.components.financial_validator_panel_v2 import ModernButton

root = tk.Tk()
apply_jack_styles(root)

def on_click():
    print("¡Botón clickeado!")

btn = ModernButton(
    root,
    text="Click Me",
    command=on_click,
    style="primary",
    width=160,
    height=40
)
btn.pack(padx=20, pady=20)

root.mainloop()
```

### Tutorial 2: Crear una KPI Card

```python
import tkinter as tk
from app.ui.themes.jack_styles import apply_jack_styles
from app.ui.components.financial_validator_panel_v2 import GlassCard

root = tk.Tk()
apply_jack_styles(root)

card = GlassCard(
    root,
    title="📦 Total Productos",
    style="success",
    width=300,
    height=120
)
card.pack(padx=20, pady=20)
card.update_content("142", "productos analizados")

root.mainloop()
```

### Tutorial 3: Input con Focus Neon

```python
import tkinter as tk
from app.ui.themes.jack_styles import apply_jack_styles
from app.ui.components.financial_validator_panel_v2 import ModernEntry, ModernButton

root = tk.Tk()
apply_jack_styles(root)

entry = ModernEntry(root, placeholder="Ingresa tu nombre...")
entry.pack(padx=20, pady=20)

def get_value():
    print(f"Valor: {entry.get()}")

btn = ModernButton(root, text="Obtener Valor", command=get_value, style="primary")
btn.pack(padx=20, pady=10)

root.mainloop()
```

---

## 🎉 ¡Listo!

Ahora tienes todo lo necesario para usar **GEM OS v3.0 Jack-Style**.

### Próximos Pasos

1. ✅ Ejecutar `test_jack_ui.py`
2. ✅ Explorar el panel Validador
3. ✅ Probar `demo_jack_components.py`
4. ✅ Leer la documentación completa
5. ✅ Crear tus propios componentes premium

---

## 🔗 Enlaces Rápidos

- **YouTube**: [@Itssssss_Jack](https://www.youtube.com/@Itssssss_Jack) (inspiración)
- **GitHub**: (tu repo aquí)
- **Documentación**: Ver archivos `*.md` en la raíz

---

## 📞 Soporte

Si encuentras problemas:

1. Consulta la sección Troubleshooting
2. Revisa la documentación completa
3. Verifica los scripts de ejemplo

---

**Versión**: 3.0.0  
**Última actualización**: 2026-10-31  
**Autor**: GEM OS Development Team

💎 **¡Disfruta del nuevo diseño premium!** 🔵
