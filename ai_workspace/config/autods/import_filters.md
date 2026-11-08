# Filtros de Importación — Auto-DS

**Checklist para evaluar proveedores antes de importar productos al catálogo Shopify**

Configurar en: **Auto-DS → Import List → Filters** y como referencia de revisión manual.

---

## NIVEL 1: Criterios de RECHAZO Automático

> Si se cumple **cualquiera** de estos, el producto se descarta sin revisión adicional.

- [ ] Tiempo de envío estimado **> 12 días laborables**
- [ ] Producto contiene **baterías de litio sueltas** (no integradas en el dispositivo)
- [ ] Multiplicador **< 2x** (PVP < 2 × coste landed: producto + envío)
- [ ] Proveedor con valoración **< 95% de satisfacción** o sin historial
- [ ] País de origen **no admitido** por la pasarela de pago activa (Stripe / PayPal)

---

## NIVEL 2: Criterios de ADVERTENCIA

> Requieren **revisión manual** antes de publicar. No se descartan automáticamente.

- [ ] Margen entre **3x y 3.5x** (WARM inferior — vigilar evolución del CPM)
- [ ] Tiempo de envío entre **10 y 12 días** (límite aceptable, comunicar bien al cliente)
- [ ] Producto con **variantes complejas** de talla, color o material (riesgo de stock)
- [ ] Proveedor con **< 500 ventas** registradas (nuevo en la plataforma)
- [ ] Categoría con **alta tasa de devoluciones** históricas (ropa de talla, electrónica frágil)

---

## NIVEL 3: Criterios IDEALES

> Priorizar estos proveedores en el catálogo. Son los candidatos HOT.

- [ ] Envío estimado **≤ 7 días laborables**
- [ ] Peso del producto **< 500 g**
- [ ] Margen calculado **≥ 5x** (clasificación HOT en GEM OS)
- [ ] Proveedor con **≥ 1.000 ventas** y **≥ 97% de satisfacción**
- [ ] Producto en nicho validado: Electronics, Home & Garden, Fitness, Pet Supplies
- [ ] Proveedor con **fotografías de alta calidad** o muestras disponibles

---

## Resumen de Clasificación GEM OS

| Margen | Envío | Clasificación | Acción |
|---|---|---|---|
| ≥ 5x | ≤ 7 días | **HOT** | Publicar — pasar a copywriting |
| 3x – 4.99x | ≤ 12 días | **WARM** | Revisar — ciclo siguiente |
| 1.5x – 2.99x | ≤ 12 días | **COLD** | Monitoreo pasivo |
| < 1.5x | cualquiera | **DISCARD** | Rechazar |
| cualquiera | > 12 días | **DISCARD** | Rechazar (logística) |

---

## Configuración en Auto-DS

**Filtros automáticos recomendados:**
- Processing Time: Max **7 days**
- Shipping Time: Max **12 days**
- Minimum feedback score: **95%**

**Filtros manuales (revisar al importar):**
- Calcular el multiplicador con la fórmula: `PVP propuesto ÷ (costo + envío)` → mínimo 2, objetivo 3
- Verificar que las imágenes del proveedor sean de calidad exportable

---

*Fuente: `.continue/rules/dropshipping_financial_rules.md` | GEM OS v2.1 — Fase 2*
