# CONFIGURACIÓN DE TEMA — [MARCA]
> AVISO (corregido 2026-11-11): este archivo se escribió para Dawn, pero el curso (`Q4Ykcwh5Osc` 00:35:31) usa el tema gratuito **Sense**, que además ya es el tema activo en la tienda. **No instalar Dawn.** Los ajustes de abajo (colores, tipografía, logo, header, carrito) existen en cualquier tema 2.0, pero los nombres exactos pueden variar en Sense: verificar en el editor.
> Shopify Admin → Online Store → Themes → Sense → Customize

---

## Tema: Sense (el del curso)

En el vídeo (`Q4Ykcwh5Osc` 00:35:31) se elige entre los temas gratuitos de la Theme Store y se publica **Sense**. Flujo del curso: nombre y logo (00:36–00:59) → 2 esquemas de color (01:00:12) → bloques `Liquid personalizado` (01:04:12) → menú (03:16:37). Dawn no aparece en el vídeo.

---

## Configuración paso a paso en el editor

### 1. Colors (Theme Settings → Colors)

Pegar los valores exactos de `paleta_marca.md`:

| Setting | Valor |
|---|---|
| Colors / Solid button label | `[COLOR_BOTONES_TEXTO]` → ej. #FFFFFF |
| Colors / Buttons | `[COLOR_PRIMARIO]` |
| Colors / Secondary button label | `[COLOR_PRIMARIO]` |
| Colors / Outline button | `[COLOR_PRIMARIO]` |
| Colors / Link | `[COLOR_PRIMARIO]` |
| Colors / Text | #1A1A1A (negro suave — no puro negro) |
| Colors / Background | #FFFFFF |
| Colors / Secondary background | #F8F8F8 (gris muy claro para secciones alternas) |

---

### 2. Typography (Theme Settings → Typography)

| Setting | Valor | Por qué |
|---|---|---|
| Headings | **Playfair Display** | Autoridad, modernidad, se ve premium |
| Body text | **DM Sans** | Legibilidad perfecta en móvil |

> En el editor: ir a Typography → Headings → Browse free fonts → buscar "Playfair Display"
> Para body: buscar "DM Sans"

**Tamaños base:**
- Heading scale: 1.3
- Body font size: 16px (default)

---

### 3. Layout (Theme Settings → Layout)

| Setting | Valor |
|---|---|
| Page width | 1200px (default) |
| Content padding | 20px (default) |
| Corner radius (botones) | 4px (aspecto moderno, no redondo) |

---

### 4. Favicon y Logo

- Logo: subir versión en PNG con fondo transparente — máximo 400px ancho
- Favicon: 32×32 px, PNG — usar símbolo del logo solamente (no texto)

**Dónde subir:**
- Logo → Theme Settings → Logo → Select image
- Favicon → Theme Settings → Favicon → Select image

---

### 5. Secciones del Header (Header section)

| Setting | Valor |
|---|---|
| Logo width | 150px |
| Enable sticky header | ✅ Activado (el menú se queda arriba al hacer scroll) |
| Show line separator | ❌ Desactivado |
| Country/region selector | ❌ Desactivado (a menos que tengas multi-currency) |

---

### 6. Cart (Theme Settings → Cart)

| Setting | Valor |
|---|---|
| Cart type | **Drawer** (se abre desde la derecha — mejor UX móvil) |
| Show vendor | ❌ Desactivado (no revelar el proveedor) |

---

### 7. Secciones a eliminar del Home por defecto

El tema trae secciones de demo. **Borrar antes de añadir las nuestras:**
- "Rich text" de demo con texto genérico
- "Image banner" con imagen de placeholder
- "Featured collection" con colección vacía

Dejar solo: Header → (nuestras secciones del homepage) → Footer

---

## Checklist de publicación

- [ ] Colores aplicados (coinciden con `paleta_marca.md`)
- [ ] Tipografías configuradas
- [ ] Logo y favicon subidos
- [ ] Header sticky activado
- [ ] Cart drawer activado
- [ ] Secciones demo eliminadas
- [ ] Vista móvil revisada (usar el botón de móvil en el editor)
