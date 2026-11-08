# Matriz Global de Precios — Auto-DS

**GEM OS v2.1 | Reglas inmutables de pricing para catálogo Shopify**

---

## Fórmula Base (Regla 3x)

```
PVP = (Costo_Proveedor + Costo_Envío) × 3
```

> Esta es la regla mínima absoluta. Por debajo de 3x → RECHAZAR el producto.

---

## Desglose del Margen

| Componente | % del PVP | Descripción |
|---|---|---|
| Costo producto + envío | ~33% | Lo que pagas al proveedor |
| Margen ads (Meta/TikTok) | ~20% | Presupuesto de adquisición |
| Margen neto operacional | ~47% | Tu beneficio real |

**Costes reales del P&L:** fees Shopify + divisa 4,0 % y cancelaciones/devoluciones 10,1 % de la facturación. El curso no fija un umbral de margen bruto (%).

---

## Configuración en Auto-DS (Pricing Rules)

### Fórmula sugerida para Auto-DS:
```
Selling Price = (Item Cost + Shipping Cost) × 3.5
```
Se usa 3.5x como valor por defecto (por encima del objetivo 3x y del mínimo 2x) para absorber variaciones de envío y fees de Shopify/Stripe.

### Reglas de redondeo psicológico

| Rango de PVP calculado | Redondeo | Ejemplo |
|---|---|---|
| Menos de 20 € | Bajar al .99 inferior | 17.99 € |
| Entre 20 € y 50 € | Bajar al .95 o .99 | 34.95 € / 49.99 € |
| Más de 50 € | Bajar al .97 o .00 | 79.97 € / 99.00 € |

> En Auto-DS: Settings → Pricing Rules → Rounding → "Round to .99" o valor personalizado.

---

## Clasificación por Multiplicador

| Multiplicador | Clasificación GEM OS | Acción |
|---|---|---|
| ≥ 5x | **HOT** | Acción inmediata — pasar a copywriting |
| 3x – 4.99x | **WARM** | Desarrollar — re-evaluar siguiente ciclo |
| 2x – 2.99x | **COLD** | Monitoreo pasivo |
| < 2x | **DISCARD** | Rechazar — no procesar |

---

## Restricciones Absolutas

- **Baterías de litio sueltas:** categoría prohibida (riesgo Stripe/PayPal)
- **Multiplicador mínimo:** 2x sobre coste landed — por debajo, RECHAZAR (objetivo 3x: advertir)

---

*Fuente: `.continue/rules/dropshipping_financial_rules.md` | Metodología Adrián Sáenz & Iván Caicedo*
