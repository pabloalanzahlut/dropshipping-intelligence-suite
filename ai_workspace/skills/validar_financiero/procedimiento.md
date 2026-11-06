# Skill: Validar Financiero de Producto

**ID:** `validar_financiero`
**Versión:** 1.0.0
**Propósito:** Validar si un producto cumple las reglas financieras y logísticas inmutables de GEM OS antes de avanzar al pipeline. Calcula CPA máximo para campañas de pago.

**Referencias:**
  - `app/services/financial_validator.py` — lógica Python de respaldo
  - `.continue/rules/dropshipping_financial_rules.md` — reglas detalladas
  - `CLAUDE.md` — Reglas Financieras Inmutables

---

## 1. Input Esperado

El agente recibe los datos del producto. Mínimo requerido:

```
Nombre: [nombre del producto]
Costo origen (AliExpress/AutoDS): [€/$ con decimales]
PVP objetivo: [€/$ con decimales]
Peso estimado: [gramos o kg]
Envío estimado: [€/$] (si se conoce; si no, usar 4.50 como estimado)
```

Si falta algún dato crítico → aplicar protocolo `DATA_GAP_REQUEST`: preguntar al usuario antes de calcular.

---

## 2. Reglas de Validación (en orden de ejecución)

### Paso 1: Regla de Peso

| Condición | Resultado |
|-----------|-----------|

### Paso 2: Categoría Prohibida

| Categoría | Resultado |
|-----------|-----------|
| Baterías de litio sueltas | **RECHAZAR** — `CATEGORIA_PROHIBIDA` |
| Líquidos inflamables | **RECHAZAR** — `CATEGORIA_PROHIBIDA` |
| Resto de categorías | CONTINUAR |

### Paso 3: Regla 3x (Multiplicador de Margen)

```
Multiplicador = PVP / Costo_origen
```

| Resultado | Clasificación |
|-----------|--------------|
| ≥ 5x | HOT — proceder al pipeline completo |
| 3x – 4.99x | WARM — proceder con monitoreo de costes |
| 1.5x – 2.99x | COLD — **ADVERTENCIA**: margen insuficiente |
| < 1.5x | **RECHAZAR** — `MARGEN_INSUFICIENTE` |

### Paso 4: Margen Bruto Operativo

```
Margen_Bruto = ((PVP - Costo_origen - Envío_estimado) / PVP) × 100
```

| Resultado | Acción |
|-----------|--------|
| — | El curso no fija umbral de margen |
| 60% – 69.9% | **ADVERTENCIA** — `MARGEN_AJUSTADO` |
| < 60% | **RECHAZAR** — `MARGEN_BRUTO_BAJO` |

### Paso 5: Cálculo CPA Máximo (Para Campañas de Pago)

```
CPA_max = PVP - Costo_origen - Envío_estimado - (PVP × 0.03)
```

> El 3% cubre comisiones de pasarela de pago (Stripe/PayPal).

Este valor es el **CPA de punto de equilibrio**. Para obtener el CPA objetivo con beneficio real:

```
CPA_objetivo = CPA_max × 0.70   (reserva 30% de margen operativo)
```

---

## 3. Output Estructurado

```
╔══════════════════════════════════════════╗
║   VALIDACIÓN FINANCIERA GEM OS           ║
╠══════════════════════════════════════════╣
║ Producto: [nombre]
║ 
║ DATOS DE ENTRADA
║   Costo origen:    [X]€
║   Envío estimado:  [X]€
║   PVP objetivo:    [X]€
║   Peso:            [X]g
║
║ RESULTADOS
║   Multiplicador:   [X]x  → [HOT/WARM/COLD/RECHAZADO]
║   Margen Bruto:    [X]%  → [APROBADO/ADVERTENCIA/RECHAZADO]
║   CPA máximo:      [X]€  (punto de equilibrio)
║   CPA objetivo:    [X]€  (con 30% margen operativo)
║
║ VEREDICTO FINAL: [APROBADO ✅ / ADVERTENCIA ⚠️ / RECHAZADO ❌]
║ Motivo: [código de error si aplica]
╚══════════════════════════════════════════╝
```

---

## 4. Reglas de Comportamiento

- **Nunca** asumir costes no proporcionados por el usuario (protocolo `DATA_GAP_REQUEST`)
- Si el producto es RECHAZADO en cualquier paso → detener y NO calcular pasos posteriores
- Si hay ADVERTENCIA → completar todos los cálculos y mostrar el motivo al final
- El CPA máximo es siempre orientativo; los costes reales de Meta Ads varían
- Registrar resultado en DB si está disponible `app/database/dropshipping_suite.db`

