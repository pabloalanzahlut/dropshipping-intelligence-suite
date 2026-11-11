# ✂️ CÓMO EDITAR CONTENIDO — Workflow CapCut

> ⚠️ **BORRADOR — no extraído del vídeo del curso.** Los títulos de capítulo y timestamps son reales; el contenido es conocimiento general. Umbrales y cifras sin verificar. Pendiente de reconstruir desde la transcripción en la KB (`/ingerir_transcripcion_kb`).
> Curso Adrián Sáenz `Q4Ykcwh5Osc 15:49:01` | GEM OS v3.0
> Plataformas: TikTok + Instagram Reels + Facebook Reels

---

## 🛠️ HERRAMIENTAS

| Herramienta | Uso | Coste |
|------------|-----|-------|
| **CapCut** (principal) | Edición completa, subtítulos IA, efectos | Gratis |
| **CapCut PC** | Edición más precisa con teclado | Gratis |
| **Remove.bg** | Fondo transparente en imágenes estáticas | 50/mes gratis |
| **Canva** | Stories, posts estáticos | Gratis |

---

## 📱 WORKFLOW CAPCUT COMPLETO (paso a paso)

### PASO 1 — Importar video
```
CapCut → Nuevo proyecto → Importar
→ Seleccionar video MP4 (de Higgsfield o grabado)
→ Formato de exportación: 9:16 vertical
→ Resolución: 1080×1920
```

### PASO 2 — Cortar y ritmo
- [ ] Eliminar los primeros 0.5s si el inicio es estático (el algoritmo mide retención desde el frame 1)
- [ ] Duración objetivo: 7-15s TikTok | 15-30s Reels
- [ ] Velocidad: Normal (1×). Solo aumentar si hay demostración lenta
- [ ] Transiciones: Ninguna o "fade" suave entre clips (no efectos de barrido llamativos)

### PASO 3 — Subtítulos automáticos (OBLIGATORIO)
```
CapCut → Texto → Auto-subtítulos
→ Idioma: Español (o el del mercado objetivo)
→ Estilo: "Bold" o "Negrita" — máx. 2-3 palabras por frame
→ Posición: Tercio inferior del video (nunca sobre el producto)
→ Color: Blanco con sombra negra (legible en cualquier fondo)
```
✅ Los subtítulos ayudan a quien ve sin sonido (efecto no medido aquí; validar con métricas propias)

### PASO 4 — Música y audio

**Si el video ya tiene audio (Higgsfield genera audio):**
- [ ] Bajar el volumen del audio original al 60-80%
- [ ] Añadir música de fondo desde biblioteca CapCut al 20-30%

**Si el video no tiene audio:**
- [ ] Buscar en CapCut: "trending [año actual]" o "motivacional producto"
- [ ] Pista sin letra para no competir con el VO o los subtítulos
- [ ] Ajustar el inicio de la música al beat drop (si lo hay)

**Para el video de Facebook (mismo audio, diferente distribución):**
- [ ] Facebook penaliza canciones con copyright más que TikTok
- [ ] Usar solo audio de la biblioteca CapCut marcado como "libre de derechos"

### PASO 5 — Texto y efectos visuales

**Hook de texto (0-2s):**
```
Texto grande, centrado, sin fondo
Efecto: "Pop" o "typewriter"
Duración: 1.5-2 segundos máximo
```

**Precio / CTA (últimos 3s):**
```
Texto: "{{PRECIO_VENTA}}€ | Envío: {{ENVIO_REAL}}"
Posición: inferior centrado
Fondo: rectángulo negro semitransparente
Tamaño: legible sin zoom
```

**Efectos a EVITAR:**
- ❌ Transiciones de zoom excesivo
- ❌ Partículas o confeti (spam visual)
- ❌ Música muy rápida que no encaje con el producto
- ❌ Texto de más de 4 líneas en pantalla simultáneamente

### PASO 6 — Revisión de retención
```
CapCut → Preview completo → Verificar:
[ ] ¿Se entiende el producto en los primeros 3s sin sonido?
[ ] ¿El CTA aparece en los últimos 3s?
[ ] ¿Los subtítulos son legibles en pantalla pequeña?
[ ] ¿La música no tapa la voz o los sonidos del producto?
```

### PASO 7 — Exportación

**Para TikTok:**
```
Exportar → 1080p → 30fps → Sin marca de agua CapCut
(TikTok penaliza la marca de agua de CapCut)
```

**Para Instagram Reels:**
```
Mismo archivo que TikTok (1080×1920, sin marca de agua)
```

**Para Facebook Reels:**
```
Mismo archivo. Si > 60s: recortar a 60s para distribución máxima.
Facebook acepta hasta 90s pero el alcance orgánico baja notablemente después de 60s.
```

---

## ⚡ WORKFLOW RÁPIDO (versión express — 10 minutos)

```
1. Importar video Higgsfield (MP4)           → 1 min
2. Cortar a duración objetivo                → 2 min
3. Auto-subtítulos CapCut                    → 2 min (IA lo hace sola)
4. Añadir música de biblioteca               → 1 min
5. Texto hook + CTA                          → 2 min
6. Preview final                             → 1 min
7. Exportar sin marca de agua                → 1 min
                                    TOTAL: ~10 min/video
```

---

## 📂 ESTRUCTURA DE ARCHIVOS (guardar en el proyecto)

```
ai_workspace/projects/producto_01/assets/
├── raw/
│   └── video_higgsfield_v1.mp4         ← original sin editar
├── edited/
│   ├── tiktok_v1_final.mp4             ← listo para TikTok/Instagram
│   └── facebook_v1_final.mp4           ← versión adaptada Facebook
└── thumbnails/
    └── thumb_v1.jpg                    ← portada del video (opcional)
```
