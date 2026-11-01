# Skill: Generar Imagen de Producto con Fondo Removido

**ID:** `generar_imagen_producto`
**Versión:** 1.0.0
**Agente responsable:** `@gem-orchestrator-core`
**Propósito:** A partir de la URL o archivo de imagen del proveedor, generar una imagen profesional de producto con fondo blanco/transparente lista para Shopify, usando Claude Design (claude.ai) o APIs de background removal.

---

## 1. Pipeline de Generación

```
Imagen original (proveedor)
        ↓
[Paso 1] Evaluación de calidad
        ↓
[Paso 2] Remoción de fondo (elegir método según disponibilidad)
        ↓
[Paso 3] Composición final (fondo blanco o transparente)
        ↓
[Paso 4] Optimización WebP para Shopify
        ↓
Imagen lista → assets/img/producto-hero.webp
```

---

## 2. Métodos de Remoción de Fondo (por orden de calidad)

### Método A — Claude Artifacts (GRATUITO, mejor calidad)

**Cuándo usar:** cuando tienes acceso a Claude con vision y la imagen tiene contornos definidos.

1. Subir la imagen al chat de Claude
2. Prompt:
```
Analiza esta imagen de producto. Genera código SVG o HTML+CSS que muestre 
el producto con fondo blanco #FFFFFF limpio, eliminando el fondo original.
Si el fondo ya es blanco o neutro, optimiza el contraste del producto.
Output: imagen PNG base64 embebida en HTML, tamaño 800x800px, 
fondo blanco puro, producto centrado con 10% de padding.
```

### Método B — remove.bg API (mejor calidad automática)

**Costo:** $0.20/imagen en plan de pago | 50 gratis/mes en free tier

```python
import httpx, base64, os

def remover_fondo_removebg(imagen_path: str, output_path: str) -> dict:
    """
    Usa remove.bg API para eliminar el fondo.
    Requiere: REMOVEBG_API_KEY en .env
    """
    api_key = os.getenv("REMOVEBG_API_KEY")
    if not api_key:
        return {"error": "DATA_GAP: REMOVEBG_API_KEY no configurado"}

    with open(imagen_path, "rb") as f:
        response = httpx.post(
            "https://api.remove.bg/v1.0/removebg",
            headers={"X-Api-Key": api_key},
            files={"image_file": f},
            data={"size": "auto", "format": "png", "bg_color": "ffffff"}
        )

    if response.status_code == 200:
        with open(output_path, "wb") as out:
            out.write(response.content)
        return {"status": "OK", "output": output_path}
    else:
        return {"status": "ERROR", "detail": response.json()}
```

### Método C — Pillow + rembg (LOCAL, GRATIS, sin API)

```python
# Instalar: pip install rembg pillow
from rembg import remove
from PIL import Image
import io

def remover_fondo_local(imagen_path: str, output_path: str) -> dict:
    """
    Remoción local usando rembg (U2Net model).
    Sin costo. Requiere ~200MB de descarga del modelo (primera vez).
    """
    with open(imagen_path, "rb") as f:
        imagen_bytes = f.read()

    resultado = remove(imagen_bytes)  # PNG con transparencia

    # Añadir fondo blanco
    img = Image.open(io.BytesIO(resultado)).convert("RGBA")
    fondo = Image.new("RGBA", img.size, (255, 255, 255, 255))
    fondo.paste(img, mask=img.split()[3])
    fondo.convert("RGB").save(output_path, "PNG", optimize=True)

    return {"status": "OK", "output": output_path}
```

### Método D — Canva Background Remover (UI manual)
Para usuarios sin Python:
1. Subir imagen a canva.com
2. Seleccionar imagen → "Editar imagen" → "Quitar fondo"
3. Descargar PNG transparente
4. Subir a Shopify

---

## 3. Conversión a WebP para Shopify

Después de remover el fondo, convertir a WebP optimizado:

```python
from PIL import Image

def convertir_a_webp(input_path: str, output_path: str, quality: int = 85) -> dict:
    """
    Convierte PNG a WebP optimizado para Shopify.
    Target: < 200KB para imágenes de producto.
    """
    img = Image.open(input_path)

    # Asegurar fondo blanco (no transparencia en Shopify)
    if img.mode in ("RGBA", "LA"):
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        fondo.paste(img, mask=img.split()[-1])
        img = fondo

    # Redimensionar a 2048x2048 (máximo Shopify recomendado)
    img.thumbnail((2048, 2048), Image.LANCZOS)

    img.save(output_path, "WebP", quality=quality, method=6)

    size_kb = os.path.getsize(output_path) / 1024
    return {
        "status": "OK",
        "output": output_path,
        "size_kb": round(size_kb, 1),
        "advertencia": "Imagen > 200KB — reducir quality" if size_kb > 200 else None
    }
```

---

## 4. Composiciones Adicionales para Shopify

### 4.1 Imagen lifestyle (producto en contexto)
Prompt para Claude:
```
Genera una imagen HTML/CSS que muestre [PRODUCTO] en un entorno lifestyle de [NICHO].
Fondo: escena minimalista [descripción]. Producto centrado, iluminación natural.
Dimensiones: 1200x1200px. Sin texto en la imagen.
```

### 4.2 Imagen de variantes (colores)
```python
def generar_variantes_color(imagen_base_path: str, colores: list[str]) -> list[dict]:
    """
    Genera una variante de imagen por cada color disponible.
    Usa PIL para recolorizar mascara del producto.
    """
    from PIL import Image, ImageOps
    resultados = []

    img_base = Image.open(imagen_base_path).convert("RGBA")

    for color_hex in colores:
        # Extraer máscara del producto (canal alpha)
        r, g, b = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        mascara = img_base.split()[3]

        variante = Image.new("RGBA", img_base.size, (r, g, b, 255))
        variante.putalpha(mascara)

        output = f"assets/img/producto-{color_hex.lstrip('#')}.webp"
        variante.convert("RGB").save(output, "WebP", quality=85)
        resultados.append({"color": color_hex, "imagen": output})

    return resultados
```

### 4.3 Pack de imágenes Shopify (estructura completa)
```
assets/img/
  producto-hero.webp         → imagen principal (fondo blanco)
  producto-detalle-1.webp    → detalle 1 (zoom feature)
  producto-detalle-2.webp    → detalle 2 (medidas/escala)
  producto-lifestyle.webp    → imagen en contexto real
  producto-blanco.webp       → variante color (si aplica)
  producto-negro.webp        → variante color (si aplica)
```

---

## 5. Reglas Inmutables

| Regla | Valor |
|-------|-------|
| Fondo imagen principal Shopify | Blanco puro #FFFFFF |
| Resolución mínima | 800×800px |
| Resolución recomendada | 2048×2048px |
| Formato final | WebP (PNG como fallback) |
| Tamaño máximo | 200KB por imagen |
| Sin texto en imagen | Shopify lo prohíbe en imagen principal |
| Sin marcas de agua del proveedor | Editar o reemplazar imagen |

---

## 6. Variables de Entorno Necesarias

```
REMOVEBG_API_KEY=<tu_key>   # Opcional (50 gratis/mes)
```

Si no tienes la key → usar Método C (local con rembg) o Método D (Canva manual).

---

## 7. Integración con Pipeline GEM OS

```
clasificar_producto (HOT/WARM)
        ↓
redactar_ficha_shopify (genera specs)
        ↓
generar_imagen_producto (este skill)  ← AQUÍ
        ↓
estructurar_landing (embedding imagen en AIDA)
        ↓
Shopify admin → subir producto completo
```

---

*Fin del procedimiento. Versión 1.0.0 — GEM OS*
