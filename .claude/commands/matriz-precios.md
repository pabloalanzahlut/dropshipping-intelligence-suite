# Skill: /matriz-precios — Matriz de Precios 2x/3x

Genera la matriz de precios con clasificación HOT/WARM/COLD/DISCARD para un lote de productos.

## Input requerido

Pide al usuario la lista de productos. Cada producto requiere:

| Campo | Requerido | Descripción |
|-------|-----------|-------------|
| `name` | ✅ | Nombre del producto |
| `cost_usd` | ✅ | Costo de origen en USD |
| `vertical` | ⬜ | Electronics / Fashion / Home / Beauty (default: "default") |
| `weight_kg` | ⬜ | Peso en kg (default: 0.0) |
| `shipping_override` | ⬜ | Envío real si se conoce; si no, usa defaults por vertical |

**Si falta `cost_usd` → `DATA_GAP_REQUEST`: preguntar al usuario antes de continuar. Nunca inventar costos.**

## Defaults de envío estimado por vertical

| Vertical | Envío estimado | Carrier típico |
|----------|---------------|----------------|
| Electronics | $5.00 | YunExpress |
| Fashion     | $3.50 | ePacket |
| Home        | $6.50 | YunExpress |
| Beauty      | $3.50 | ePacket |
| (otros)     | $4.50 | — |

## Fórmulas

```
PVP 2x  = ceil(CO × 2) − 0.01      ej: CO $9.50 → $18.99
PVP 3x  = ceil(CO × 3) − 0.01      ej: CO $9.50 → $28.99
Ratio   = PVP / CO
Margen neto = (PVP − CO − envío) / PVP × 100
```

## Clasificación por ratio (PVP/CO)

| Ratio | Clasificación |
|-------|--------------|
| ≥ 5.0x | 🔥 HOT |
| 3.0–4.99x | ♨️ WARM |
| 1.5–2.99x | 🧊 COLD |
| < 1.5x | ❌ DISCARD |

## Ejecución

```python
from app.services.pricing_matrix import PricingMatrix
from datetime import datetime

pm = PricingMatrix()
output = pm.run(
    products=[
        {"name": "...", "cost_usd": 0.0, "vertical": "...", "weight_kg": 0.0},
    ],
    budget_month=datetime.now().strftime("%Y-%m"),
    save=True,
)
print(output["table"])
```

## Output esperado

1. Tabla ASCII con columnas: Producto | CO | Ship | PVP 2x | Mg2x | Cls2x | PVP 3x | Mg3x | Cls3x | FV
2. Resumen de clasificaciones (HOT/WARM/COLD/DISCARD counts)
3. `correlation_id` del lote para auditoría
4. IDs guardados en `productos_validados` (si `save=True`)

**Referencia de reglas:** `CLAUDE.md` → Reglas Financieras (Inmutables) y `.continue/rules/dropshipping_financial_rules.md`
