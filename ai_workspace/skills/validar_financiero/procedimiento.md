# Skill: Validar Financiero de Producto

**ID:** `validar_financiero`
**Versión:** 2.0.0
**Propósito:** Validar si un producto cumple las reglas financieras y logísticas de GEM OS antes de avanzar en el pipeline, y calcular el CPA de equilibrio para campañas de pago.

**Fuente única de reglas:** `.claude/memory/reglas-financieras.md` (Adrián Sáenz). Si este procedimiento y ese archivo discrepan, manda ese archivo.

**Referencias:**
  - `app/services/financial_validator.py` — cálculo con coste landed y costes operativos
  - `app/services/deterministic_gate.py` — recálculo independiente, no persuadible
  - `CLAUDE.md` — Reglas financieras

---

## 1. Input Esperado

Los cuatro primeros datos son obligatorios:

```
Nombre: [nombre del producto]
Costo origen (proveedor): [importe y divisa]
Envío del proveedor al cliente: [importe y divisa]
PVP objetivo: [importe y divisa]
¿Baterías de litio sueltas?: [sí/no]
Peso: [dato del proveedor — solo informativo]
```

Si falta el costo de origen, el envío o el PVP → protocolo `DATA_GAP_REQUEST`: preguntar al usuario antes de calcular. **El envío nunca se estima**: sin envío no hay coste landed y sin coste landed no hay multiplicador.

Si el coste y el PVP están en divisas distintas, convertir al tipo del día (`app/services/fx_rates.py`); un tipo fijo falsea el multiplicador.

---

## 2. Reglas de Validación (en orden de ejecución)

### Paso 1: Categoría Prohibida

| Categoría | Resultado |
|-----------|-----------|
| Baterías de litio sueltas | **RECHAZAR** — `CATEGORIA_PROHIBIDA` |
| Líquidos inflamables | **RECHAZAR** — `CATEGORIA_PROHIBIDA` |
| Resto de categorías | CONTINUAR |

El curso no fija límite de peso en kg: el peso no rechaza ni advierte.

### Paso 2: Coste Landed

```
Coste_landed = Costo_origen + Envío
```

El multiplicador se mide siempre contra el coste landed, nunca contra el producto solo
(`qgK3GfY5ZC4 11:30`: $5 producto + $2 envío = $7 landed).

### Paso 3: Multiplicador sobre coste landed

```
Multiplicador = PVP / Coste_landed
```

| Resultado | Clasificación | Acción |
|-----------|--------------|--------|
| ≥ 5x | HOT | Aprobar — pipeline completo |
| 3x – 4.99x | WARM | Aprobar |
| 2x – 2.99x | COLD | **ADVERTENCIA** — cumple el mínimo; subir hacia 3x si el producto lo permite |
| < 2x | DISCARD | **RECHAZAR** — `MARGEN_INSUFICIENTE` |

Fuente: mínimo 2x y objetivo 3x (`Q4Ykcwh5Osc 24:40`).

### Paso 4: Coste de origen

| Condición | Resultado |
|-----------|-----------|
| $5 – $15 | OK |
| Fuera de rango | **ADVERTENCIA** — `COSTE_ORIGEN_FUERA_DE_RANGO` (`Q4Ykcwh5Osc 17:50`) |

### Paso 5: Margen (informativo)

```
Margen_bruto = (PVP − Coste_landed) / PVP × 100
Margen_neto_unidad = PVP − Coste_landed − (PVP × 0,040) − (PVP × 0,101)
```

- 4,0 % = fees Shopify + cambio de divisa · 10,1 % = cancelaciones y devoluciones (`rqMrq2MGdpw`, P&L de 30 días).
- **El curso no fija umbral de margen en %**: se muestra, no rechaza ni advierte.

### Paso 6: CPA de equilibrio (para campañas de pago)

```
CPA_equilibrio = Margen_neto_unidad
```

Es lo máximo que se puede pagar por una venta sin perder dinero. El curso no fija un CPA
objetivo: la rentabilidad de la campaña se controla con **ROAS real ≥ 2**, medido contra
ingresos reales y no contra lo que declara la plataforma (`Q4Ykcwh5Osc 09:40`).

---

## 3. Output Estructurado

```
╔══════════════════════════════════════════╗
║   VALIDACIÓN FINANCIERA GEM OS           ║
╠══════════════════════════════════════════╣
║ Producto: [nombre]
║
║ DATOS DE ENTRADA
║   Costo origen:    [X]
║   Envío:           [X]
║   Coste landed:    [X]
║   PVP objetivo:    [X]
║   Peso:            [X]  (informativo)
║
║ RESULTADOS
║   Multiplicador:   [X]x sobre coste landed → [HOT/WARM/COLD/DISCARD]
║   Margen bruto:    [X]%  (informativo)
║   Margen neto/ud:  [X]   tras fees 4,0 % y cancelaciones 10,1 %
║   CPA equilibrio:  [X]
║
║ VEREDICTO FINAL: [APROBADO ✅ / ADVERTENCIA ⚠️ / RECHAZADO ❌]
║ Motivo: [código si aplica]
╚══════════════════════════════════════════╝
```

Ejemplo del curso (`Q4Ykcwh5Osc 23:54`): 21 € → 49,99 € = 2,38x, 58 % de margen →
VALIDADO con advertencia de subir a 3x.

---

## 4. Reglas de Comportamiento

- **Nunca** asumir costes no proporcionados por el usuario (protocolo `DATA_GAP_REQUEST`)
- Si el producto es RECHAZADO en cualquier paso → detener y NO calcular pasos posteriores
- Si hay ADVERTENCIA → completar todos los cálculos y mostrar el motivo al final
- Todo resultado con números pasa por `verificar_validacion_financiera` (`deterministic_gate.py`) antes de darse por bueno
- El CPA de equilibrio es orientativo; los costes reales de las campañas varían
- Registrar resultado en DB si está disponible `app/database/dropshipping_suite.db`
