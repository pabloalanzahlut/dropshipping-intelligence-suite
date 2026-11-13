---
model: sonnet
---
# Skill: /matriz-precios — Matriz de Precios 2x/3x

Genera la matriz de precios con clasificación HOT/WARM/COLD/DISCARD para un lote de productos.
Todos los múltiplos se calculan sobre el **coste landed** (producto + envío).

## Input requerido

Pide al usuario la lista de productos. Cada producto requiere:

| Campo | Requerido | Descripción |
|-------|-----------|-------------|
| `name` | ✅ | Nombre del producto |
| `cost_usd` | ✅ | Costo de origen en USD |
| `shipping_usd` | ✅ | Envío real del proveedor al cliente en USD |
| `vertical` | ⬜ | Electronics / Fashion / Home / Beauty (solo etiqueta; default: "default") |
| `weight_kg` | ⬜ | Peso en kg (informativo; default: 0.0) |

**Si falta `cost_usd` o `shipping_usd` → `DATA_GAP_REQUEST`: preguntar al usuario antes de continuar. Nunca inventar costos ni estimar el envío por vertical.**

## Fórmulas

```
Landed  = CO + envío
PVP 2x  = primer precio .99 que sea ≥ Landed × 2     ej: landed $7.00 → $14.99
PVP 3x  = primer precio .99 que sea ≥ Landed × 3     ej: landed $7.00 → $21.99
Ratio   = PVP / Landed
Margen  = (PVP − Landed) / PVP × 100                 (informativo)
```

El precio .99 se redondea siempre hacia arriba: un PVP un céntimo por debajo del múltiplo
(p. ej. $13.99 sobre landed $7.00 = 1,998x) no cumple el mínimo 2x.

## Clasificación por ratio (PVP / coste landed)

| Ratio | Clasificación |
|-------|--------------|
| ≥ 5.0x | 🔥 HOT |
| 3.0–4.99x | ♨️ WARM |
| 2.0–2.99x | 🧊 COLD |
| < 2.0x | ❌ DISCARD |

## Ejecución

```python
from app.services.pricing_matrix import PricingMatrix
from datetime import datetime

pm = PricingMatrix()
output = pm.run(
    products=[
        {"name": "...", "cost_usd": 0.0, "shipping_usd": 0.0, "vertical": "...", "weight_kg": 0.0},
    ],
    budget_month=datetime.now().strftime("%Y-%m"),
    save=True,
)
print(output["table"])
```

## Output esperado

1. Tabla ASCII con columnas: Producto | CO | Ship | Landed | PVP 2x | Mg2x | Cls2x | PVP 3x | Mg3x | Cls3x | FV
2. Resumen de clasificaciones (HOT/WARM/COLD/DISCARD counts)
3. `correlation_id` del lote para auditoría
4. IDs guardados en `productos_validados` (si `save=True`)

**Referencia de reglas:** `.claude/memory/reglas-financieras.md`
