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
Margen Bruto  = (PVP - CO) / PVP × 100  (debe ser ≥ 70%)
```

## Reglas de validación:

| Criterio | Umbral | Resultado si falla |
|----------|--------|-------------------|
| Ratio 3x | ≥ 3.0 | ❌ RECHAZAR |
| Margen Bruto | ≥ 70% | ⚠️ ADVERTIR |
| Peso | < 1.2 kg | ❌ RECHAZAR si supera |
| Baterías litio sueltas | No | ❌ RECHAZAR categoría |

## Output:

```
✅ APROBADO / ❌ RECHAZADO / ⚠️ CONDICIONAL

Ratio 3x: X.X (objetivo ≥ 3.0)
Margen Bruto: XX% (objetivo ≥ 70%)
Peso: X.X kg (límite < 1.2 kg)
Logística: OK / PROBLEMA

Veredicto: [explicación]
```

**Referencia:** `.continue/rules/dropshipping_financial_rules.md`
