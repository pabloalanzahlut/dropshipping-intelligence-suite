# Beneficios + Trust Badges
> producto_01 · Fase 2 · Módulo 04
> Pegar en: Home (debajo del banner) y/o página de producto (cerca del botón "Añadir al carrito")
> Equivale a: "Constructor de Beneficios" + "Constructor de Trust Badges" del documento complementario

---

## 1. Sección Beneficios

Expande la sección "¿Por qué nosotros?" de [../01_tema/configuracion_tema.md](../01_tema/configuracion_tema.md) a 4 bloques icono + título + texto.

```html
<section style="padding:40px 16px; text-align:center;">
  <h2 style="font-family:[FUENTE_HEADING]; margin-bottom:24px;">¿Por qué comprar en [MARCA]?</h2>
  <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:24px;">
    <div style="max-width:220px;">
      <div style="font-size:32px;">🚚</div>
      <h3 style="font-size:16px; margin:8px 0 4px;">Envío rastreado</h3>
      <p style="font-size:14px; opacity:.8;">6-12 días laborables, con número de seguimiento.</p>
    </div>
    <div style="max-width:220px;">
      <div style="font-size:32px;">🔒</div>
      <h3 style="font-size:16px; margin:8px 0 4px;">Pago seguro</h3>
      <p style="font-size:14px; opacity:.8;">Shopify Payments / PayPal, cifrado SSL.</p>
    </div>
    <div style="max-width:220px;">
      <div style="font-size:32px;">✅</div>
      <h3 style="font-size:16px; margin:8px 0 4px;">Garantía real</h3>
      <p style="font-size:14px; opacity:.8;">Devolución 30 días si no cumple lo descrito.</p>
    </div>
    <div style="max-width:220px;">
      <div style="font-size:32px;">[ICONO_4]</div>
      <h3 style="font-size:16px; margin:8px 0 4px;">[BENEFICIO_4]</h3>
      <p style="font-size:14px; opacity:.8;">[EXPLICACION_4]</p>
    </div>
  </div>
</section>
```

---

## 2. Trust Badges (franja de métodos de pago)

```html
<div style="display:flex; justify-content:center; align-items:center; gap:16px; flex-wrap:wrap; padding:16px 0;">
  <img src="[URL_LOGO_VISA]" alt="Visa" height="28">
  <img src="[URL_LOGO_MASTERCARD]" alt="Mastercard" height="28">
  <img src="[URL_LOGO_PAYPAL]" alt="PayPal" height="28">
  <img src="[URL_LOGO_SSL]" alt="SSL seguro" height="28">
</div>
<p style="text-align:center; font-size:12px; opacity:.7;">Pago 100% seguro y cifrado</p>
```

---

## Notas de Implementación

- Logos oficiales: descargar del Brand Center de cada proveedor (Visa, Mastercard, PayPal) — no reutilizar sin derechos de marca.
- **No mostrar un badge de un método de pago que no esté realmente activo en tu checkout.** Verificar primero contra [../05_pagos/proveedores_pago.md](../05_pagos/proveedores_pago.md).
- `[BENEFICIO_4]`: usar un diferenciador real del producto/operación (ej. "Hecho en [PAÍS_ORIGEN]", "Stock propio", "Atención en español 24h") — no genérico vacío.
