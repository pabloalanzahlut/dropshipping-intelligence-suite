# Proveedores de Pago — Checklist de Activación
> producto_01 · Fase 2 · Módulo 05
> Shopify Admin → Settings → Payments
> Referencia del documento complementario: [Shopify — Aceptar pagos en línea](https://www.shopify.com/es/aceptar-pagos-en-linea)

---

## Por qué importa

Sin un proveedor de pago activo, la tienda no puede procesar ventas. Esta página **no es un generador de contenido** — es una decisión de configuración que debe tomar el operador humano directamente en el Admin de Shopify, según disponibilidad en tu país y datos fiscales/bancarios reales.

---

## Opciones principales

| Proveedor | Disponibilidad | Comisión típica | Notas |
|---|---|---|---|
| Shopify Payments | Según país (ver link oficial arriba) | Variable según plan | Recomendado si está disponible en [PAÍS]: evita la comisión extra por pasarela de terceros |
| PayPal | Global | ~3-4% + fijo | Complemento habitual, o alternativa si Shopify Payments no está disponible en [PAÍS] |
| Pasarela de terceros (Stripe, Mercado Pago, etc.) | Según país | Variable | Shopify cobra comisión extra por transacción si no se usa Shopify Payments |

---

## Checklist

- [ ] Confirmar si Shopify Payments está disponible en [PAÍS] (consultar el link oficial — no asumir)
- [ ] Si no está disponible, activar al menos PayPal para no perder ventas
- [ ] Activar mínimo 1 método de pago en Settings → Payments antes de publicar la tienda
- [ ] Completar verificación de identidad / cuenta bancaria que exija el proveedor (KYC)
- [ ] Alinear los logos mostrados en [../04_componentes_conversion/02_beneficios_y_trust_badges.md](../04_componentes_conversion/02_beneficios_y_trust_badges.md) con los métodos realmente activos
- [ ] Hacer una compra de prueba (modo test / tarjeta de prueba de Shopify) antes de lanzar

---

## Nota GEM OS

Esta acción la ejecuta el operador humano directamente en Shopify Admin — requiere datos bancarios/fiscales reales que este sistema no debe ni puede introducir (Regla Suprema NO INVENTAR + prohibición de manejo de credenciales financieras).
