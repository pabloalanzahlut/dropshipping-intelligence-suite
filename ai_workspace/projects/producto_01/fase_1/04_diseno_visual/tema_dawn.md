# CONFIGURACIÓN TEMA DAWN — [MARCA]
> Shopify Admin → Online Store → Themes → Dawn → Customize

---

## Por qué Dawn (metodología Adrián Sáenz)

Dawn es el tema gratuito oficial de Shopify 2.0. Adrián Sáenz lo recomienda para empezar porque:
- Carga rápida (Core Web Vitals altos → mejor SEO y conversión)
- Compatible con todas las apps de dropshipping
- Secciones arrastrables sin código
- Se ve profesional con la configuración correcta

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

> En Dawn: ir a Typography → Headings → Browse free fonts → buscar "Playfair Display"
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

Dawn viene con secciones de demo. **Borrar antes de añadir las nuestras:**
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
