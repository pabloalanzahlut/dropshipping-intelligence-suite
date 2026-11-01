# Spline 3D Hero — Integración para Dropshipping

Añadir un hero 3D con Spline en webs de producto. Uso **opt-in únicamente**: solo cuando el producto tiene un wow-factor visual alto (gadgets, accesorios tech, joyería, lifestyle). Para consumibles, ropa básica o nicho precio-bajo → usar hero estático con parallax estándar.

---

## Cuándo usar Spline

| Nicho | ¿Usar Spline? | Alternativa |
|-------|--------------|-------------|
| Gadget / tech / iluminación | ✅ Sí | — |
| Joyería / reloj / lifestyle premium | ✅ Sí | — |
| Ropa básica / consumible | ❌ No | Parallax imagen |
| Precio < $20 (margen bajo) | ❌ No | CSS gradient animated |
| Mobile first (>70% tráfico móvil) | ⚠️ Con fallback | Canvas 2D fallback |

---

## Integración (sin npm, sin build step)

### HTML — Añadir en `<head>` con cache-buster
```html
<script
  type="module"
  src="https://unpkg.com/@splinetool/viewer@1.9.27/build/spline-viewer.js?v=20261101"
  defer
></script>
```

**Importante:** Este es el único caso donde se permite `type="module"` en el skill — el viewer de Spline es un Web Component de terceros que lo requiere internamente. El código de GEM OS propio sigue siendo IIFE.

### HTML — Hero Section
```html
<section class="hero hero--spline" id="hero">
  <!-- Fallback visible antes de que cargue Spline (obligatorio) -->
  <div class="hero__fallback" aria-hidden="true">
    <img
      src="assets/img/producto-hero.webp?v=20261101"
      alt=""
      loading="eager"
      width="1200"
      height="800"
    />
  </div>

  <!-- Spline viewer (reemplaza al fallback al cargar) -->
  <spline-viewer
    url="https://prod.spline.design/TU_SCENE_ID/scene.splinecode"
    class="hero__spline"
    loading="lazy"
  ></spline-viewer>

  <!-- Copy encima del 3D — siempre hardcoded en HTML -->
  <div class="hero__copy">
    <h1 class="hero__title"><!-- título SEO aquí --></h1>
    <p class="hero__sub"><!-- hook de dolor aquí --></p>
    <a href="#comprar" class="btn-cta">Ver producto</a>
  </div>
</section>
```

### CSS — Stacking y fallback
```css
.hero--spline {
  position: relative;
  min-height: 100svh;
  display: grid;
  place-items: center;
  overflow: hidden;
}

/* Fallback: visible por defecto */
.hero__fallback {
  position: absolute;
  inset: 0;
  z-index: 0;
  transition: opacity 0.6s ease;
}
.hero__fallback img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Spline: por encima del fallback al cargar */
.hero__spline {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  opacity: 0;
  transition: opacity 0.8s ease;
}

/* Copy: siempre encima de todo */
.hero__copy {
  position: relative;
  z-index: 10;
  text-align: center;
  padding: 2rem;
}

/* Cuando Spline carga → ocultar fallback */
.hero--spline-loaded .hero__fallback { opacity: 0; pointer-events: none; }
.hero--spline-loaded .hero__spline  { opacity: 1; }

/* Mobile: deshabilitar Spline si reduce-motion o pantalla estrecha */
@media (max-width: 768px), (prefers-reduced-motion: reduce) {
  .hero__spline { display: none; }
  .hero__fallback { opacity: 1 !important; }
}
```

### JS — Detectar carga y aplicar clase (IIFE, no module)
```javascript
(function initSplineHero() {
  var hero = document.querySelector('.hero--spline');
  var viewer = hero && hero.querySelector('spline-viewer');
  if (!viewer) return;

  // Tiempo máximo de espera antes de mostrar fallback permanente
  var TIMEOUT = 5000;
  var timer = setTimeout(function() {
    // Spline tardó demasiado → quedarse con fallback
    viewer.style.display = 'none';
  }, TIMEOUT);

  viewer.addEventListener('load', function() {
    clearTimeout(timer);
    hero.classList.add('hero--spline-loaded');
  });

  viewer.addEventListener('error', function() {
    clearTimeout(timer);
    viewer.style.display = 'none';
  });
})();
```

---

## Cómo crear la escena Spline para dropshipping

### Opción A — Usar plantilla pública de Spline
1. Ir a [spline.design/community](https://spline.design/community)
2. Buscar: "product 3d floating" o "hero gadget 3d"
3. Duplicar la escena → reemplazar el modelo 3D con el del producto
4. Publicar → copiar URL `scene.splinecode`

### Opción B — Pedir a Claude que genere la escena (via Spline AI)
```
Prompt para Spline AI:
"Create a 3D floating product scene for [nombre producto].
Background: dark gradient (#0a0a0a to #1a1a2e).
Product: [descripción del producto].
Animation: slow floating rotation (4s loop).
Lighting: warm rim light from the right + cool fill from left.
No text in the scene."
```

### Opción C — Three.js fallback (sin Spline, 100% local)
Para proyectos que necesitan zero-dependency 3D:
```javascript
// Requiere three.min.js en lib/
// Ver reference/03-effects-catalog.md § 4.1 WebGL Canvas
```

---

## Gotchas críticos

1. **Nunca** colocar texto importante dentro de la escena Spline — si falla la carga, el texto desaparece.
2. **Siempre** incluir fallback de imagen (`hero__fallback`) visible por defecto.
3. El viewer Spline carga ~200KB JS. Si PageSpeed es prioritario → usar Three.js local o CSS animation.
4. En móvil: Spline consume CPU elevada → deshabilitar por defecto en `max-width: 768px`.
5. La URL de la escena (`scene.splinecode`) debe ser pública. Escenas privadas dan 403.

---

## Integración con Archetype de Dropshipping

Para el archetype **Glassmorphism Modern** (el más común en productos tech dropshipping):
- Hero: Spline 3D + glassmorphism overlay en el copy
- Section 2: Benefits con scroll reveal (sin 3D)
- Section 3: Specs técnicas con layout grid limpio
- Section 4: Trust badges + CTA final

El 3D solo en el hero → el resto del funnel: velocidad de conversión primero.

---

*Ref: Jack Roberts @Itssssss_Jack — AntiGravity + Spline 3D | GEM OS v2.0*
