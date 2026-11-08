# 🎥 CÓMO GRABAR / GENERAR CONTENIDO (SIN PRODUCTO FÍSICO)
> Curso Adrián Sáenz `Q4Ykcwh5Osc 15:36:33` | Adaptación: Videos con IA (Higgsfield)
> Plataformas: TikTok + Instagram Reels + Facebook Reels

---

## 🤖 ESTRATEGIA ACTUAL: VIDEOS CON IA (sin producto físico)

Dado que no hay producto físico disponible ahora, el flujo es:

```
Imagen del producto (proveedor/AliExpress)
    ↓
Gemini Vision → analiza specs y ángulos automáticamente
    ↓
Higgsfield AI → genera video TikTok 9:16 realista (sin filmar)
    ↓
CapCut → subtítulos + música + efectos
    ↓
Make.com → publica en TikTok / Instagram / Facebook
```

**Skill disponible:** `/generar-video-ia` → activa este pipeline automáticamente.

---

## 📐 ESPECIFICACIONES TÉCNICAS (aplican tanto a video real como IA)

| Parámetro | Valor |
|-----------|-------|
| Formato | Vertical 9:16 |
| Resolución mínima | 1080×1920 px |
| Duración óptima TikTok | 7-15 segundos (corto, > retención) |
| Duración óptima Reels | 15-30 segundos |
| Duración Facebook Reels | 15-60 segundos (máx. orgánico: 90s) |
| FPS | 30 mínimo, 60 ideal |
| Audio | Obligatorio (video sin sonido = penalización) |

---

## 🎬 ESTRUCTURA DEL VIDEO (aplica a todos los formatos)

### Si grabas tú mismo (cuando tengas producto)

**Iluminación:**
- [ ] Luz natural de frente (ventana) o ring light a 45°
- [ ] Sin sombras duras sobre el producto
- [ ] Fondo: liso blanco, negro o textura neutral (no pared con cuadros)

**Encuadre:**
- [ ] Producto ocupa 60-70% del frame
- [ ] Manos visibles si es producto de uso manual (humaniza el contenido)
- [ ] Regla de los tercios: producto en zona central o tercio superior

**Teléfono:**
- [ ] Estabilizador o trípode (evitar tiemblo)
- [ ] Grabar en 4K si el teléfono lo permite
- [ ] Limpiar el objetivo antes de grabar

**Ángulos recomendados por tipo de producto:**
| Tipo | Ángulo |
|------|--------|
| Gadget / tech | Frontal + macro de detalle clave |
| Hogar | 45° cenital + mano usando el producto |
| Belleza / cuidado | Espejo + resultado visible en piel |
| Fitness | Acción completa (antes → durante → después) |

---

## 🤖 FLUJO CON HIGGSFIELD (fase actual sin producto)

### Paso 1: Obtener imagen del producto
- Descargar imagen del proveedor (AliExpress, CJ Dropshipping, AutoDS)
- Remover fondo: usar `/generar-imagen-producto` o remove.bg
- Guardar en: `ai_workspace/projects/producto_01/assets/producto_sin_fondo.png`

### Paso 2: Activar análisis de imagen
```bash
# GEM OS skill
/generar-video-ia
# → Gemini Vision analiza la imagen
# → Genera prompt optimizado para Higgsfield
# → Higgsfield devuelve video MP4 9:16
```

### Paso 3: Outputs generados
- `assets/video_tiktok_hook.mp4` — versión hook (0-3s llamativo)
- `assets/video_tiktok_demo.mp4` — versión demostración completa
- `assets/video_facebook.mp4` — versión adaptada para Facebook (mismo contenido, posible corte)

---

## 🎨 RECURSOS DE AUDIO (TikTok / Instagram / Facebook)

| Plataforma | Dónde buscar audio | Criterio |
|-----------|-------------------|---------|
| TikTok | Creator Center → Biblioteca de sonidos | "Trending" en tu región |
| Instagram | Reels → Explorar audio → "Populares" | > 50K usos recientes |
| Facebook | Creator Studio → Biblioteca de sonidos | Colección Meta gratuita |

**Regla de oro:** No usar canciones con copyright → usar solo audio de la biblioteca nativa o audio original.

---

## 📋 CHECKLIST ANTES DE PUBLICAR CADA VIDEO

```
[ ] Formato 9:16 vertical
[ ] Duración correcta según plataforma (ver tabla arriba)
[ ] Audio añadido (no silencio)
[ ] Subtítulos añadidos (CapCut auto-subtitle o manualmente)
[ ] Hook visible en frame 1 (primeros 3 segundos)
[ ] Sin marca de agua de otra plataforma
[ ] Para Facebook: recortado o adaptado del TikTok (no copia exacta)
[ ] CTA en los últimos 3 segundos
[ ] Video exportado en 1080×1920 mínimo
```
