# Banner Hero + Marquesina (Ticker)
> producto_01 · Fase 2 · Módulo 04
> Pegar en: Shopify Admin → Online Store → Themes → Customize → sección "Custom Liquid" (justo debajo del header)
> Equivale a: "Constructor de Banners" + "Constructor de Marquesina" del documento complementario

---

## 1. Banner Hero

Reutiliza los valores ya definidos en [../01_tema/configuracion_tema.md](../01_tema/configuracion_tema.md) (`[MENSAJE_HERO]`, `[SUBTITULO_HERO]`, `[CTA_HERO]`). Completa primero ese archivo.

```html
<section style="background:[HEX_FONDO]; color:[HEX_PRIMARIO]; text-align:center; padding:48px 16px;">
  <h1 style="font-family:[FUENTE_HEADING]; font-size:clamp(24px,5vw,40px); margin:0 0 8px;">[MENSAJE_HERO]</h1>
  <p style="font-family:[FUENTE_BODY]; font-size:16px; margin:0 0 20px; opacity:.85;">[SUBTITULO_HERO]</p>
  <a href="/collections/[CATEGORIA_1]" style="display:inline-block; background:[HEX_SECUNDARIO]; color:#fff; padding:14px 28px; border-radius:6px; text-decoration:none; font-weight:600;">[CTA_HERO]</a>
</section>
```

---

## 2. Marquesina (franja de confianza)

Texto corto en movimiento horizontal continuo, debajo del header o del banner. Solo usa afirmaciones verificables.

```html
<div style="overflow:hidden; background:[HEX_SECUNDARIO]; color:#fff; padding:8px 0;">
  <div style="display:inline-block; white-space:nowrap; animation: gem-marquee 22s linear infinite;">
    <span style="margin:0 32px;">🚚 Envío 6-12 días laborables</span>
    <span style="margin:0 32px;">🔒 Pago 100% seguro</span>
    <span style="margin:0 32px;">↩️ Devolución 30 días</span>
    <span style="margin:0 32px;">⭐ [N_CLIENTES] clientes satisfechos</span>
    <!-- bloque duplicado para loop continuo sin salto visual -->
    <span style="margin:0 32px;">🚚 Envío 6-12 días laborables</span>
    <span style="margin:0 32px;">🔒 Pago 100% seguro</span>
    <span style="margin:0 32px;">↩️ Devolución 30 días</span>
    <span style="margin:0 32px;">⭐ [N_CLIENTES] clientes satisfechos</span>
  </div>
</div>
<style>
@keyframes gem-marquee { from { transform: translateX(0); } to { transform: translateX(-50%); } }
</style>
```

---

## Notas de Implementación

- `[N_CLIENTES]`: usar el número real de pedidos completados (Shopify Analytics). Si aún no hay ventas, omitir ese `<span>` por completo — no inventar cifra (Regla Suprema NO INVENTAR).
- Nunca sustituir "6-12 días laborables" por "24-48h" ni similares.
- Sin JS: funciona con CSS puro en cualquier tema Shopify que permita bloque "Custom Liquid"/"Custom HTML".
- Verificar contraste de color (texto blanco sobre `[HEX_SECUNDARIO]`) — si el color secundario es claro, usar texto oscuro en su lugar.
