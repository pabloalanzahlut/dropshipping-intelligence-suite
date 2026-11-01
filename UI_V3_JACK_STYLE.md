# 💎 GEM OS v3.0 - Jack-Style UI/UX Premium

## 🎯 Resumen Ejecutivo

**GEM OS v3.0** introduce un rediseño completo del UI/UX inspirado en el estilo premium de **@Itssssss_Jack**, transformando la aplicación con:

- ✨ **Glassmorphism** profundo con efectos de blur
- 🌟 **Neon accents** (cyan, purple, pink)
- 🎨 **Dark mode premium** con negros profundos
- ⚡ **Micro-interacciones** y hover effects
- 🔮 **Componentes modernos** custom-built

---

## 🚀 Inicio Rápido

### Ejecutar la aplicación

```bash
# Desde la raíz del proyecto
python test_jack_ui.py
```

O directamente:

```bash
python -m app.main
```

### Ver el nuevo Validador

1. Iniciar la aplicación
2. Hacer clic en **"💎 Validador"** en el sidebar
3. Explorar los componentes premium

---

## 🎨 Características Visuales Principales

### 1. Paleta de Colores Neon

| Color | Hex | Uso |
|-------|-----|-----|
| 🔵 Cyan | `#00f5ff` | Acento principal, hover, focus |
| 🟣 Purple | `#b462ff` | Acento secundario, especial |
| 🔴 Pink | `#ff006e` | Error, crítico, alertas |
| 🟢 Green | `#00ff88` | Éxito, validación |
| 🟡 Yellow | `#ffea00` | Warning, precaución |
| ⚪ Blue | `#00d9ff` | Info, datos |

### 2. Backgrounds Profundos

| Tipo | Hex | Descripción |
|------|-----|-------------|
| Primary | `#0a0a0f` | Fondo principal (casi negro) |
| Secondary | `#13131a` | Paneles, sidebar |
| Tertiary | `#1a1a24` | Cards, modales |
| Input | `#252535` | Controles de entrada |
| Hover | `#2a2a3e` | Estado hover |

### 3. Jerarquía de Texto

| Nivel | Color | Uso |
|-------|-------|-----|
| Primary | `#ffffff` | Títulos, contenido principal |
| Secondary | `#b4b4c8` | Subtítulos, labels |
| Tertiary | `#6b6b82` | Captions, hints |
| Disabled | `#4a4a5e` | Elementos deshabilitados |

---

## 🏗️ Componentes Nuevos

### `ModernButton`
Canvas personalizado con glassmorphism.

```python
from app.ui.components.financial_validator_panel_v2 import ModernButton

btn = ModernButton(
    parent,
    text="Acción Premium",
    command=callback,
    style="primary",  # primary, success, warning, error, secondary
    width=160,
    height=40
)
```

**Estados:**
- Normal: Background oscuro, borde terciario
- Hover: Borde cyan neon, texto cyan
- Press: Background más oscuro

### `GlassCard`
Tarjeta con efecto glassmorphism.

```python
from app.ui.components.financial_validator_panel_v2 import GlassCard

card = GlassCard(
    parent,
    title="📦 Total Productos",
    style="primary",  # primary, success, error, info, purple, pink
    width=280,
    height=110
)
card.update_content("142", "productos analizados")
```

**Características:**
- Gradiente sutil de background
- Borde neon con glow
- Inner glow translúcido
- Contenido dinámico

### `ModernEntry`
Input field con focus neon.

```python
from app.ui.components.financial_validator_panel_v2 import ModernEntry

entry = ModernEntry(
    parent,
    placeholder="Ingresa el SKU...",
    width=300
)
value = entry.get()
```

**Estados:**
- Normal: Borde gris terciario
- Focus: Borde cyan neon (2px), cursor cyan
- Placeholder: Texto terciario que desaparece

### `Sidebar` (Glassmorphism)
Navegación premium colapsable.

```python
from app.ui.components.navigation_v2 import Sidebar

sidebar = Sidebar(
    parent,
    items=[
        ("🏠", "Dashboard", callback1),
        ("💎", "Validador", callback2),
        # ...
    ]
)
```

**Características:**
- Botones con hover glow
- Línea vertical cyan para ítem activo
- Colapsable (220px → 70px)
- Logo con borde neon
- Footer con botón de configuración

