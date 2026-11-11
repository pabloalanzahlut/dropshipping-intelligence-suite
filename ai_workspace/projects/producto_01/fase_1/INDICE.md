# FASE 1 — Estructura Base Tienda Shopify
> Fuente de verdad: vídeo `Q4Ykcwh5Osc` (transcripción descargada y contrastada el 2026-11-11; timestamps hh:mm:ss). Tienda: `jiimqj-ms.myshopify.com`.

---

## Estado verificado en vivo (2026-11-11)

Resultado: 3 elementos completos, 3 parciales, 7 pendientes, 2 no aplican o no son verificables desde fuera. **No está al 100 %.**

| Elemento | Qué pide el curso | Estado real |
|---|---|---|
| Tema | Sense (`00:35:31`) | OK — Sense activo |
| Políticas: reembolso, envío, términos, contacto + aviso legal, privacidad | Plantillas de Shopify + envío con días reales + aviso legal (`03:51:39`–`03:54:04`) | OK — 5 publicadas en español el 2026-11-11, enlazadas en el footer; pasan el gate determinista |
| Footer: políticas visibles + iconos de pago | `22:12:06`, `22:15:58` | OK — "Tecnología de Shopify" sigue visible |
| Página de contacto | Formulario + email, dirección, teléfono (≥2 de 3) + horario + plazo, en header y footer (`22:09:21`–`22:10:46`) | PARCIAL — `/pages/contact` solo tiene formulario; el footer enlaza "Información de contacto" (política) |
| Privacidad | Plantilla de Shopify revisada (`03:51:39`) | PARCIAL — nombra a "Il mio negozio" como titular; regenerar tras renombrar la tienda |
| Hero de la home | — | PARCIAL — existe, pero su botón apunta al producto del peine, que está en borrador (`products.json` vacío) |
| Nombre de marca, dominio y logo | ChatGPT 100 nombres + dominio libre + logo (`00:36:57`–`00:59:02`) | PENDIENTE — la tienda sigue llamándose "Il mio negozio"; sin dominio propio |
| Esquemas de color y tipografía | 2 esquemas (`01:00:12`); serifa si es belleza (`00:53:53`) | PENDIENTE — depende de la marca |
| Menú principal | Sustituir "Catálogo" por enlace al producto (`03:16:37`) | PENDIENTE — sigue el menú por defecto (Home / Catalogo / Contatti / Carrito) |
| FAQ | Acordeón en la ficha de producto (`03:06:48`) | PENDIENTE — la ficha está en borrador; la página `faqs` publicada está vacía |
| Páginas vacías | Evitar 404 y vacíos (`22:18:37`) | PENDIENTE — `about-us`, `faqs`, `return-policy`, `shipping-policy`, `terms-and-conditions`, `track-order` publicadas solo con título en inglés: rellenar o despublicar |
| Email de contacto con dominio | `03:52:49`, `22:09:21` | PENDIENTE — el contacto es un Gmail personal; depende del dominio |
| Envío | Siempre gratuito (`03:47:15`, `22:28:09`) | PENDIENTE — tarifas por definir (decisión: gratis siempre o umbral) |
| Colecciones | No se usan con un solo producto (`03:37:47`) | No aplica — solo existe `frontpage` |
| Cookies / privacidad del cliente | Dejar que Shopify lo active por mercado (`03:50:31`) | No verificable desde fuera: revisar Settings → Customer privacy |

---

## Archivos de esta fase

| Archivo | Estado |
|---|---|
| [01_navegacion/menu_principal.md](01_navegacion/menu_principal.md) | Sin aplicar. Contradice el curso para un solo producto (ver aviso del archivo) |
| [01_navegacion/colecciones.md](01_navegacion/colecciones.md) | Sin aplicar. No aplica a un solo producto |
| [01_navegacion/menu_footer.md](01_navegacion/menu_footer.md) | Sin aplicar. El footer de políticas ya es automático |
| [02_paginas_confianza/contacto.md](02_paginas_confianza/contacto.md) | Aplicar sobre `/pages/contact` (faltan dirección y teléfono) |
| [02_paginas_confianza/sobre_nosotros.md](02_paginas_confianza/sobre_nosotros.md) | Opcional (no está en el vídeo de 27 h) |
| [02_paginas_confianza/faq.md](02_paginas_confianza/faq.md) | Opcional; el curso usa el acordeón de `fase_2/04_componentes_conversion` |
| [02_paginas_confianza/seguimiento_pedido.md](02_paginas_confianza/seguimiento_pedido.md) | Opcional (no está en el vídeo) |
| [03_politicas_legales/borradores_es/politicas_es_borrador.md](03_politicas_legales/borradores_es/politicas_es_borrador.md) | Publicado 2026-11-11: es la versión vigente de las políticas |
| [03_politicas_legales/politica_reembolso.md](03_politicas_legales/politica_reembolso.md), [terminos_servicio.md](03_politicas_legales/terminos_servicio.md), [envio_entrega.md](03_politicas_legales/envio_entrega.md) | SUPERADOS por los publicados; no reutilizar |
| [03_politicas_legales/aviso_legal.md](03_politicas_legales/aviso_legal.md) | Publicado como "Información de contacto y aviso legal"; la página estándar no existe |
| [04_diseno_visual/tema_dawn.md](04_diseno_visual/tema_dawn.md) | Obsoleto como Dawn: el tema es Sense (aviso al inicio del archivo) |
| [04_diseno_visual/paleta_marca.md](04_diseno_visual/paleta_marca.md) | Pendiente de marca y logo |
| [04_diseno_visual/homepage.md](04_diseno_visual/homepage.md) | El hero ya existe en vivo; depende del producto |

Enlaces: las plantillas usan handles que no existen (`/pages/contacto`, `/pages/faq`, `/pages/sobre-nosotros`, `/pages/seguimiento-pedido`). En la tienda existen `contact`, `faqs`, `about-us` y `track-order`: usar esos para no crear enlaces rotos.

---

## Pendiente, en el orden del curso

1. Marca → dominio → email de dominio (`03:49:29`, `03:52:49`). Datos que faltan: nombre de marca (DATA_GAP).
2. Logo (icono + nombre, PNG transparente) y 2 esquemas de color (`00:50:01`–`01:02:56`).
3. Producto nuevo (el actual está en borrador) y arreglar el hero.
4. Menú: Inicio + producto + Contacto (`03:16:37`).
5. Completar `/pages/contact` y dejarla en header y footer.
6. Rellenar o despublicar las 6 páginas vacías.
7. Renombrar la tienda (Settings → General) y regenerar privacidad y contacto.
8. Tarifas de envío.
9. Revisión por un profesional cuando haya ventas (`03:51:39`): consta que no hay partita IVA.

Automatización: el repo no tiene ningún publicador hacia Shopify para menús, páginas o políticas (0 usos de las mutaciones correspondientes); se hace a mano en el admin. La app solo tiene lectura y `write_products` / `write_orders`: automatizarlo exigiría ampliar sus scopes.
