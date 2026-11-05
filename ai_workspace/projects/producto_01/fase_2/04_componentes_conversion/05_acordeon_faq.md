# Acordeón FAQ (versión HTML interactiva)
> producto_01 · Fase 2 · Módulo 04
> Pegar en: Home y/o página de producto (complementa, no sustituye, la página /pages/faq de Fase 1)
> Equivale a: "Constructor de Acordeón" del documento complementario

Convierte el contenido ya validado de [../../fase_1/02_paginas_confianza/faq.md](../../fase_1/02_paginas_confianza/faq.md) en bloques plegables `<details>/<summary>` — nativos de HTML, sin dependencias ni JS.

```html
<section style="max-width:700px; margin:0 auto; padding:40px 16px;">
  <h2 style="text-align:center; margin-bottom:24px;">Preguntas Frecuentes</h2>

  <details style="border-bottom:1px solid #e5e5e5; padding:12px 0;">
    <summary style="cursor:pointer; font-weight:600;">¿Cuánto tarda en llegar mi pedido?</summary>
    <p style="font-size:14px; margin-top:8px;">Los pedidos se procesan en 1-3 días laborables. El tiempo de tránsito es de 6 a 12 días laborables adicionales. Recibirás un email con el número de seguimiento una vez que tu paquete haya salido de nuestro almacén.</p>
  </details>

  <details style="border-bottom:1px solid #e5e5e5; padding:12px 0;">
    <summary style="cursor:pointer; font-weight:600;">¿Envían a toda España / Latinoamérica?</summary>
    <p style="font-size:14px; margin-top:8px;">Sí, enviamos a [PAÍSES/REGIONES]. Si tienes dudas sobre si llegamos a tu zona, escríbenos a [EMAIL].</p>
  </details>

  <details style="border-bottom:1px solid #e5e5e5; padding:12px 0;">
    <summary style="cursor:pointer; font-weight:600;">¿Puedo devolver un producto?</summary>
    <p style="font-size:14px; margin-top:8px;">Aceptamos devoluciones y reclamaciones durante los 30 días siguientes a la recepción del pedido cuando el producto llegue defectuoso, dañado o no corresponda a lo descrito.</p>
  </details>

  <details style="border-bottom:1px solid #e5e5e5; padding:12px 0;">
    <summary style="cursor:pointer; font-weight:600;">¿Qué métodos de pago aceptáis?</summary>
    <p style="font-size:14px; margin-top:8px;">Aceptamos tarjeta de crédito/débito (Visa, Mastercard, Amex), PayPal y [otros métodos según configuración de Shopify Payments].</p>
  </details>

  <!-- añadir un <details> más por cada pregunta restante de faq.md (Productos, etc.) -->

</section>
```

---

## Notas de Implementación

- El texto de cada respuesta debe copiarse **literal** de `faq.md` (ya pasó la verificación GEM OS de Fase 1: plazos de envío, política de reembolso) — no reescribir ni acortar plazos.
- `<details>/<summary>` funciona en cualquier tema Shopify sin instalar apps ni JS adicional.
- No elimines la página completa `/pages/faq` — este acordeón es un resumen embebido en Home/producto, la página completa sigue siendo la referencia legal/operativa.
