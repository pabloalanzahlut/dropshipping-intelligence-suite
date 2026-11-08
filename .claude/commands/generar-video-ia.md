# Skill: Generar Video TikTok con IA (Higgsfield)

Genera un video de producto para TikTok Ads usando **Higgsfield AI** — sin filmar, sin equipo.

## Qué necesito del usuario:
1. **URL de imagen del producto** (foto del proveedor o Shopify CDN)
2. **Nombre del producto**
3. **Hook visual** (el conflicto/problema de los primeros 3 segundos)
4. **Duración**: 5 o 10 segundos (default: 5s para TikTok Ads)

Si falta alguno → `DATA_GAP_REQUEST`.

---

## Proceso multi-IA (3 pasos):

### PASO 1 — Gemini Vision analiza la imagen
```python
from app.services.gemini_vision import analyze_product_image
specs = analyze_product_image(image_url, task="extract_specs")
```
Extrae: material, categoría, wow factor, restricciones (baterías litio).

### PASO 2 — Claude construye el motion prompt
Usando los specs extraídos + el hook del usuario:
```python
from app.services.higgsfield_client import build_motion_prompt
prompt = build_motion_prompt(producto=nombre, hook_visual=hook)
```

### PASO 3 — Higgsfield genera el video
```python
from app.services.higgsfield_client import generate_product_video
video_url = generate_product_video(
    image_url=url_imagen,
    motion_prompt=prompt,
    duration_seconds=5,
    aspect_ratio="9:16"
)
```

---

## Output final:

```
🎬 VIDEO GENERADO

Producto:     [nombre]
Duración:     5s | 9:16 vertical
Video URL:    https://...

📋 Specs detectados por Gemini Vision:
  - Material: [extraído de imagen]
  - Categoría: [nicho]
  - Restricciones: [OK / ALERTA]

🎯 Motion prompt usado:
  "[prompt enviado a Higgsfield]"

✅ Listo para subir a TikTok Ads Manager
```

---

## Configuración requerida (.env):
```
HIGGSFIELD_API_KEY=hf-...    # higgsfield.ai → Dashboard → API Keys
OPENROUTER_API_KEY=sk-or-... # ya configurado (Gemini Vision lo reutiliza)
```

## Alternativa sin API Higgsfield:
Si no tienes clave de Higgsfield, el skill entrega el motion prompt listo para usar manualmente en higgsfield.ai (plan gratuito disponible) o en Runway ML / Kling AI.
