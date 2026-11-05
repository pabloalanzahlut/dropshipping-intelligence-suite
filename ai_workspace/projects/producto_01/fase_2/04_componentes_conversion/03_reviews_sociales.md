# Reviews Sociales (Clientes + Influencers)
> producto_01 · Fase 2 · Módulo 04
> Pegar en: página de producto (debajo de la ficha) y/o Home
> Equivale a: "Constructor de Reviews Clientes" + "Constructor de Reviews Influencers" (+ "con fotos") del documento complementario

---

> ⚠️ **Regla GEM OS — NO INVENTAR:** nunca fabricar testimonios, nombres, cifras o fotos de reviews. Si todavía no tienes reviews reales, deja el bloque fuera de la tienda hasta tenerlas (app de reviews de Shopify, o acuerdo real con un creador).

---

## 1. Reviews de clientes

```html
<section style="padding:40px 16px;">
  <h2 style="text-align:center; margin-bottom:24px;">Lo que dicen nuestros clientes</h2>
  <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:16px;">
    <div style="max-width:280px; border:1px solid #e5e5e5; border-radius:8px; padding:16px;">
      <div>⭐⭐⭐⭐⭐</div>
      <p style="font-size:14px; margin:8px 0;">"[TESTIMONIO_REAL_1]"</p>
      <p style="font-size:12px; opacity:.7;">— [NOMBRE_CLIENTE_1], [PAIS_CLIENTE_1]</p>
    </div>
    <!-- duplicar este bloque por cada review real que tengas -->
  </div>
</section>
```

---

## 2. Reviews de influencers (con o sin fotos)

```html
<section style="padding:40px 16px; background:[HEX_FONDO];">
  <h2 style="text-align:center; margin-bottom:24px;">Recomendado por creadores</h2>
  <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:16px;">
    <div style="max-width:260px; text-align:center;">
      <img src="[URL_FOTO_INFLUENCER_1]" alt="[NOMBRE_INFLUENCER_1]" style="width:100%; border-radius:8px; aspect-ratio:1/1; object-fit:cover;">
      <p style="font-size:14px; margin:8px 0;">"[CITA_INFLUENCER_1]"</p>
      <p style="font-size:12px; opacity:.7;">@[HANDLE_INFLUENCER_1]</p>
    </div>
    <!-- duplicar por cada creador -->
  </div>
</section>
```

**Variante sin fotos:** elimina la etiqueta `<img>` y deja solo la cita + handle.

---

## Notas de Implementación

- Autorización obligatoria antes de publicar: usar solo citas/fotos con permiso explícito del creador o cliente (derechos de imagen / UGC rights).
- No usar reviews de plantilla/stock como si fueran reales — es tanto una infracción de la Regla Suprema como un riesgo legal (publicidad engañosa).
- Si usas una app de reviews de Shopify (Judge.me, Loox, etc.), este bloque HTML es complementario, no sustituto — la app gestiona la verificación de compra real.
