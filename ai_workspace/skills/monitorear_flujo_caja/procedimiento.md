# Skill: Monitorear Flujo de Caja

**ID:** `monitorear_flujo_caja`
**Versión:** 1.0.0
**Propósito:** Analizar la salud del flujo de caja diario o semanal de una tienda en dropshipping activo. Detectar el riesgo de quiebra por timing entre cobros de pasarela (2-3 días) y pagos al proveedor (inmediatos). Nivel 6 del framework de escalado.

**Referencias:**
  - `ai_workspace/skills/validar_financiero/procedimiento.md` — para CPA_max de referencia
  - `ai_workspace/context/formulas_conversion.md` — benchmarks ROAS y CPA

---

## 1. Input Esperado

El usuario pega los datos en texto plano. No se requiere formato específico:

```
DATOS DE HOY (o de la semana):
- Ventas Shopify: [X] pedidos × [PVP]€ = [X]€ ingresos brutos
- Gasto publicitario Meta/TikTok: [X]€
- Coste de pedidos pagados al proveedor hoy: [X]€
- Dinero liberado por pasarela hoy: [X]€
- Saldo disponible en cuenta bancaria: [X]€
- Pedidos pendientes de pago al proveedor (aún no pagados): [X] pedidos × [costo]€
```

Si faltan datos, preguntar antes de continuar (protocolo `DATA_GAP_REQUEST`).

---

## 2. Cálculos de Salud Financiera

### Paso 1: Resultado Neto del Período

```
Ingresos_brutos - Gasto_publicitario - COGS_pagado = Resultado_neto_período
```

### Paso 2: Flujo de Caja Real (Dinero en Mano)

```
Saldo_cuenta + Liberaciones_pasarela_hoy - Pagos_proveedor_pendientes = Caja_disponible_real
```

### Paso 3: Días de Caja

```
Días_de_caja = Caja_disponible_real / (Gasto_publicitario_diario + COGS_diario_estimado)
```

| Días de caja | Estado |
|--------------|--------|
| ≥ 7 días | 🟢 SALUDABLE |
| 4 – 6 días | 🟡 PRECAUCIÓN — reducir presupuesto de ads 20% |
| 2 – 3 días | 🔴 ALERTA — pausar ads hasta liberar pagos de pasarela |
| < 2 días | 🚨 CRÍTICO — pausar ads inmediatamente, no hacer nuevos pedidos |

### Paso 4: ROAS del Período

```
ROAS = Ingresos_brutos / Gasto_publicitario
```

| ROAS | Interpretación |
|------|----------------|
| ≥ 3.0 | Campaña rentable — mantener o escalar |
| 2.0 – 2.99 | Rentable pero ajustado — optimizar públicos |
| 1.0 – 1.99 | En pérdida — revisar CPA y producto |
| < 1.0 | Sangrado — pausar inmediatamente |

### Paso 5: CPA Real vs. CPA Objetivo

```
CPA_real = Gasto_publicitario / Número_de_ventas
```

Comparar con `CPA_objetivo` calculado en `/validar-financiero` (CPA_max × 0.70).

---

## 3. Output Estructurado

```
╔══════════════════════════════════════════╗
║   MONITOR DE FLUJO DE CAJA GEM OS        ║
╠══════════════════════════════════════════╣
║ Período: [fecha]
║
║ RESULTADO DEL PERÍODO
║   Ingresos brutos:     [X]€
║   Gasto publicitario:  [X]€
║   COGS pagado:         [X]€
║   Resultado neto:      [X]€  ([+/-])
║
║ SALUD DE CAJA
║   Caja disponible real: [X]€
║   Días de caja:         [X] días  → [🟢/🟡/🔴/🚨]
║
║ EFICIENCIA DE CAMPAÑA
║   ROAS:                 [X]x  → [estado]
║   CPA real:             [X]€
║   CPA objetivo:         [X]€  → [BAJO OBJETIVO ✅ / SOBRE OBJETIVO ⚠️]
║
║ ACCIÓN RECOMENDADA:
║   [instrucción concreta: mantener / reducir X% / pausar / escalar]
╚══════════════════════════════════════════╝
```

---

## 4. Reglas de Comportamiento

- Nunca recomendar escalar si los días de caja son < 4
- Si ROAS > 2.5 pero días de caja < 4 → recomendar esperar liberación de pagos antes de escalar
- Alertar explícitamente sobre el desfase temporal: "las pasarelas liberan en 2-3 días pero el proveedor cobra ahora"
- Si los datos son de varios días, calcular promedios diarios para normalizar
- Este análisis es orientativo; recomendar siempre validar con un contador para decisiones fiscales
