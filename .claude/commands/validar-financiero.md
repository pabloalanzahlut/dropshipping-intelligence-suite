---
model: sonnet
---
# Skill: Validación Financiera de Producto

Ejecuta la validación financiera completa de un producto según las reglas inmutables de GEM OS.

Lee `ai_workspace/skills/validar_financiero/procedimiento.md` y aplícalo.

## Input requerido:
- Costo de origen (CO) del proveedor
- Coste de envío del proveedor al cliente
- Precio de venta sugerido (PVP)
- ¿Contiene baterías de litio sueltas? (sí/no)

Si alguno falta → preguntar al usuario (`DATA_GAP_REQUEST`). El envío nunca se estima.
El peso es un dato del proveedor: se muestra, no valida (el curso no fija límite).

## Cálculos obligatorios:

```
Coste landed  = costo_origen + envío
Multiplicador = PVP / coste landed
Margen bruto  = (PVP - coste landed) / PVP × 100  (informativo: el curso no fija umbral)
Margen neto/unidad = PVP - coste landed - PVP × 4,0 % - PVP × 10,1 %
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

**Referencia:** `.claude/memory/reglas-financieras.md`
