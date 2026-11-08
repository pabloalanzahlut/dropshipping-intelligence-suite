# Skill: Validación Financiera de Producto

Ejecuta la validación financiera completa de un producto según las reglas inmutables de GEM OS.

## Input requerido:
- Costo de origen (CO) del proveedor
- Precio de venta sugerido (PVP)
- Peso del producto (kg)
- ¿Contiene baterías de litio sueltas? (sí/no)

Si alguno falta → preguntar al usuario.

## Cálculos obligatorios:

```
Ratio 3x      = PVP / CO  (debe ser ≥ 3.0)
Coste landed  = costo_origen + envío
Multiplicador = PVP / coste landed
Margen bruto  = (PVP - coste landed) / PVP × 100  (informativo: el curso no fija umbral)
```

## Reglas de validación:

| Criterio | Umbral | Resultado si falla |
|----------|--------|-------------------|
| Multiplicador mínimo (sobre coste landed) | ≥ 2.0 | ❌ RECHAZAR |
| Multiplicador objetivo | ≥ 3.0 | ⚠️ ADVERTIR |
| Coste de origen | $5–15 | ⚠️ ADVERTIR fuera de rango |
| Baterías litio sueltas | No | ❌ RECHAZAR categoría |

## Output:

```
✅ APROBADO / ❌ RECHAZADO / ⚠️ CONDICIONAL

Multiplicador: X.X sobre coste landed (mínimo 2.0 · objetivo 3.0)
Margen neto/unidad: $X.XX tras fees 4,0 % y cancelaciones 10,1 %
Logística: OK / PROBLEMA (baterías de litio sueltas)

Veredicto: [explicación]
```

**Referencia:** `.continue/rules/dropshipping_financial_rules.md`
