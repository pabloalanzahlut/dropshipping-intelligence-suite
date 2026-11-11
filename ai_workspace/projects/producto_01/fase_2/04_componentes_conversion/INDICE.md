# FASE 2 — Módulo 04: Componentes de Conversión
> Basado en "GPTs para diseñar tu tienda" (documento complementario del curso)
> GEM OS v2.2 — equivalentes nativos, sin depender de GPTs externos de ChatGPT

---

## Por qué este módulo existe

El documento complementario enlaza una serie de GPTs de ChatGPT (Constructor de Banners, Marquesina, Beneficios, Reviews, Comparador, Acordeón, Trust Badges). Esos GPTs requieren tu propia cuenta de ChatGPT — no son accesibles desde esta sesión. En su lugar, GEM OS genera aquí el mismo tipo de componente, listo para pegar en Shopify (**Online Store → Themes → Customize → Add section → Custom Liquid**, o en la descripción de una página/producto).

---

## Mapa Documento → Archivo

| Componente (GPT del documento) | Archivo GEM OS |
|---|---|
| Constructor de Banners | [01_banner_y_marquesina.md](01_banner_y_marquesina.md) |
| Constructor de Marquesina | [01_banner_y_marquesina.md](01_banner_y_marquesina.md) |
| Constructor de Beneficios | [02_beneficios_y_trust_badges.md](02_beneficios_y_trust_badges.md) |
| Constructor de Trust Badges | [02_beneficios_y_trust_badges.md](02_beneficios_y_trust_badges.md) |
| Constructor de Reviews Clientes | [03_reviews_sociales.md](03_reviews_sociales.md) |
| Constructor de Reviews Influencers (+ con fotos) | [03_reviews_sociales.md](03_reviews_sociales.md) |
| Constructor de Comparador | [04_comparador.md](04_comparador.md) |
| Constructor de Acordeón | [05_acordeon_faq.md](05_acordeon_faq.md) |
| Constructor de Descripción de Producto | Ya cubierto en [../02_producto/ficha_shopify.md](../02_producto/ficha_shopify.md) |
| Lista de proveedores de pago | [../05_pagos/proveedores_pago.md](../05_pagos/proveedores_pago.md) |

---

## Reglas GEM OS aplicadas en todo el módulo

- Ningún componente promete envío en 24-48h → siempre los días reales del proveedor ({{DIAS_ENVIO_PROVEEDOR}})
- Ningún componente usa superlativos vacíos ("el mejor", "increíble", "revolucionario")
- Reviews e influencers: **nunca fabricados** — solo contenido real o el bloque se deja vacío
- Comparador: nunca nombra marcas de competidores reales (riesgo legal de publicidad comparativa)
- Todo dato financiero o logístico usa placeholder hasta validarse con `/validar-financiero` o datos reales del proveedor

---

## Checklist de implementación

- [ ] Fase 1 implementada (prerequisito: páginas de confianza + políticas legales + aviso legal)
- [ ] Paleta/tipografía de `01_tema/configuracion_tema.md` ya completada (los componentes reutilizan esos mismos placeholders de color)
- [ ] Banner + Marquesina pegados en Home
- [ ] Beneficios + Trust Badges pegados en Home y/o página de producto
- [ ] Reviews reales cargadas (o bloque omitido hasta tener contenido real)
- [ ] Comparador revisado legalmente (sin nombrar competidores)
- [ ] Acordeón FAQ pegado, con texto idéntico al de `fase_1/02_paginas_confianza/faq.md`