---

## 📊 Panel Validador - Guía de Uso

### Sección 1: Header
```
💎 Validador Financiero
Validación de productos según reglas de Adrián Sáenz e Iván Caicedo
⚡ Listo para importar productos
```
- Título con emoji y cyan neon
- Subtítulo descriptivo
- Status bar dinámico

### Sección 2: KPI Cards

4 tarjetas glassmorphism:
- **📦 Total Productos**: Contador general
- **✅ Validados**: Productos aprobados (verde)
- **❌ Rechazados**: Productos rechazados (rosa)
- **📊 Margen Promedio**: Margen bruto medio (cyan)

Cada card tiene:
- Título con emoji
- Valor grande (24px bold)
- Subtítulo informativo
- Borde neon con glow

### Sección 3: Importar Productos

Tres botones premium:
- **📄 Importar CSV**: Abre diálogo de archivo CSV
- **📋 Importar JSON**: Abre diálogo de archivo JSON
- **➕ Añadir Manual**: Modal para entrada manual (próximamente)

Formato CSV esperado:
```csv
sku,costo_origen,peso_kg,pvp
PROD-001,12.50,0.85,37.50
PROD-002,25.00,1.35,60.00
```

Formato JSON esperado:
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

### Sección 4: Tabla de Validaciones

Columnas:
- **#**: Número de fila
- **SKU**: Identificador del producto
- **Costo ($)**: Costo de origen
- **PVP ($)**: Precio de venta público
- **Margen %**: Margen bruto calculado
- **Regla 3x**: ✅ si cumple, ❌ si no
- **Peso (kg)**: Peso del producto
- **Estado**: ✅ APROBADO / ❌ RECHAZADO

**Reglas de validación:**
1. **Regla 3x** (Adrián Sáenz): `PVP >= Costo * 3`
2. **Margen mínimo**: `Margen >= 70%`
3. **Peso máximo** (Iván Caicedo): `Peso <= 1.2 kg`

**Colores de filas:**
- Verde: Producto APROBADO
- Rosa: Producto RECHAZADO
- Hover: Background lighter con borde cyan

### Sección 5: Exportar Resultados

Tres botones:
- **💾 Exportar CSV**: Guarda resultados en CSV
- **📦 Exportar JSON**: Guarda resultados en JSON
- **🗑️ Limpiar Todo**: Reset completo (confirmación)

---

## 🔧 Configuración Técnica

### Estilos Globales

Los estilos se aplican automáticamente al iniciar:

```python
from app.ui.themes.jack_styles import apply_jack_styles

root = tk.Tk()
apply_jack_styles(root)  # Configura ttk.Style globalmente
```

Esto aplica el tema Jack a:
- Todos los widgets ttk
- Frames, Labels, Buttons
- Entry, Combobox, Spinbox
- Treeview, Notebook
- Scrollbars, Progressbars
- Y más...

### Crear Bordes Neon

```python
from app.ui.themes.jack_styles import create_neon_border

border_frame, inner_frame = create_neon_border(
    parent,
    color=NEON_COLORS['cyan'],
    thickness=2
)
# Añadir widgets a inner_frame
```

### Glassmorphism Panel

```python
from app.ui.themes.jack_styles import create_glass_panel

canvas = create_glass_panel(
    parent,
    width=400,
    height=300
)
# Dibujar contenido en canvas
```

---

## 📁 Estructura de Archivos

```
app/ui/
├── themes/
│   ├── design_tokens.py          ← Paleta neon, colores base
│   ├── dark_theme.py              ← Tema Jack v3.0
│   ├── jack_styles.py             ← Sistema de estilos ttk
│   └── ...
├── components/
│   ├── financial_validator_panel_v2.py  ← Panel rediseñado
│   ├── navigation_v2.py                 ← Sidebar glassmorphism
│   └── ...
└── ...
```

### Archivos Clave

| Archivo | Descripción |
|---------|-------------|
| `design_tokens.py` | Paleta completa, constantes de diseño |
| `jack_styles.py` | Estilos ttk.Style configurables |
| `financial_validator_panel_v2.py` | Panel Validador premium |
| `navigation_v2.py` | Sidebar con glassmorphism |
| `dark_theme.py` | Tema oscuro Jack v3.0 |

---

## 🎓 Guía de Desarrollo

