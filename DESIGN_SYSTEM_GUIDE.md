# 🎨 Design System Guide — GEM OS Premium v3.0

## 📐 Guía Completa de Diseño

### Secciones
1. [Colores](#colores)
2. [Tipografía](#tipografía)
3. [Espaciado](#espaciado)
4. [Componentes](#componentes)
5. [Animaciones](#animaciones)
6. [Ejemplos](#ejemplos)

---

## 🎨 Colores

### Paleta Primaria

#### Indigo (Acción Principal)
```
Light:   #818cf8  (para hover)
Base:    #6366f1  (botones, links, acentos)
Dark:    #4f46e5  (active, hover)
Darker:  #4338ca  (pressed)
```

**Uso:**
- Botones principales
- Links de navegación
- Acentos en tarjetas
- Indicadores activos

#### Púrpura (Acción Secundaria)
```
Light:   #a78bfa
Base:    #8b5cf6
Dark:    #7c3aed
```

**Uso:**
- Botones secundarios
- Acentos alternos
- Estados hover

### Colores Semánticos

#### Verde (Éxito)
```
#10b981 - Validaciones exitosas
#059669 - Hover
#047857 - Active
```
**Uso:** Checkmarks, validaciones OK, tendencias positivas

#### Rojo (Error)
```
#ef4444 - Alertas, rechazos
#dc2626 - Hover
#b91c1c - Active
```
**Uso:** Errores, validaciones rechazadas, advertencias críticas

#### Ámbar (Advertencia)
```
#f59e0b - Advertencias moderadas
#d97706 - Hover
#b45309 - Active
```
**Uso:** Advertencias, items pendientes, información importante

#### Azul (Información)
```
#3b82f6 - Información general
#1d4ed8 - Hover
#1e40af - Active
```
**Uso:** Tips, información, datos neutros

### Neutros (Sistema Dark)

#### Fondos
```
Primary:   #0f0f0f  - Background ultra-oscuro (fatiga ocular mínima)
Secondary: #1a1a1a  - Sidebar, headers
Tertiary:  #252525  - Hover states, borders
Card:      #2d2d2d  - Card backgrounds
Border:    #3d3d3d  - Separadores, bordes
```

#### Textos
```
Primary:   #ffffff     - Texto principal
Secondary: #b0b0b0     - Texto secundario (labels)
Tertiary:  #888888     - Texto deshabilitado
Disabled:  #666666     - Texto deshabilitado (más oscuro)
```

### Gradientes Recomendados

```python
# Card Success (Verde)
gradient_success = {
    'start': '#1a2e1a',
    'end': '#0d1a0d',
    'border': '#10b981',
    'accent': '#4ade80',
}

# Card Primary (Indigo)
gradient_primary = {
    'start': '#1a1a2e',
    'end': '#0f0f1a',
    'border': '#6366f1',
    'accent': '#818cf8',
}

# Card Warning (Ámbar)
gradient_warning = {
    'start': '#2e2a1a',
    'end': '#1a1510',
    'border': '#f59e0b',
    'accent': '#fbbf24',
}
```

---

## 📝 Tipografía

### Escala Tipográfica

```
Display Large:    32pt bold   (títulos principales de página)
Display Medium:   28pt bold   (títulos de sección)
Display Small:    24pt bold   (títulos destacados)

Heading Large:    20pt bold   (títulos de card)
Heading Medium:   16pt bold   (subtítulos)
Heading Small:    14pt bold   (labels importantes)
Heading XS:       12pt bold   (labels secundarios)

Body Large:       16pt normal (párrafos)
Body Medium:      14pt normal (descripción)
Body Small:       12pt normal (texto auxiliar)
Body XS:          11pt normal (metadata)

Mono Large:       12pt mono   (código)
Mono Medium:      11pt mono   (código pequeño)
Mono Small:       10pt mono   (datos tabulares)
Mono XS:          9pt mono    (inline code)
```

### Familias de Fuentes

```
Heading Font:     "Inter" o "Segoe UI"
Body Font:        "Inter" o "Segoe UI"
Mono Font:        "Courier New" o "Consolas"
```

### Pesos

```
Light:        300
Normal:       400
Medium:       500
Semi-Bold:    600
Bold:         700
```

### Ejemplos en Contexto

```
┌─────────────────────────────────────────┐
│ 📊 Dashboard Analytics    (18pt bold)   │  Título principal
│ Última actualización: 23:04:03  (9pt)   │  Metadata
├─────────────────────────────────────────┤
│ ✅ Últimas Validaciones   (11pt bold)   │  Sección
│                                         │
│ SKU    PVP     Margen   Status   (10pt) │  Encabezados tabla
│ ───────────────────────────────────    │
│ SKU1   $90     68%      ✓        (10pt) │  Datos tabla
│ SKU2   $150    75%      ✓               │
└─────────────────────────────────────────┘
```

---

## 📐 Espaciado

### Sistema de Espaciado (8px base)

```
XS:   4px    (gaps mínimos)
SM:   8px    (espacios pequeños)
MD:   12px   (espacios medios)
LG:   16px   (espacios grandes)
XL:   24px   (espacios extra grandes)
2XL:  32px   (espacios máximos)
```

### Aplicaciones

```
Padding interno de cards:       LG (16px)
Padding de botones:            SM/MD (8-12px)
Espaciado entre componentes:   MD/LG (12-16px)
Espaciado entre secciones:     XL (24px)
Margin de bordes:              LG (16px)
Gap entre grid items:          SM (8px)
```

### Ejemplo

```python
# Card con padding y gap
card = tk.Frame(parent, bg=COLOR_BG_CARD)
card.pack(fill=tk.BOTH, expand=True, 
          padx=SPACING.lg,      # 16px horizontal
          pady=SPACING.md)      # 12px vertical

# Interior del card
content = tk.Frame(card, bg=COLOR_BG_CARD)
content.pack(fill=tk.BOTH, expand=True,
             padx=SPACING.md,   # 12px padding interno
             pady=SPACING.md)

# Items dentro con gap
label.pack(pady=(0, SPACING.sm))  # Espacio después del label
value.pack(pady=(SPACING.sm, 0))  # Espacio antes del value
```

---

## 🧩 Componentes

### KPI Card

```
╔════════════════════════════════╗
║ ▓▓ Borde superior (3-4px)      ║  Color según semántica
║ 📦 Título                       ║  11pt bold, gris
║ 245                            ║  22pt bold, color semántico
║ ↑ 82% OK                        ║  9pt, verde
╚════════════════════════════════╝
```

**Estructura:**
- Borde superior coloreado
- Icon + Title
- Valor grande
- Indicador de tendencia

### Botón Primario

```
[⚡ Sincronizar]  ← Fondo Indigo, hover Púrpura
```

**Estados:**
- Normal: #6366f1
- Hover: #8b5cf6
- Active: #4f46e5
- Disabled: #666666

### Tabla

```
╔═════════════════════════════════════════╗
║ ✅ Últimas Validaciones                 ║  Header con color
├─────────────────────────────────────────┤
║ SKU    │ PVP    │ Margen │ Status      ║  Encabezados
├─────────────────────────────────────────┤
║ SKU1   │ $90    │ 68%    │ ✓           ║  Fila par #1a1a1a
║ SKU2   │ $150   │ 75%    │ ✓           ║  Fila impar #252525
║ SKU3   │ $60    │ 65%    │ ✗           ║  Fila par
╚═════════════════════════════════════════╝
```

**Styling:**
- Even rows: #1e1e1e
- Odd rows: #252525
- Hover: #3d3d3d
- Sin bordes pesados

---

## ⚡ Animaciones

### Velocidades

```
Fast:    150ms cubic-bezier(0.4, 0, 0.2, 1)
Base:    250ms cubic-bezier(0.4, 0, 0.2, 1)
Slow:    350ms cubic-bezier(0.4, 0, 0.2, 1)
```

### Transiciones

```
Color:       150ms
Position:    250ms
Size:        250ms
Opacity:     150ms
Transform:   200ms
```

### Ejemplos

```python
# Hover en botón
btn.bind('<Enter>', lambda e: btn.config(bg=COLOR_HOVER))
btn.bind('<Leave>', lambda e: btn.config(bg=COLOR_NORMAL))

# Transición de valor (animada)
from app.ui.components.animations import AnimatedValue
anim = AnimatedValue(label, steps=12, interval=25)
anim.animate(new_value)  # Anima de valor actual a nuevo_value
```

---

## 🎯 Ejemplos

### Ejemplo 1: Card KPI Premium

```python
# Crear card KPI
card = tk.Frame(parent, bg=COLOR_BG_CARD,
                highlightthickness=1,
                highlightbackground=COLOR_BORDER)

# Borde superior coloreado
top_bar = tk.Frame(card, bg=COLOR_SUCCESS, height=3)
top_bar.pack(fill=tk.X)

# Contenido
content = tk.Frame(card, bg=COLOR_BG_CARD)
content.pack(fill=tk.BOTH, expand=True,
             padx=SPACING.md, pady=SPACING.md)

# Título
title = tk.Label(content, text="Productos Validados",
                font=FONT_BODY_SM, fg=COLOR_TEXT_SECONDARY,
                bg=COLOR_BG_CARD)
title.pack(anchor="w")

# Valor
value = tk.Label(content, text="245",
                font=(TYPOGRAPHY.heading_family, 22, "bold"),
                fg=COLOR_SUCCESS, bg=COLOR_BG_CARD)
value.pack(anchor="w", pady=(SPACING.md, 0))

# Tendencia
trend = tk.Label(content, text="↑ 82% OK",
                font=FONT_BODY_SM, fg=COLOR_SUCCESS,
                bg=COLOR_BG_CARD)
trend.pack(anchor="w", pady=(SPACING.sm, 0))
```

### Ejemplo 2: Botón Premium

```python
def create_button(parent, text, command, color=COLOR_PRIMARY):
    """Crear botón con hover effects."""
    btn = tk.Button(parent, text=text, command=command,
                   font=FONT_BODY_SM,
                   bg=color, fg=COLOR_TEXT_PRIMARY,
                   border=0, padx=SPACING.md, pady=SPACING.sm,
                   cursor="hand2", relief=tk.FLAT,
                   highlightthickness=0)
    
    def on_enter(e):
        new_color = lighten_color(color, 0.2)
        btn.config(bg=new_color)
    
    def on_leave(e):
        btn.config(bg=color)
    
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    
    return btn
```

### Ejemplo 3: Header Premium

```python
# Header container
header = tk.Frame(self, bg=COLOR_BG_SECONDARY, height=80)
header.pack(fill=tk.X, padx=0, pady=0)
header.pack_propagate(False)

# Contenido
header_inner = tk.Frame(header, bg=COLOR_BG_SECONDARY)
header_inner.pack(fill=tk.BOTH, expand=True,
                  padx=SPACING.lg, pady=SPACING.md)

# Lado izquierdo
left = tk.Frame(header_inner, bg=COLOR_BG_SECONDARY)
left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

title = tk.Label(left, text="📊 Dashboard Analytics",
                font=FONT_TITLE, fg=COLOR_TEXT_PRIMARY,
                bg=COLOR_BG_SECONDARY)
title.pack(side=tk.LEFT, anchor="w")

timestamp = tk.Label(left, text="Última actualización: 23:04:03",
                    font=FONT_BODY_SM, fg=COLOR_TEXT_TERTIARY,
                    bg=COLOR_BG_SECONDARY)
timestamp.pack(side=tk.LEFT, padx=SPACING.lg)

# Lado derecho (botones)
right = tk.Frame(header_inner, bg=COLOR_BG_SECONDARY)
right.pack(side=tk.RIGHT)

btn_sync = create_button(right, "⚡ Sincronizar",
                        command=on_sync, color=COLOR_PRIMARY)
btn_sync.pack(side=tk.LEFT, padx=SPACING.xs)

btn_refresh = create_button(right, "🔄 Actualizar",
                           command=on_refresh, color=COLOR_INFO)
btn_refresh.pack(side=tk.LEFT, padx=SPACING.xs)
```

---

## 📋 Checklist de Implementación

### Para Nuevos Componentes

- [ ] Usar colores de la paleta semántica
- [ ] Aplicar espaciado sistemático (4/8/12/16/24px)
- [ ] Tipografía jerárquica correcta
- [ ] Estados hover/active implementados
- [ ] Contraste adecuado (WCAG AA mínimo)
- [ ] Responsive en 1280x800 y 1920x1080
- [ ] Sin fuentes embebidas (usar sistema)
- [ ] Animaciones suaves (<300ms)

### Para Actualizaciones de Diseño

- [ ] Revisar paleta de colores
- [ ] Validar espaciado
- [ ] Probar en resoluciones distintas
- [ ] Verificar contraste de texto
- [ ] Testear estados interactivos
- [ ] Documentar cambios

---

## 🔗 Referencias

- **Sistema Base:** Material Design 3 + Modern SaaS
- **Inspiración Visual:** Figma, Linear, Stripe
- **Framework:** tkinter nativo (Python 3.8+)
- **Compatibilidad:** Dark theme primary

---

**Versión:** 3.0  
**Última actualización:** 2026-10-31  
**Estado:** ✅ Completo y Productivo
