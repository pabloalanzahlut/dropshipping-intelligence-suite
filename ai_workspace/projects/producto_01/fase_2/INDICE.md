# FASE 2 — Tema Visual + Primer Producto
> Metodología Adrián Sáenz | GEM OS v3.7

---

## Prerequisito
Fase 1 implementada en Shopify (páginas de confianza, menú, políticas legales).

---

## Módulos de esta fase

### 01 — Tema y Personalización Visual
Archivo: [01_tema/configuracion_tema.md](01_tema/configuracion_tema.md)

- Paleta de colores (hex primario, secundario, fondo)
- Tipografía (heading / body)
- Logo y favicon
- Banner hero (mensaje + CTA)
- Sección de confianza ("¿Por qué nosotros?")

### 02 — Ficha Producto (primer producto)
Archivo: [02_producto/ficha_shopify.md](02_producto/ficha_shopify.md)

Generado con `/redactar-ficha-shopify`:
- Título SEO (< 60 chars)
- Descripción AIDA en HTML Shopify
- Bullet points de beneficios (máx. 5)
- Variantes y precio (Regla 3x verificada)
- Metafields: material, peso_kg, origen

### 03 — Configuración de Envío
Archivo: [03_envio/zonas_tarifas.md](03_envio/zonas_tarifas.md)

- Zonas geográficas
- Tarifa estándar ({{DIAS_ENVIO_PROVEEDOR}} días laborables)
- Umbral de envío gratuito
- Perfil de envío en Shopify

### 04 — Componentes de Conversión
Archivo: [04_componentes_conversion/INDICE.md](04_componentes_conversion/INDICE.md)

Equivalentes nativos a los GPTs del documento complementario del curso ("GPTs para diseñar tu tienda"): banner, marquesina, beneficios, trust badges, reviews (clientes/influencers), comparador, acordeón FAQ.

### 05 — Proveedores de Pago
Archivo: [05_pagos/proveedores_pago.md](05_pagos/proveedores_pago.md)

Checklist de activación de Shopify Payments / PayPal — acción manual del operador en Shopify Admin (no generable por GEM OS).

---

## Checklist de implementación

- [ ] Tema instalado y paleta aplicada
- [ ] Logo subido (PNG transparente, mín. 300×100 px)
- [ ] Primer producto creado con ficha AIDA
- [ ] Precio verificado con `/validar-financiero`
- [ ] Zonas de envío configuradas (sin prometer < 6 días)
- [ ] Componentes de conversión (módulo 04) pegados en Home/producto
- [ ] Al menos un método de pago activo (módulo 05)
- [ ] Vista previa en móvil revisada

---

## Estado: PENDIENTE

Ejecutar `/redactar-ficha-shopify` y `/validar-financiero` antes de completar módulo 02. Módulos 04 y 05 pueden avanzarse en paralelo (no dependen del producto final), pero el contenido con placeholders de color/marca depende de que el módulo 01 (tema) esté completado.
