# Configuración de Envío — Zonas y Tarifas
> producto_01 · Fase 2 · Módulo 03

---

## Perfil de envío en Shopify

**Ruta:** Settings → Shipping and delivery → Manage rates

---

## Zonas geográficas

| Zona | Países incluidos | Tarifa | Plazo |
|------|-----------------|--------|-------|
| `[ZONA_1]` | `[PAISES_1]` | `[PRECIO_ENV_1]` | {{DIAS_ENVIO_PROVEEDOR}} días lab. |
| `[ZONA_2]` | `[PAISES_2]` | `[PRECIO_ENV_2]` | {{DIAS_ENVIO_PROVEEDOR}} días lab. |
| Envío gratuito | Todas las zonas | Gratis | {{DIAS_ENVIO_PROVEEDOR}} días lab. |

**Umbral envío gratuito:** `[IMPORTE_GRATIS]` (ej. 35€)

> El curso (`Q4Ykcwh5Osc` 03:47:15 y 22:28:09) recomienda envío **siempre gratuito** (mejor un precio algo mayor que un coste de envío en el pago; a Google también le gusta). Decisión pendiente del operador: umbral o gratis siempre. En ambos casos el envío entra en el coste landed.

---

## Reglas GEM OS

- ✅ Nunca prometer menos días que los reales del proveedor (CLAUDE.md, Funnel Builder)
- ✅ Siempre incluir "laborables" (no días naturales)
- ✅ Mencionar código de rastreo disponible
- ❌ No prometer plazos de envío más cortos que los reales del proveedor

---

## Texto para página de Envío (ver fase_1/03_politicas_legales/envio_entrega.md)

Verificar coherencia entre:
- La tarifa configurada aquí
- El texto de la política de envío (Fase 1)
- La FAQ sobre envíos (Fase 1)

---

## Checklist

- [ ] Zona principal creada con tarifa real del proveedor
- [ ] Envío gratuito configurado a partir de `[IMPORTE_GRATIS]`
- [ ] Plazo = días reales del proveedor en todas las zonas
- [ ] Coherente con política de envío (Fase 1)