### Crear un Nuevo Panel con Jack-Style

```python
import tkinter as tk
from tkinter import ttk
from app.ui.themes.design_tokens import NEON_COLORS, DARK_BASE, TEXT_COLORS

class MiPanelPremium(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(style='Dark.TFrame')
        self._build_ui()
    
    def _build_ui(self):
        # Header
        header = tk.Label(
            self,
            text="💡 Mi Panel Premium",
            font=("Segoe UI", 18, "bold"),
            fg=NEON_COLORS['cyan'],
            bg=DARK_BASE['bg_primary']
        )
        header.pack(anchor="w", padx=20, pady=15)
        
        # Contenido...
```

### Añadir Hover Effects

```python
from app.ui.themes.jack_styles import apply_widget_animations

label = tk.Label(parent, text="Hover me", fg=TEXT_COLORS['secondary'])
apply_widget_animations(
    label,
    hover_color=NEON_COLORS['cyan'],
    normal_color=TEXT_COLORS['secondary']
)
```

### Usar Cards Glassmorphism

```python
from app.ui.components.financial_validator_panel_v2 import GlassCard

# Card de éxito
success_card = GlassCard(
    parent,
    title="✅ Operación Exitosa",
    style="success",
    width=300,
    height=120
)
success_card.update_content("142", "productos procesados")

# Card de error
error_card = GlassCard(
    parent,
    title="❌ Error Crítico",
    style="error",
    width=300,
    height=120
)
error_card.update_content("5", "fallos detectados")
```

---

## 🐛 Troubleshooting

### Problema: Colores no se ven
**Solución:** Asegúrate de llamar `apply_jack_styles(root)` después de crear la ventana:
```python
root = tk.Tk()
apply_jack_styles(root)  # ← Importante
```

### Problema: Sidebar no colapsa
**Solución:** Verifica que el callback del botón toggle esté conectado:
```python
sidebar = Sidebar(parent, items=[...])
# El botón ⚙️ llama internamente a _toggle_collapse
```

### Problema: Botones sin hover
**Solución:** Los `ModernButton` usan Canvas, no ttk.Button. Asegúrate de usar la clase correcta:
```python
from app.ui.components.financial_validator_panel_v2 import ModernButton
btn = ModernButton(parent, text="Click", command=callback)
```

### Problema: Imports fallan
**Solución:** Verifica que estés en la raíz del proyecto:
```bash
cd H:\dropshipping_intelligence_suite
python test_jack_ui.py
```

---

## 🚀 Roadmap

### ✅ Completado
- [x] Sistema de design tokens neon
- [x] Componentes premium (Button, Card, Entry, Sidebar)
- [x] Panel Validador rediseñado
- [x] Estilos globales ttk
- [x] Documentación completa

### 🔄 En Progreso
- [ ] Dashboard con charts glassmorphism
- [ ] Animaciones con PIL para glow effects reales
- [ ] Modal dialogs premium

### 📋 Próximamente
- [ ] Rediseño de todos los paneles
- [ ] Loading states animados
- [ ] Toast notifications neon
- [ ] Exportar como tema standalone

---

## 📖 Referencias

- **Inspiración**: [@Itssssss_Jack](https://www.youtube.com/@Itssssss_Jack) YouTube Channel
- **Glassmorphism**: [CSS Tricks - Glassmorphism](https://css-tricks.com/glassmorphism/)
- **Neon UI**: Figma/Dribbble neon design kits
- **Material Design 3**: Elevation and shadows

---

## 📝 Changelog

### v3.0.0 (2026-10-31)
- 🎨 **Rediseño completo** Jack-Style UI/UX
- ✨ **Nuevos componentes**: ModernButton, GlassCard, ModernEntry
- 🔮 **Sidebar glassmorphism** con collapse
- 💎 **Panel Validador** rediseñado desde cero
- 🌟 **Sistema de estilos** ttk completo
- 📚 **Documentación** extensa con ejemplos

### v2.0.x (Anterior)
- ⚙️ Sistema base con ttk estándar
- 🎨 Tema oscuro básico
- 📊 Panel Validador funcional

---

**Versión**: 3.0.0  
**Última actualización**: 2026-10-31  
**Autor**: GEM OS Development Team  
**Licencia**: Propietario

💎 **Hecho con ❤️ y mucho neon cyan** 🔵
